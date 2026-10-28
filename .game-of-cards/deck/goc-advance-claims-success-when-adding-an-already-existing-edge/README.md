---
title: goc-advance-claims-success-when-adding-an-already-existing-edge
summary: "`goc advance A --by B` printed `advance: A.advanced_by += B; B.advances += A` and exited 0 when the bidirectional edge already existed — both READMEs rewritten byte-identical, the auto-commit a silent no-op — so a re-add looked exactly like a new edge. It now refuses (exit 2, `ERROR: cannot add B → A: the edge already exists`, nothing written) when both halves of the edge are listed, through the parent epic's shared `_refuse_invalid_input` helper and ahead of the cycle guard; a new edge, or a dangling half of one, is still added. Symmetric counterpart to `goc-unadvance-claims-success-when-removing-a-non-existent-edge`."
status: done
stage: null
contribution: medium
created: "2026-05-29T19:42:01Z"
closed_at: "2026-10-28T04:44:52Z"
human_gate: none
advances:
  - mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (defect no longer fires — running `goc advance` on a pre-existing edge produces a distinct signal from creating a new edge). — the edge already in place gets exit 2, `ERROR:` on stderr, no success line and both READMEs untouched, while the first call, which adds the edge, gets exit 0 and the success line; the same script exits 1 against the pre-fix engine. Reworded from `exits non-zero`, which matched the inverted original script.
  - [x] PROCESS: decision recorded on whether the failure mode is `exit 2 + ERROR`, `exit 0 + WARNING on stderr`, or `exit 0 + no-op-success message ("edge already exists")`. Match whichever shape the resolved sibling `goc-unadvance-claims-success-when-removing-a-non-existent-edge` picks for analogous non-mutating verb calls. — decided 2026-10-22 via the parent epic: strict-refuse (exit 2).
  - [x] MECHANICAL: `_cmd_advance` (engine.py:6565) checks edge presence before mutating, OR `_mutate_pair` returns a "no-op" sentinel that `_cmd_advance` honors before printing the success line and entering the auto-commit branch. — `_cmd_advance` checks before `_mutate_pair`: both halves listed is refused through `_refuse_invalid_input` ahead of any write and of the cycle guard; one listed half is completed as before.
  - [x] TDD: a regression test in `tests/` asserts the chosen signal for the already-existing-edge case. — `AdvanceCliTest` in `tests/test_mutation_verbs_refuse_invalid_input.py`; 3 of its 6 tests fail against the pre-fix engine, as does the `advance` row of `tests/test_verb_rerun_safety.py`, now `REFUSES`.
  - [x] PROCESS: `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# `goc advance` claims success when adding an already-existing edge

## Location

- `goc/engine.py` `_cmd_advance` — printed the addition line and entered
  the auto-commit branch without checking whether the edge was already in
  place; it now checks first.
- `goc/engine.py` `_add_to_list_field` / `_mutate_pair` — the idempotent
  add and the byte-identical rewrite behind the false success line
  (unchanged).

## What was broken

Before the fix, `_cmd_advance` unconditionally printed an "added edge"
success message and entered the auto-commit branch regardless of whether
the edge already existed. The excerpts and line numbers below are the
pre-fix code.

```python
# goc/engine.py:6565
def _cmd_advance(args):
    """Add bidirectional value-flow edge: title.advanced_by += advancer, advancer.advances += title."""
    title = args.title
    advancer = args.advancer
    commit = args.commit
    no_commit = args.no_commit
    if title == advancer:
        print("ERROR: cannot advance a card with itself", file=sys.stderr)
        sys.exit(2)
    cards = load_all_cards()
    if _would_create_advance_cycle(cards, title, advancer):
        print(f"ERROR: adding {advancer} → {title} would create a cycle in the advances graph", file=sys.stderr)
        sys.exit(2)
    _mutate_pair(title, advancer, "advanced_by", "advances", add=True)
    print(f"advance: {title}.advanced_by += {advancer}; {advancer}.advances += {title}")
    commit_policy = _commit_override(commit, no_commit)
    if auto_commit_enabled(commit_policy):
        if _git_auto_commit([DECK_DIR / title, DECK_DIR / advancer], f"deck: {advancer} advances {title}"):
            print("  committed")
```

`_add_to_list_field` is correctly idempotent at the data layer:

```python
# goc/engine.py:6308
def _add_to_list_field(text: str, field: str, title_to_add: str) -> str:
    """Add title_to_add to a frontmatter list field, idempotent."""
    fm, body = parse_frontmatter(text)
    cur = fm.get(field) or []
    if not isinstance(cur, list):
        raise ValueError(f"{field}: not a list")
    if title_to_add in cur:
        return text   # <-- silent no-op signal
    cur.append(title_to_add)
    fm[field] = cur
    return emit_frontmatter(fm, body=body)
```

…but `_mutate_pair` discards the signal — it writes the unchanged text
back without telling its caller. `_cmd_advance` therefore never learned
that the requested edge already existed, and reported a confident
"created" outcome where reality was "did nothing." `_git_auto_commit`
(invoked when `--commit`/auto-commit is on) found no diff and silently
returned False, so the only durable trace of the operation was the
misleading line on stdout.

## Empirical evidence

As filed, the original reproducer showed the false success:

```text
=== Call 1: goc advance b --by a (edge does NOT yet exist) ===
  stdout: 'advance: b.advanced_by += a; a.advances += b'
  sha256(a/README.md)[:12]: 1aca8b8f80a4
  sha256(b/README.md)[:12]: 593066d8d1c6

