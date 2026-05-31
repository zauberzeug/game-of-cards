---
title: goc-attest-silently-ignores-unknown-skip-names
summary: "`goc attest <card> --skip <name>` accepts arbitrary strings as skip names without validating them against the configured check inventory. A typo (e.g. `--skip complie` instead of `compile`) is silently a no-op: the user thinks they skipped a check; the check actually ran. No error, no warning. Same shape as the existing family of silently-dropped CLI-input bugs."
status: open
stage: null
contribution: medium
created: "2026-05-31T03:20:21Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: human picks Option A (strict reject) or Option B (warn-continue); decision recorded with `goc decide`.
  - [ ] TDD: `reproduce.py` exits zero (typo is rejected/warned per chosen option, no longer silently dropped).
  - [ ] TDD: regression test under `tests/` covers (a) the unknown-skip rejection/warning path and (b) the all-valid-skips happy path.
  - [ ] MECHANICAL: `_cmd_attest` in `goc/engine.py` validates `args.skips` against the configured check inventory before the per-check loop.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` passes; `uv run goc validate` passes.
---

# `goc attest --skip <name>` accepts unknown skip names with no error

## Location

`goc/engine.py:4115-4147` — `_cmd_attest`.

## What's broken

`_cmd_attest` builds `skips_set = set(args.skips)` and then checks
membership inside the per-check loop:

```python
def _cmd_attest(args):
    title = args.title
    skips = args.skips
    ...
    skips_set = set(skips)
    results: list[dict] = []
    any_failed = False

    for layer_key, layer_num in [("layer_2_project_dod", 2), ("layer_3_goc_dod", 3)]:
        layer_checks = config.get(layer_key) or []
        ...
        for check in layer_checks:
            name = check["name"]
            if name in skips_set:
                ...
                print(f"  [~] {name} — SKIPPED")
                continue
            ...
```

The set comparison is one-directional: every configured check name
is tested against `skips_set`, but no configured check name is ever
*tested for membership in the inventory of valid names*. A skip
name that does not match any configured check is silently dropped
on the floor.

User-observable consequence:

```bash
$ uv run goc attest my-card --skip complie    # typo for 'compile'
Layer-2 (project) checks:
  ... running compile
  [ ] compile — FAIL — ...
```

The user passed `--skip complie` intending to bypass the `compile`
check. The CLI accepted the flag (no error, no warning), then ran
the check anyway. In the pass case the user got their intended
outcome by accident; in the fail case the user has to debug why
"the skip didn't work" before realizing it's a typo.

## Empirical evidence

See `reproduce.py`. The script builds a temp deck with one
`layer_2_project_dod` check named `placeholder` (kind `manual`, so
it runs deterministically under `--non-interactive`), invokes
`goc attest <card> --skip plceholdr --non-interactive` with a
single-character typo, and asserts the stdout contains no
`unknown skip name` error AND that the check ran (rather than being
skipped):

```text
=== goc attest stdout ===
Layer-2 (project) checks:
  [ ] placeholder — non-interactive: manual check declined

Wrote attestation to ...
ERROR: attestation has failures; finish-card will block closure.

=== assertions ===
typo accepted silently: True       (expected: False — should error)
skipped marker present:  False     (i.e. check ran, not skipped)
```

The typo `plceholdr` was accepted as a valid skip name, no error
was raised, and the configured `placeholder` check ran (and failed)
instead of being treated as the user's intended skip target.

## Why it matters

`goc attest` is the closure-gate entry point — the verb is wired
into `goc done`'s bundled closure (`bundled-closure-skips-configured-attestation-checks`,
`goc-done-single-skips-log-md-attestation-while-bundle-emits-one`)
and into project-local DoD checks. Silent acceptance of an unknown
`--skip` name corrupts the closure-gate contract:

- **Pass case:** the user typed the wrong name; the targeted check
  passed anyway; the user files closure thinking they skipped it.
  The attestation log records `[x] <real-name>` instead of `[~]
  <real-name> — SKIPPED`. The skip didn't apply, but the user
  believes it did.
- **Fail case:** the user typed the wrong name; the targeted check
  failed; the user re-reads the CLI error, sees "attestation has
  failures", does not see "no such skip name 'plceholdr'", and may
  spend time investigating why the bypass didn't work.

Either way, the user's mental model of what was skipped diverges
from what the attestation log actually says. This is the same shape
as the existing family of silently-dropped CLI-input bugs — e.g.
[goc-decide-accepts-empty-decision-and-because-arguments](../goc-decide-accepts-empty-decision-and-because-arguments/),
[goc-advance-claims-success-when-adding-an-already-existing-edge](../goc-advance-claims-success-when-adding-an-already-existing-edge/),
[goc-unadvance-claims-success-when-removing-a-non-existent-edge](../goc-unadvance-claims-success-when-removing-a-non-existent-edge/),
[goc-status-silently-drops-worker-overrides-on-non-active-transitions](../goc-status-silently-drops-worker-overrides-on-non-active-transitions/)
— and warrants the same kind of fix.

Reachability path: the CLI argparser at `goc/engine.py:_build_parser`
adds `--skip` as `append`-style with no `choices=` restriction, so
any string flows through to `args.skips` and into `skips_set`.

## Decision required

Two credible fix paths exist; one needs a human pick.

### Option A — strict rejection at command entry (recommended)

Before the per-check loop, compute the set of valid skip names
from the config:

```python
valid_skip_names = {
    check["name"]
    for layer_key in ("layer_2_project_dod", "layer_3_goc_dod")
    for check in (config.get(layer_key) or [])
}
unknown = set(skips) - valid_skip_names
if unknown:
    print(
        f"ERROR: --skip name(s) {sorted(unknown)!r} do not match any "
        f"configured check; valid: {sorted(valid_skip_names)!r}",
        file=sys.stderr,
    )
    sys.exit(2)
```

Matches the existing pattern in `_cmd_status` / `_cmd_decide` for
flagged-unknown rejection. Breaking change for any script that
relied on the silent-no-op behavior, but that behavior is itself
the bug — no caller should be relying on it.

### Option B — warn-and-continue

Same validation, but print a warning to stderr and let the
attestation proceed. Preserves any backwards compat with scripts
that pass `--skip` names speculatively but still surfaces the
typo to a human in the terminal.

### What the human picks

- A or B (strict-error vs warn-continue).
- Whether the policy should generalize across the rest of the CLI
  surface — `goc decide`, `goc status`, `goc advance` already have
  pieces of this pattern; this card may want to be promoted to a
  `meta-fix` epic for "uniform unknown-input validation across CLI
  verbs" if the answer is consistently A.

## Fix (provisional, pending decision)

`goc/engine.py:_cmd_attest` (around line 4125), insert the validation
block from Option A or B before `for layer_key, layer_num in [...]`.

Regression test: `tests/test_attest_unknown_skip.py` covering both
the typo-rejection and the all-valid-skips happy path.

Do NOT apply the fix until the human picks A vs B.
