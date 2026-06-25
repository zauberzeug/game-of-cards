---
title: goc-advance-claims-success-when-adding-an-already-existing-edge
summary: "`goc advance A --by B` prints a confident `advance: A.advanced_by += B; B.advances += A` message and exits 0 even when the bidirectional edge already exists. Both READMEs are rewritten byte-for-byte unchanged, the auto-commit silently no-ops, and the user (or a script driving `--commit`) is left believing an edge was just added. Symmetric counterpart to `goc-unadvance-claims-success-when-removing-a-non-existent-edge`."
status: open
stage: null
contribution: medium
created: "2026-05-29T19:42:01Z"
closed_at: null
human_gate: decision
advances:
  - mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: reproduce.py exits non-zero (defect no longer fires — running `goc advance` on a pre-existing edge produces a distinct signal from creating a new edge).
  - [ ] PROCESS: decision recorded on whether the failure mode is `exit 2 + ERROR`, `exit 0 + WARNING on stderr`, or `exit 0 + no-op-success message ("edge already exists")`. Match whichever shape the resolved sibling `goc-unadvance-claims-success-when-removing-a-non-existent-edge` picks for analogous non-mutating verb calls.
  - [ ] MECHANICAL: `_cmd_advance` (engine.py:4382) checks edge presence before mutating, OR `_mutate_pair` returns a "no-op" sentinel that `_cmd_advance` honors before printing the success line and entering the auto-commit branch.
  - [ ] TDD: a regression test in `tests/` asserts the chosen signal for the already-existing-edge case.
  - [ ] PROCESS: `uv run goc validate` passes.
---

# `goc advance` claims success when adding an already-existing edge

## Location

- `goc/engine.py:4382-4400` — `_cmd_advance`
- `goc/engine.py:4158-4168` — `_add_to_list_field` (idempotent: returns input text when the value is already present)
- `goc/engine.py:4180-4193` — `_mutate_pair` (writes the result of `_add_to_list_field` back, but exposes no signal when the write was a no-op)

## What's broken

`_cmd_advance` unconditionally prints an "added edge" success message and
enters the auto-commit branch regardless of whether the edge actually
existed beforehand.

```python
# goc/engine.py:4382
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
# goc/engine.py:4158
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
back without telling its caller. `_cmd_advance` therefore never learns
that the requested edge already existed, and reports a confident
"created" outcome where reality is "did nothing." `_git_auto_commit`
(invoked when `--commit`/auto-commit is on) finds no diff and silently
returns False, so the only durable trace of the operation is the
misleading line on stdout.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-advance-claims-success-when-adding-an-already-existing-edge/reproduce.py`
on a clean checkout:

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

The reproducer exits 0 while the defect fires; the DoD flips this so
exit 0 only happens once the fix is in.

## Why it matters

`_cmd_advance` is one of the two CLI surfaces (alongside `_cmd_unadvance`)
through which agents and humans rewrite the deck's value-flow graph. The
verb is reachable through three documented paths:

1. Direct CLI: `goc advance <title> --by <advancer>` — invoked from
   `Skill(advance-card)` when an agent links two existing cards.
2. `goc new --advanced-by <existing>` (`engine.py:4150-4153`) — routes
   through the same `_mutate_pair` codepath. A `goc new` filing that
   re-asserts an already-wired edge would also misreport.
3. `goc repair-edges --execute` (`engine.py:4296`) — repairs half-edges
   by calling `_mutate_pair(..., add=True)` for each missing inverse.
   The repair loop pre-filters to genuinely missing inverses, so this
   path is not currently miscalled — but the misreporting shape lives
   in the shared helper, which means any future caller inherits it.

Concrete failure mode:

- An agent driving `Skill(advance-card)` under `/loop` re-asserts a known
  edge to satisfy an aggregation-epic DoD item. The CLI prints
  `advance: ...`. The agent records "edge added" in `log.md` and moves
  on. The auto-commit no-ops silently, so no git history records the
  outcome either way. A reader investigating "why was this edge added on
  date X" finds nothing — the edge predates the apparent claim.
- More damaging in shell automation: a script using `goc advance ... &&
  git commit -m "deck: B advances A"` will create an empty commit (the
  goc auto-commit is off, but the wrapper's `&&` sees exit 0). The deck
  history accumulates ghost edge-add commits whose diff is empty.

This is the symmetric counterpart to
[goc-unadvance-claims-success-when-removing-a-non-existent-edge](../goc-unadvance-claims-success-when-removing-a-non-existent-edge/),
which catalogues the same defect shape in the remove direction. The
shared root cause (the `_mutate_pair` / `_add_to_list_field` no-op
signal is discarded) suggests one fix touching both verbs, which is why
this card carries the `meta-fix` tag.

## Decision required

Three credible options for the failure mode; pick one and apply to BOTH
add and remove directions consistently:

1. **`exit 2 + ERROR`** — strict, mirrors `cannot advance a card with
   itself`. Maximally clear, but breaks any script that retries
   `goc advance` defensively (the second call is currently a quiet
   success; making it a hard failure changes existing behavior).
2. **`exit 0 + WARNING on stderr`** — backward-compatible: the success
   line still fires on stdout, but a `WARNING: edge already exists`
   joins it on stderr. Scripts keep working; humans get an honest
   signal.
3. **`exit 0 + no-op success message`** — replace the misleading
   `advance: ...` line with a distinct `noop: b.advanced_by already
   contains a; nothing to do`. Same exit code as today, distinct
   stdout, easy to grep.

The right choice depends on the resolution of the sibling card; this
card's fix should land second and adopt whichever shape that card picked
so the two verbs stay symmetric.

## Fix

Once the decision lands, the smallest change is to make `_mutate_pair`
return a tri-state result (`"added" | "noop" | "removed"`) and have
both `_cmd_advance` and `_cmd_unadvance` honor it before printing
the success line and entering the auto-commit branch. The data-layer
idempotency stays; only the CLI's claim about what happened changes.