=== Call 2: goc advance b --by a (edge ALREADY exists) ===
  stdout: 'advance: b.advanced_by += a; a.advances += b'
  sha256(a/README.md)[:12]: 1aca8b8f80a4
  sha256(b/README.md)[:12]: 593066d8d1c6

=== Verdict ===
  Call 2 prints the same success line as call 1?  True
  Call 2 left both READMEs byte-for-byte unchanged? True
  DEFECT FIRES (claims-success-on-no-op): True
```

That reproducer exited 0 while the defect fired. After the fix,
`uv run python .game-of-cards/deck/goc-advance-claims-success-when-adding-an-already-existing-edge/reproduce.py`
exits 0 (the reproducer contract: 0 = defect no longer fires, 1 = fires,
2 = harness broken):

```text
$ goc advance beta --by alpha   # edge not yet in place
  exit 0
  stdout: advance: beta.advanced_by += alpha; alpha.advances += beta
  stderr: (empty)
$ goc advance beta --by alpha   # edge already in place
  exit 2
  stdout: (empty)
  stderr: ERROR: cannot add alpha → beta: the edge already exists — beta.advanced_by lists alpha and alpha.advances lists beta

FIXED: an edge already in place is refused with nothing written; a new edge is still added.
```

Against the pre-fix engine the same script exits 1 (`DEFECT FIRES`).

## Why it matters

`_cmd_advance` is one of the two CLI surfaces (alongside `_cmd_unadvance`)
through which agents and humans rewrite the deck's value-flow graph. Three
documented paths reach the shared add helper `_mutate_pair(..., add=True)`:

1. Direct CLI: `goc advance <title> --by <advancer>` — invoked from
   `Skill(advance-card)` when an agent links two existing cards. This is
   the path that misreported.
2. `goc new --advances <existing>` / `--advanced-by <existing>` — the new
   card starts with empty edge lists and repeated flags are deduplicated
   (`_unique_preserving_order`), so at most one half of an edge can
   already be in place; the call is never a full no-op.
3. `goc repair-edges --apply` — repairs half-edges by calling
   `_mutate_pair(..., add=True)` for each missing inverse. The repair loop
   pre-filters to genuinely missing inverses, so this path is not
   miscalled either.

`_mutate_pair` itself still reports nothing about a no-op, so a future
caller that can hand it an edge already in place needs its own check, the
way `_cmd_advance` and `_cmd_unadvance` now have one.

Concrete failure mode:

- An agent driving `Skill(advance-card)` under `/loop` re-asserts a known
  edge to satisfy an aggregation-epic DoD item. The CLI prints
  `advance: ...`. The agent records "edge added" in `log.md` and moves
  on. The auto-commit no-ops silently, so no git history records the
  outcome either way. A reader investigating "why was this edge added on
  date X" finds nothing — the edge predates the apparent claim.
- More damaging in shell automation: a script chaining
  `goc advance ... && git commit ...` sees exit 0 and proceeds as though
  an edge landed, so its own record of the deck's history claims an edge
  addition whose diff is empty.

This is the symmetric counterpart to
[goc-unadvance-claims-success-when-removing-a-non-existent-edge](../goc-unadvance-claims-success-when-removing-a-non-existent-edge/),
which catalogued the same defect shape in the remove direction and
closed first, introducing the shared refusal helper this fix reuses.

## Decision

*Resolved 2026-10-22T05:20:21Z:* Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: option 1, exit 2 + ERROR — adding an already-existing edge is refused and mutates nothing, symmetric with the unadvance sibling

*Reasoning:* The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question

## Fix

`_cmd_advance` loads both cards and checks the edge before `_mutate_pair`,
mirroring the guard its sibling put in `_cmd_unadvance`:

- **Both halves listed** — `<title>.advanced_by` names the advancer and
  `<advancer>.advances` names the title. There is nothing to add, so it
  refuses through the parent epic's shared `_refuse_invalid_input`:
  `ERROR: cannot add <advancer> → <title>: the edge already exists — …`,
  exit 2, nothing written.
- **One half listed** — a dangling half a hand edit left behind.
  Completing it is a real addition, so it proceeds as before.
- **Neither listed** — a new edge, unchanged.

The check runs ahead of the cycle guard, so an edge already inside a
hand-built cycle is refused as existing rather than as a cycle the call
would not create. An edge already running the other way
(`<title> → <advancer>`) is not the edge being added; the cycle guard
still refuses it as before.

The fix sketch filed with this card — a tri-state `_mutate_pair` result
honored by both verbs — was not used, for the reason the sibling gave: it
writes first and asks afterwards, while the decision requires that a
refusal write nothing.

A second `goc advance` of the same edge is now refused instead of
re-emitting both cards, so `tests/test_verb_rerun_safety.py` declares
`advance` `REFUSES` (was `RE_EMITS`). The regression cases sit beside the
sibling's in `tests/test_mutation_verbs_refuse_invalid_input.py`.
