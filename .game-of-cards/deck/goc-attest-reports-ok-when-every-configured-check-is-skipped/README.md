---
title: goc-attest-reports-ok-when-every-configured-check-is-skipped
summary: "`goc attest <title> --skip <name>` for every configured check runs zero real checks, records each as `{passed, skipped}`, prints `Attestation OK`, and writes a `## Closure verification` block whose rows are all `[~] SKIPPED`. The empty-config guard that refuses to write a block proving nothing only fires when both layer arrays are empty — not when checks exist but are all skipped, so the same `proves-nothing` outcome leaks through the skip path."
status: active
stage: null
contribution: medium
created: "2026-06-10T05:14:06Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` asserts current defect (exit 0, "Attestation OK", log.md gains an all-SKIPPED block), then is re-asserted to exit zero (defect no longer fires) after the fix
  - [ ] MECHANICAL: `_cmd_attest` refuses to attest (non-zero exit, no `log.md` mutation) when every configured check across both layers is covered by `--skip`, mirroring the existing empty-config guard
  - [ ] TDD: a new regression test in `tests/` exercises the all-skipped path and verifies log.md is untouched and the exit code matches the empty-config contract
  - [ ] MECHANICAL: `goc validate` passes and the existing attest tests stay green
  - [ ] PROCESS: the all-skipped contract is documented in `_cmd_attest`'s docstring alongside the empty-config contract
worker: {who: "claude[bot]", where: main}
---

# `goc attest` reports OK and writes a closure block when every configured check is skipped

## Location

- `goc/engine.py:4218-4306` — `_cmd_attest`
- `goc/engine.py:4240-4247` — the empty-config guard (fires only when both layer arrays are empty)
- `goc/engine.py:4256-4267` — the per-check `--skip` branch (records `{passed: True, skipped: True}`)
- `goc/engine.py:4296-4305` — unconditional log-write + "Attestation OK."

## What's broken

`_cmd_attest`'s docstring states the empty-config contract explicitly:

```python
"""Run layer-2 + layer-3 closure checks; append "Closure verification" block to log.md.

Empty-config contract: when both ``layer_2_project_dod`` and ``layer_3_goc_dod``
are empty/unset, refuse the call (non-zero exit, no log.md mutation). Writing
a bare ``## Closure verification`` header would satisfy the bundled
``log-md-closure-entry`` derived check on content that proves nothing.
"""
```

The guard backing that contract only inspects whether the config arrays are
empty (`engine.py:4240`):

```python
layer_2_checks = config.get("layer_2_project_dod") or []
layer_3_checks = config.get("layer_3_goc_dod") or []
if not layer_2_checks and not layer_3_checks:
    print("ERROR: no closure checks configured ...", file=sys.stderr)
    sys.exit(2)
```

But a deck with checks *configured* can still run zero of them: pass `--skip`
for each one. Each skipped check takes the early branch at `engine.py:4256`:

```python
if name in skips_set:
    results.append({"layer": layer_num, "name": name, "passed": True,
                    "skipped": True, "summary": f"SKIPPED (...)"})
    print(f"  [~] {name} — SKIPPED")
    continue
```

`any_failed` never flips (skipped results carry `passed: True`), so execution
falls through to the unconditional log-write (`engine.py:4296-4299`) and the
"Attestation OK." print. The block written is all `[~] SKIPPED` rows — content
that proves exactly as much as the bare header the empty-config guard exists to
prevent: nothing. The bundled `log-md-closure-entry` derived check only looks
for the `## Closure verification` heading, so it accepts this block and lets
closure proceed as if attestation ran.

## Empirical evidence

See `reproduce.py`. With the goc-shipped default config (three layer-3 derived
checks) on a card with one unchecked DoD box:

```
goc attest sample-card --skip advanced-by-closed --skip dod-100-percent --skip log-md-closure-entry --non-interactive
```

prints "Attestation OK.", exits 0, and appends a `## Closure verification`
block whose three rows are all `[~] ... SKIPPED`. No check actually ran.

## Reachability

- An operator who finds one check inapplicable reaches for `--skip`; nothing
  stops them from skipping all three (e.g. a scripted closure wrapper that
  passes the full skip set, or a copy-paste of a skip line per check).
- `goc attest --skip <unknown>` is silently tolerated (sibling card
  `goc-attest-silently-ignores-unknown-skip-names`), so an operator already
  has no feedback that their skip names are doing anything — making an
  all-skip invocation easy to land by accident.

## Why it matters

This is the same integrity hole the empty-config guard was written to close,
reached through a different door. "No check ran" should be refused regardless
of *why* none ran — whether because none were configured or because all were
skipped. Allowing the all-skipped block to be written lets a downstream
`log-md-closure-entry` derived check pass on attestation that never verified
anything, defeating the closure contract. It joins the filed attest-integrity
family:
[goc-attest-reports-ok-and-writes-empty-stub-when-no-checks-are-configured](../goc-attest-reports-ok-and-writes-empty-stub-when-no-checks-are-configured/),
[goc-attest-silently-ignores-unknown-skip-names](../goc-attest-silently-ignores-unknown-skip-names/),
[bundled-closure-skips-configured-attestation-checks](../bundled-closure-skips-configured-attestation-checks/).

## Fix

Mirror the empty-config guard. After the layer arrays are loaded and the
empty-config guard passes, compute the set of configured check names and
refuse — non-zero exit, no `log.md` mutation — when `--skip` covers all of
them:

```python
all_check_names = {c["name"] for c in layer_2_checks} | {c["name"] for c in layer_3_checks}
if all_check_names and all_check_names <= skips_set:
    print("ERROR: every configured closure check was skipped ...", file=sys.stderr)
    sys.exit(2)
```

`--gate none`: the mechanism is determined by the existing empty-config guard's
documented intent (treat "no check actually runs" as a refusal). The fix is
single-site in `_cmd_attest` plus a regression test; the contract is recorded
in the docstring.
