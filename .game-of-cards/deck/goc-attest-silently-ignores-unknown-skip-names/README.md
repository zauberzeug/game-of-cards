---
title: goc-attest-silently-ignores-unknown-skip-names
summary: "`goc attest <card> --skip <name>` accepted any string: `_cmd_attest` only asked whether each configured check was named, never whether each name was a configured check, so a typo (`--skip plceholdr` for `placeholder`) was silently dropped and the check it meant to skip ran and was recorded as run — beside a valid skip the call even exited 0 with `Attestation OK`. It now refuses an unknown name before any check runs — exit 2, `ERROR: <title>: unknown --skip name '<name>' — the configured closure checks are: …`, nothing written — through the parent epic's shared `_refuse_invalid_input` helper."
status: done
stage: null
contribution: medium
created: "2026-05-31T03:20:21Z"
closed_at: "2026-10-28T05:09:47Z"
human_gate: none
advances:
  - mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] PROCESS: human picks Option A (strict reject) or Option B (warn-continue); decision recorded with `goc decide`. — decided 2026-10-22 via the parent epic: strict-refuse (exit 2).
  - [x] TDD: `reproduce.py` exits zero (typo is rejected/warned per chosen option, no longer silently dropped). — a typo alone and a typo beside a valid skip each get exit 2, `ERROR:` naming the unknown name and listing the configured checks, no check run and log.md untouched, while the valid-skip control is still recorded; the same script exits 1 against the pre-fix engine. Rewritten to the 0/1/2 contract: as filed it exited 0 while the defect fired.
  - [x] TDD: regression test under `tests/` covers (a) the unknown-skip rejection/warning path and (b) the all-valid-skips happy path. — `AttestCliTest` in `tests/test_mutation_verbs_refuse_invalid_input.py`: four refusal tests (a typo alone, beside a valid skip, several names reported once each in order, ahead of the all-skipped refusal) prove through marker files that no check ran and fail against the pre-fix engine; the valid-skip test passes on both.
  - [x] MECHANICAL: `_cmd_attest` in `goc/engine.py` validates `args.skips` against the configured check inventory before the per-check loop. — after the closed-card and no-checks-configured refusals, ahead of the all-skipped refusal and the loop, through `_refuse_invalid_input`.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` passes; `uv run goc validate` passes. — 1411 tests pass; `goc validate` exits 0.
worker: {who: "claude[bot]", where: main}
---

# `goc attest --skip <name>` accepts unknown skip names with no error

## Location

- `goc/engine.py` `_cmd_attest` — matched `--skip` names against the
  configured checks in one direction only; it now refuses a name no
  configured check has, before any check runs.
- `goc/engine.py` `p_attest` (the `attest` subparser) — `--skip` is
  `action="append"` with no `choices=`, so any string reaches
  `args.skips`. Unchanged: the check inventory lives in
  `.game-of-cards/config.yaml`, not in the parser. Its help now says an
  unknown name is refused.

## What was broken

As filed, `_cmd_attest` built `skips_set = set(args.skips)` and consulted
it only inside the per-check loop:

```python
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

The membership test ran one way: every configured check was looked up in
`skips_set`, but no skip name was ever looked up among the configured
checks. A name matching no check was dropped on the floor — no error, no
warning — and the check the caller meant to skip ran instead:

- **Pass case:** the targeted check ran and passed, the call printed
  `Attestation OK` and exited 0, and log.md recorded `[x] <real-name>`
  where the caller believed it had `[~] <real-name> SKIPPED`.
- **Fail case:** the targeted check ran and failed; the caller saw
  `attestation has failures` and nothing naming the typo, and had to
  work out why the skip did not apply.

## Empirical evidence

As filed, the original reproducer showed the typo accepted:

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

That reproducer exited 0 while the defect fired. It now follows the
reproducer contract (0 = defect no longer fires, 1 = fires, 2 = harness
broken) and drives the real CLI over a typo alone and a typo beside a
valid skip, each on its own card, with a valid skip as the control.
After the fix,
`uv run python .game-of-cards/deck/goc-attest-silently-ignores-unknown-skip-names/reproduce.py`
exits 0:

```text
$ goc attest typo --skip plceholdr --non-interactive
  exit 2
  stdout: (empty)
  stderr: ERROR: typo: unknown --skip name 'plceholdr' — the configured closure checks are: advanced-by-closed, placeholder

$ goc attest typo-beside-a-valid-skip --skip placeholder --skip advanced-by-clsed --non-interactive
  exit 2
  stdout: (empty)
  stderr: ERROR: typo-beside-a-valid-skip: unknown --skip name 'advanced-by-clsed' — the configured closure checks are: advanced-by-closed, placeholder

FIXED: an unknown --skip name is refused before any check runs, naming the configured checks, with nothing written; a valid skip is still recorded.
```

Against the pre-fix engine the same script exits 1: the typo alone ran
`placeholder` and wrote a FAIL block, and the typo beside a valid skip ran
`advanced-by-closed`, wrote its `[x]` row and exited 0 with
`Attestation OK` — the pass case above.

## Why it matters

`goc attest` writes the closure gate's record: `Skill(finish-card)` Step 5
runs it before `goc done`, and the block it appends to log.md is what a
later reader trusts for which checks ran and which were skipped. A silently
dropped `--skip` makes that record disagree with what the closer believed.
`--skip` is documented as the last-resort escape for a genuinely flaky
check, so it is reached for exactly when the closer is least likely to
re-read the output.

This card is one of the input-validation family the parent epic
[mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success](../mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success/)
coordinates — each one CLI verb whose argparse layer accepts the input and
whose command function acts on it without a precondition check — beside
[goc-decide-accepts-empty-decision-and-because-arguments](../goc-decide-accepts-empty-decision-and-because-arguments/),
[goc-advance-claims-success-when-adding-an-already-existing-edge](../goc-advance-claims-success-when-adding-an-already-existing-edge/),
[goc-unadvance-claims-success-when-removing-a-non-existent-edge](../goc-unadvance-claims-success-when-removing-a-non-existent-edge/)
and
[goc-status-silently-drops-worker-overrides-on-non-active-transitions](../goc-status-silently-drops-worker-overrides-on-non-active-transitions/).

## Decision

*Resolved 2026-10-22T05:20:22Z:* Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: Option A, strict rejection at command entry — an unknown --skip name exits 2 and lists the valid check names

*Reasoning:* The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question

## Fix

`_cmd_attest` collects the unknown names — each `--skip` value that is not
a configured check in either layer, reported once each in the order given
— and refuses them through the parent epic's shared
`_refuse_invalid_input` before any check runs:

```text
ERROR: <title>: unknown --skip name 'plceholdr' — the configured closure checks are: advanced-by-closed, placeholder
```

Exit 2, no check run, log.md untouched; several unknown names read
`unknown --skip names 'a', 'b'`. The refusal sits after the closed-card and
no-checks-configured refusals and ahead of the all-skipped one, so a typo is
reported even when the remaining names would also skip every check: fixing
the typo may be all the call needed. `Skill(finish-card)` `reference.md`
§ "Attest details and skip policy" documents it.

Regression tests: `AttestCliTest` in
`tests/test_mutation_verbs_refuse_invalid_input.py`, beside the family's
other verbs. Its configured checks are automated commands that each leave a
marker file when they run, so the refusal tests can show that no check ran,
not even the one a typo meant to skip.
