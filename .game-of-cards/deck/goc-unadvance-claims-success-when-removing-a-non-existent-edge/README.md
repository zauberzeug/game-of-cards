---
title: goc-unadvance-claims-success-when-removing-a-non-existent-edge
summary: "`goc unadvance A --by B` printed `unadvance: A.advanced_by -= B; B.advances -= A` and exited 0 when no edge existed between A and B — both READMEs rewritten byte-identical, the auto-commit a silent no-op — so a missing edge looked exactly like a removed one. It now refuses (exit 2, `ERROR: cannot remove B → A: no such edge`, nothing written) when neither half of the edge is listed, through the parent epic's new shared `_refuse_invalid_input` helper, and names the reversed command when the edge runs the other way; a real edge, or a dangling half of one, is still removed."
status: done
stage: null
contribution: medium
created: "2026-05-29T19:29:58Z"
closed_at: "2026-10-28T04:34:09Z"
human_gate: none
advances:
  - mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (defect no longer fires — running `goc unadvance` on a non-existent edge produces a distinct signal from removing a real edge). — the missing edge gets exit 2, `ERROR:` on stderr, no success line and both READMEs untouched, while the real-edge control gets exit 0 and the success line; the same script exits 1 against the pre-fix engine.
  - [x] PROCESS: decision recorded on whether the failure mode is `exit 2 + ERROR`, `exit 0 + WARNING on stderr`, or `exit 0 + no-op-success message ("no edge to remove")`. Match whichever shape the rest of the engine uses for analogous non-mutating verb calls (e.g. `goc wait --clear` on a card without a wait). — decided 2026-10-22 via the parent epic: strict-refuse (exit 2).
  - [x] MECHANICAL: `_cmd_unadvance` (engine.py:6535) checks edge presence before mutating, OR `_mutate_pair` returns a "no-op" sentinel that `_cmd_unadvance` honors before printing the success line and entering the auto-commit branch. — `_cmd_unadvance` checks before `_mutate_pair`: either half listed passes, neither listed is refused through `_refuse_invalid_input` ahead of any write.
  - [x] TDD: a regression test in `tests/` asserts the chosen signal for the missing-edge case. — `tests/test_mutation_verbs_refuse_invalid_input.py`; 4 of its 6 tests fail against the pre-fix engine.
  - [x] PROCESS: `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# `goc unadvance` claims success when removing a non-existent edge

## Location

- `goc/engine.py` `_cmd_unadvance` — printed the removal line and entered
  the auto-commit branch without checking that the edge existed; it now
  checks first.
- `goc/engine.py` `_refuse_invalid_input` — the parent epic's shared
  strict-refuse emission, added with this fix.
- `goc/engine.py` `_remove_from_list_field` / `_mutate_pair` — the no-op
  removal and the byte-identical rewrite behind the false success line
  (unchanged).

## What was broken

Before the fix, `_cmd_unadvance` unconditionally printed a "removed edge"
success message and entered the auto-commit branch regardless of whether the
edge actually existed. The excerpts and line numbers below are the pre-fix
code.

```python
# goc/engine.py:6587
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
# goc/engine.py:6321
def _remove_from_list_field(text: str, field: str, title_to_remove: str) -> str:
    fm, body = parse_frontmatter(text)
    cur = fm.get(field) or []
    if title_to_remove not in cur:
        return text
    ...
```

`_mutate_pair` writes the unchanged text back to disk:

```python
# goc/engine.py:6342
(child_dir / "README.md").write_text(op(child_text, field_on_child, parent_title))
(parent_dir / "README.md").write_text(op(parent_text, field_on_parent, child_title))
```

The auto-commit's `git diff --cached --quiet` check then silently returns no
diff (so `_git_auto_commit` returns `False` and the secondary `committed` line
is omitted) — but the *primary* "unadvance:" line at line 4410 already lied.

Contrast with `_cmd_advance` (engine.py:6565), which validates the proposed
edge before mutation — self-edge (line 4388) and cycle (line 4392). Both
checks rely on knowing what the edge set already looks like; checking
"already in / not in" the list would be one more guard in the same shape.

## Empirical evidence

As filed, the original reproducer showed the false success:

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

After the fix,
`uv run python .game-of-cards/deck/goc-unadvance-claims-success-when-removing-a-non-existent-edge/reproduce.py`
exits 0 (the reproducer contract: 0 = defect no longer fires, 1 = fires,
2 = harness broken):

```
$ goc unadvance alpha --by beta   # no such edge
  exit 2
  stdout: (empty)
  stderr: ERROR: cannot remove beta → alpha: no such edge — alpha.advanced_by does not list beta and beta.advances does not list alpha
$ goc unadvance delta --by gamma  # real edge
  exit 0
  stdout: unadvance: delta.advanced_by -= gamma; gamma.advances -= delta

FIXED: a non-existent edge is refused with nothing written; a real edge is still removed.
```

Against the pre-fix engine the same script exits 1 (`DEFECT FIRES`).

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

## Decision

*Resolved 2026-10-22T05:20:22Z:* Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: option 1, exit 2 + ERROR on stderr — removing a non-existent edge is refused, symmetric with the advance sibling

*Reasoning:* The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question

## Fix

`_cmd_unadvance` loads both cards and checks the edge before `_mutate_pair`
runs:

- **Either half listed → remove.** `title.advanced_by` naming `advancer`, or
  `advancer.advances` naming `title`, is enough: a hand edit can leave one
  half of an edge dangling, and `goc unadvance` is how it gets removed. That
  covers the half-edge case the `_mutate_pair`-sentinel alternative was
  preferred for, without writing first and asking afterwards.
- **Neither listed → refuse** through `_refuse_invalid_input`:
  `ERROR: cannot remove <advancer> → <title>: no such edge …` on stderr,
  exit 2, before any write — the READMEs are not rewritten and the
  auto-commit branch is never reached.
- **The edge runs the other way** (`title` advances `advancer`) → the same
  refusal also names `goc unadvance <advancer> --by <title>`. A swapped
  spelling is one way to land here: `goc validate`'s `BACKWARDS_EPIC_EDGE`
  hint prints one
  ([validate-backwards-epic-edge-fix-suggestion-has-swapped-command-arguments](../validate-backwards-epic-edge-fix-suggestion-has-swapped-command-arguments/)).

`_refuse_invalid_input(reason)` is the parent epic's decided factoring: one
shared emission (`ERROR: <reason>`, exit 2) with each verb's predicate
inline. `_cmd_advance`'s self-edge and cycle refusals now go through it too,
with byte-identical output, so the pair's refusals cannot drift apart. The
prefix is `ERROR:`, the one every mutation verb's precondition refusal
already prints; `goc: error:` belongs to the query-flag parser.

A second `goc unadvance` of the same edge is now refused rather than
re-emitting both cards, so `tests/test_verb_rerun_safety.py` declares
`unadvance` `REFUSES` (was `RE_EMITS`).

Tests: `tests/test_mutation_verbs_refuse_invalid_input.py` pins the helper's
contract; the refusal (exit 2, no success line, deck byte-identical) for no
edge, for a re-run after the removal, and for the swapped direction (with
the reversed command named); and that a real edge and either dangling half
are still removed. The family's remaining children add their verb's cases
there.

Unchanged, out of scope: `goc unadvance <t> --by <t>` on a card that carries
a self-edge passes this guard (a half is listed) and still leaves the
half-edge — that is the gated
[goc-unadvance-with-self-target-leaves-card-in-half-edge-state](../goc-unadvance-with-self-target-leaves-card-in-half-edge-state/).
Without a self-edge the call is now refused as a missing edge.
