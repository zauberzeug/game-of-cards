---
title: attest-treats-dangling-advanced-by-refs-as-closed
summary: "`goc attest` runs the layer-3 `advanced-by-closed` check, which silently drops any `advanced_by` title that is not in the deck — so a card whose every upstream is a dangling reference passes with `all N closed` even though zero upstreams actually exist."
status: open
stage: null
contribution: medium
created: "2026-05-29T15:48:29Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `deck/attest-treats-dangling-advanced-by-refs-as-closed/reproduce.py` exits non-zero on a clean checkout before the fix and exits zero after
  - [ ] TDD: a regression test under `tests/` constructs a card whose `advanced_by` contains only titles absent from `all_cards`, calls `engine._run_derived_check({"name": "advanced-by-closed"}, ...)`, and asserts the result is `(False, <message naming the missing upstream>)`
  - [ ] MECHANICAL: the fix lands in `goc/engine.py` and the surrounding docstring (or a comment at the check site) names the invariant the message is asserting
  - [ ] PROCESS: closure log records which of the two fix options from `## Decision required` was taken and why
---

# attest-treats-dangling-advanced-by-refs-as-closed

## Location

`goc/engine.py:3749-3767` — `_run_derived_check` for the
`advanced-by-closed` layer-3 closure check.

## What's broken

The check filters the "not done" set with `t in by_title and ...`,
which drops dangling references from `unclosed`. When every entry of
`advanced_by` is dangling, `unclosed` is empty and the function
returns the success branch — but the message it returns,
`"all N closed"`, is a lie: not one of the N titles points at a
card in the deck at all, so none of them are "closed" in any
meaningful sense.

```python
# goc/engine.py:3751-3767
if name == "advanced-by-closed":
    advanced_by = card.frontmatter.get("advanced_by") or []
    if not isinstance(advanced_by, list):
        advanced_by = []
    if not advanced_by:
        return True, "no advanced_by edges"
    by_title = {c.title: c for c in all_cards}
    unclosed = [t for t in advanced_by if t in by_title and by_title[t].status not in TERMINAL_STATUSES]
    if unclosed:
        sample = ", ".join(unclosed[:3])
        hint = (
            f"wait for them to close, or if an edge is false, "
            f"retract it: `goc unadvance {card.title} --by <upstream>` "
            f"(prefer over `--skip`)"
        )
        return False, f"{len(unclosed)} not done: {sample} — {hint}"
    return True, f"all {len(advanced_by)} closed"
```

Contrast `validate_supersedes_targets` at `engine.py:1297-1306`,
which uses the same `by_title.get(ref); if target is None: continue`
shape on the record-axis pointer — but that path is paired with the
generic dangling-ref error from `validate_card` at `engine.py:1252`
(`{field}: references unknown title`), which `goc validate` emits
once per dangling entry. `attest` runs `_run_derived_check`
independently and does not consult `validate_card`, so the layer-3
closure gate is satisfied without the dangling-ref invariant
actually holding.

## Empirical evidence

```
$ uv run python -c "
import sys; sys.path.insert(0, '.')
from pathlib import Path
from goc import engine
fm = {'status':'active', 'contribution':'medium', 'human_gate':'none',
      'advanced_by': ['nonexistent-upstream-a', 'nonexistent-upstream-b']}
card = engine.Card(title='dummy', path=Path('/tmp/dummy'), frontmatter=fm,
                   body='', dod_open=0, dod_done=0)
ok, summary = engine._run_derived_check(
    {'name':'advanced-by-closed'}, card, [card], '2026-05-29')
print(f'passed={ok}  summary={summary!r}')
"
passed=True  summary='all 2 closed'
```

The function reports `passed=True` and `'all 2 closed'` for a card
whose two declared upstreams do not exist in the deck. See
`reproduce.py` for the packaged version.

## Why it matters

The reachability path is concrete: a hand-edit to `advanced_by`,
a `goc move` on an upstream that did not propagate, or any
direct-write to a frontmatter list field can leave dangling
entries. (The `bare-string-scalars-on-list-fields` meta-fix family
documents that this is a real failure mode.) Once dangling refs
exist, `goc validate` correctly errors — but `goc attest` (which
gates `goc done` closure via the attestation block in `log.md`)
runs the layer-3 check in isolation and reports `[x]
advanced-by-closed — all N closed`. The closure log then carries a
recorded success message that is empirically false, and a card
closes with the value-flow invariant unverified.

The defect class is "closure-gate check reports PASS on input it
cannot evaluate, instead of FAIL." It is the same shape as the
disproved card `dod-rewrite-trailing-newline-reconstruction-is-inverted`
in spirit (a derivation function returning a non-defensible result
on edge inputs) but lives in a different module and is
reproducible. See sibling unverified candidates surfaced in the
same audit pass:

- `advanced-by-closed-counts-skipped-dangling-refs-in-the-pass-message`
  (low; companion drift — `len(advanced_by)` counts dangling refs
  in the partial-dangling case)
- `validate-supersedes-targets-silently-skips-dangling-refs`
  (low; symmetric shape in the record-axis pointer check)

If the fix lands in `_run_derived_check`, the sibling unverifieds
should be re-evaluated as part of the close — both share the
`by_title.get / in by_title` blind spot.

## Decision required

Two credible fix paths; pick one before implementing:

**Option A — make the check itself dangling-aware.** Split the
filter so dangling refs are counted as "not done" and surfaced
with a distinct, accurate message:

```python
by_title = {c.title: c for c in all_cards}
missing = [t for t in advanced_by if t not in by_title]
unclosed = [t for t in advanced_by if t in by_title and by_title[t].status not in TERMINAL_STATUSES]
problems = missing + unclosed
if problems:
    parts = []
    if missing:
        parts.append(f"{len(missing)} unknown: {', '.join(missing[:3])}")
    if unclosed:
        parts.append(f"{len(unclosed)} not done: {', '.join(unclosed[:3])}")
    return False, "; ".join(parts) + " — " + hint
return True, f"all {len(advanced_by)} closed"
```

Localized to the check; matches the layer-3 reader's expectations
("if attest passes, the invariant holds"); independent of validate.

**Option B — make attest cross-call validate first.** Have
`_cmd_attest` run `validate_card(card, all_titles)` before any
layer-3 check and abort with a non-zero exit if dangling refs
exist. Single source of truth for "the frontmatter is internally
consistent," but introduces an attest → validate coupling and
changes attest's exit semantics (a new failure mode before the
checks even run).

The audit author leans A for locality and minimal blast radius, but
B is the right call if the project wants attest to consistently
refuse to evaluate inconsistent input.

## Fix

Apply the chosen option above, run the regression suite, run the
reproducer, and re-evaluate the two sibling unverified candidates
listed in "Why it matters" against the chosen fix's call sites.
