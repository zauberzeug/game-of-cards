---
title: goc-unadvance-claims-success-when-removing-a-non-existent-edge
summary: "`goc unadvance A --by B` prints a confident `unadvance: A.advanced_by -= B; B.advances -= A` message and exits 0 even when no edge exists between A and B. The two READMEs are rewritten with their original content (zero diff), the auto-commit silently no-ops, and the user is left believing an edge was removed."
status: open
stage: null
contribution: medium
created: "2026-05-29T19:29:58Z"
closed_at: null
human_gate: decision
advances:
  - mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (defect no longer fires — running `goc unadvance` on a non-existent edge produces a distinct signal from removing a real edge).
  - [ ] PROCESS: decision recorded on whether the failure mode is `exit 2 + ERROR`, `exit 0 + WARNING on stderr`, or `exit 0 + no-op-success message ("no edge to remove")`. Match whichever shape the rest of the engine uses for analogous non-mutating verb calls (e.g. `goc wait --clear` on a card without a wait).
  - [ ] MECHANICAL: `_cmd_unadvance` (engine.py:4403) checks edge presence before mutating, OR `_mutate_pair` returns a "no-op" sentinel that `_cmd_unadvance` honors before printing the success line and entering the auto-commit branch.
  - [ ] TDD: a regression test in `tests/` asserts the chosen signal for the missing-edge case.
  - [ ] PROCESS: `uv run goc validate` passes.
---

# `goc unadvance` claims success when removing a non-existent edge

## Location

- `goc/engine.py:4403-4414` — `_cmd_unadvance`
- `goc/engine.py:4171-4177` — `_remove_from_list_field`
- `goc/engine.py:4180-4193` — `_mutate_pair`

## What's broken

`_cmd_unadvance` unconditionally prints a "removed edge" success message and
enters the auto-commit branch regardless of whether the edge actually existed.

```python
# goc/engine.py:4403
def _cmd_unadvance(args):
    """Remove bidirectional value-flow edge."""
    title = args.title
    advancer = args.advancer
    ...
    _mutate_pair(title, advancer, "advanced_by", "advances", add=False)
    print(f"unadvance: {title}.advanced_by -= {advancer}; {advancer}.advances -= {title}")
    commit_policy = _commit_override(commit, no_commit)
    if auto_commit_enabled(commit_policy):
        if _git_auto_commit([DECK_DIR / title, DECK_DIR / advancer], f"deck: {advancer} no longer advances {title}"):
            print("  committed")
```

The mutation helper it calls is a no-op when the title isn't in the target
field's list:

```python
# goc/engine.py:4171
def _remove_from_list_field(text: str, field: str, title_to_remove: str) -> str:
    fm, body = parse_frontmatter(text)
    cur = fm.get(field) or []
    if title_to_remove not in cur:
        return text
    ...
```

`_mutate_pair` writes the unchanged text back to disk:

```python
# goc/engine.py:4192
(child_dir / "README.md").write_text(op(child_text, field_on_child, parent_title))
(parent_dir / "README.md").write_text(op(parent_text, field_on_parent, child_title))
```

The auto-commit's `git diff --cached --quiet` check then silently returns no
diff (so `_git_auto_commit` returns `False` and the secondary `committed` line
is omitted) — but the *primary* "unadvance:" line at line 4410 already lied.

Contrast with `_cmd_advance` (engine.py:4382), which validates the proposed
edge before mutation — self-edge (line 4388) and cycle (line 4392). Both
checks rely on knowing what the edge set already looks like; checking
"already in / not in" the list would be one more guard in the same shape.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-unadvance-claims-success-when-removing-a-non-existent-edge/reproduce.py`:

```
--- stdout ---
unadvance: alpha.advanced_by -= beta; beta.advances -= alpha
--- stderr ---
--- exit code: 0 ---

DEFECT CONFIRMED:
  - exit code 0 (no error signalled)
  - stdout asserts the edge was removed
  - both README files are byte-identical to their pre-call contents
  - no warning on stderr that the edge did not exist
```

## Why it matters

This is a member of the recurring **"verb mutates without guard" family**
already filed (`goc-attest-mutates-log-md-on-already-closed-cards`,
`goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards`,
`goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard`,
`goc-status-active-discards-worker-overrides-when-target-already-active`).
The shape is different here — the guard isn't about terminal status; it's
about pre-existence of the edge being removed — but the consequence is the
same: a user (or autonomous agent) running a verb that *appears* to act
gets a confident success signal with no acknowledgement that the action was
a no-op.

Reachability: any operator typo of either slug, any race between parallel
agents both running `goc unadvance` on the same edge, and any
hand-written script that calls `unadvance` defensively to ensure an edge is
gone will all hit this path. The audit that surfaced this card found the
defect by walking the verb handlers; it is reachable from every entry point
that calls `_cmd_unadvance`.

The asymmetry with `_cmd_advance` (which DOES check preconditions before
mutating) is the api-contract inconsistency: removing-a-thing should give
the same level of feedback as adding-a-thing.

## Decision required

Three credible failure modes; the engine has analogues for all three and the
project hasn't settled on a convention for "non-mutating verb call":

1. **`exit 2 + ERROR on stderr`** — matches `_cmd_advance`'s self-edge and
   cycle handling (engine.py:4389, 4393). Strictest: a no-op verb call is a
   user error, surface it.
2. **`exit 0 + WARNING on stderr + no success message`** — least disruptive
   to scripts that call `unadvance` defensively; still distinguishable from
   a real removal. Matches the "advisory" tone of the `STALE_BLOCKED` /
   `ORPHAN_BLOCKED` validators.
3. **`exit 0 + "no edge to remove" success line`** — silent acceptance of
   the idempotent shape. Matches `_remove_from_list_field`'s own no-op
   return (engine.py:4174). Least intrusive but loses information.

Whichever shape the implementer picks should also cover the analogous
`goc wait --clear` on a card without a wait (currently unverified — check
`_cmd_wait` for the same pattern when implementing) so the convention
applies consistently across the verb set.

## Fix

Concrete change in `_cmd_unadvance` (engine.py:4403):

```python
def _cmd_unadvance(args):
    title = args.title
    advancer = args.advancer
    ...
    # NEW: inspect edge presence before mutating.
    child_fm, _ = parse_frontmatter((DECK_DIR / title / "README.md").read_text())
    if advancer not in (child_fm.get("advanced_by") or []):
        # Chosen failure mode goes here.
        ...
    _mutate_pair(title, advancer, "advanced_by", "advances", add=False)
    ...
```

Alternative: have `_mutate_pair` (engine.py:4180) return `True` iff at least
one of the two writes changed the file, and let `_cmd_unadvance` branch on
that return. Cleaner because it also catches the rare case where one side of
the bidirectional edge exists but the other doesn't (broken referential
integrity — `goc repair-edges` territory).

Do NOT apply the fix in this card; record the decision in `log.md` and
implement under whichever closure path the project picks.
