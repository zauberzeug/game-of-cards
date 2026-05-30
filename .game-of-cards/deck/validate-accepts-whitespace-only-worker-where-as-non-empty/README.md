---
title: validate-accepts-whitespace-only-worker-where-as-non-empty
summary: "`goc validate` accepts `worker: {who: alice, where: \"   \"}` as valid. The mapping branch of the worker validator checks `where` is a string but never checks it's non-whitespace, while the sibling `who` sub-key and the bare-string branch both reject whitespace-only. Second instance of the same defect shape as [validate-accepts-whitespace-only-worker-as-non-empty](../validate-accepts-whitespace-only-worker-as-non-empty/), which fixed the bare-string and `who` branches but missed `where`."
status: active
stage: null
contribution: medium
created: "2026-05-30T13:11:50Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: regression test asserts `goc validate` rejects `worker: {who: alice, where: "   "}` with stderr containing `worker: 'where' must be a non-empty, non-whitespace string`
  - [ ] TDD: existing whitespace-worker tests still pass (bare string, mapping `who`, valid `where`)
  - [ ] TDD: `reproduce.py` exits zero after fix (defect no longer fires)
  - [ ] MECHANICAL: `goc/engine.py` `where`-validation branch mirrors the `who` strip-check
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` passes
worker: {who: "claude[bot]", where: main}
---

# `goc validate` accepts whitespace-only `worker.where`

## Location

`goc/engine.py:1269` — the `where` sub-key validation branch of the
worker validator.

## What's broken

The bare-string `worker` branch and the mapping `who` sub-key both
reject whitespace-only strings; the mapping `where` sub-key rejects
only non-strings:

```python
worker = fm.get("worker")
if worker is not None:
    if isinstance(worker, str):
        if not worker.strip():
            errors.append(f"{t.title}: worker: must not be empty or whitespace-only")
    elif isinstance(worker, dict):
        if "who" not in worker:
            errors.append(f"{t.title}: worker: mapping must have a 'who' key")
        elif not isinstance(worker.get("who"), str) or not worker["who"].strip():
            errors.append(f"{t.title}: worker: 'who' must be a non-empty, non-whitespace string")
        if "where" in worker and not isinstance(worker.get("where"), str):
            errors.append(f"{t.title}: worker: 'where' must be a string")
```

The `where` predicate at line 1269 stops at `isinstance(..., str)`. A
card with `worker: {who: alice, where: "   "}` passes `goc validate`
unchanged.

The just-closed sibling card
[validate-accepts-whitespace-only-worker-as-non-empty](../validate-accepts-whitespace-only-worker-as-non-empty/)
strengthened the bare-string and `who` branches with `.strip()` checks,
but did not extend the same rule to `where`. The
`tests/test_validate_worker_whitespace.py` suite added by that fix
covers bare-string whitespace, mapping `who` whitespace, and the
`who+where` combination — but not the `where`-only case.

## Empirical evidence

Reproducer (run on `927e714` HEAD, the closure commit of the sibling
card):

```
$ uv run python .game-of-cards/deck/validate-accepts-whitespace-only-worker-where-as-non-empty/reproduce.py
validate exit code: 0
validate stderr: (empty)
EXPECTED: nonzero exit + "worker: 'where' must be a non-empty, non-whitespace string"
```

## Why it matters

`worker.where` is a branch hint — it points at the working tree where
a card is being worked on. Filter views (`goc --worker who=alice`,
`GOC_WORKER`) and human readers depend on it being meaningful. A
whitespace-only value is identical-in-meaning to an absent value but
slips past the validator, so two cards that should produce the same
runner-queue view can produce different ones.

**Reachability:** Two paths produce the offending input.

1. **Hand-edited frontmatter.** A user editing a card to add a `where`
   hint can type `worker: {who: alice, where: " "}` (stray space, IDE
   trim-on-save disabled, etc.). `uv run goc validate` reports `OK`.
2. **CLI flag passthrough.** `_auto_populate_worker` in `engine.py`
   (the `goc status <title> active --worker-where "   "` path) writes
   the raw `where` string into the frontmatter via the inline emitter
   without a strip-check. Subsequent `goc validate` reports `OK`.

This is the second instance of the family "validator predicate accepts
whitespace-only where it claims to require non-empty." Filing as a
discrete card (not a meta-fix umbrella) per the audit-deck sibling
rule: meta-fix is filed at the 4th instance, this is the 2nd. The
`meta-fix` tag flags the family lineage so the audit-deck sweep can
count instances cleanly.

## Fix

In `goc/engine.py:1269`, extend the `where` predicate to mirror the
`who` rule:

```python
if "where" in worker:
    if not isinstance(worker.get("where"), str) or not worker["where"].strip():
        errors.append(
            f"{t.title}: worker: 'where' must be a non-empty, non-whitespace string"
        )
```

Add a regression test to `tests/test_validate_worker_whitespace.py`:

```python
def test_mapping_with_whitespace_where_rejected(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        _write_card(cwd, "ws-where", 'worker: {who: alice, where: "  "}')

        result = _run_validate(cwd)

        self.assertNotEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
        self.assertIn(
            "ws-where: worker: 'where' must be a non-empty, non-whitespace string",
            result.stderr,
        )
```

The fix lands in `goc/engine.py` only; the four plugin mirrors
(`claude-plugin/goc/engine.py`, `codex-plugin/goc/engine.py`,
`openclaw-plugin/goc/engine.py`) regenerate via the pre-commit sync.
