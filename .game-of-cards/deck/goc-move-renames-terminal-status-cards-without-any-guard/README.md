---
title: goc-move-renames-terminal-status-cards-without-any-guard
summary: "`goc move <old> <new>` renames a card directory and rewrites every cross-reference across the tracked tree with no terminal-status check. Calling it on a `done` / `disproved` / `superseded` card silently retitles the card and rewrites historical links to the old slug — the kanban record axis the closed card sits on. Sibling in the same meta-fix family already in flight as `goc-decide-accepts-decisions-on-already-closed-cards` (closed; guard added at engine.py:4556), `goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard` (open), `goc-attest-mutates-log-md-on-already-closed-cards` (open), and `goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards` (open). That last card's DoD step 4 explicitly flags `_cmd_move` as a follow-up audit; this card is that follow-up."
status: open
stage: null
contribution: medium
created: "2026-06-01T05:26:39Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: pick the guard shape from `## Decision required` and record the choice via `Skill(decide-card)` (lowers the gate to `none`).
  - [ ] TDD: reproduce.py exits zero — a two-card fixture (one `done`, one `open`) runs `goc move <done> <new>` and the chosen guard either rejects with a non-zero exit + clear error (option a) or refuses to write while letting Layer-1 prose stay legible (option b); the done card's directory is unchanged on disk; the open-card rename path remains green via a paired positive case.
  - [ ] MECHANICAL: implement the chosen guard in `goc/engine.py` (`_cmd_move`, line 4780) and re-sync plugin mirrors via `python scripts/sync_plugin_assets.py`.
  - [ ] PROCESS: sibling sweep — confirm `_apply_verdict_interactive` (engine.py:3300-3313) inherits the new guard via its `goc move` subprocess call (defense-in-depth — the parent quality-pass card has its own entry-point guard but the move subprocess hop is a second seam); add a regression test if the inheritance is not obvious from code reading.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` stays green; `uv run goc validate` clean.
---

# `goc move` renames terminal-status cards without any guard

## Location

- `goc/engine.py:4780-4838` — `_cmd_move` (no terminal-status check at the entry point or before mutation)
- `goc/engine.py:4710-4779` — `_move_text_rewrite` / `_move_rewrite_tracked_files` (repo-wide reference rewrite; runs unconditionally)
- `goc/engine.py:3300-3313` — `_apply_verdict_interactive` shells out to `goc move` via `subprocess.run`, so the unguarded entry point is the seam through which the quality-pass LLM rewrite path also acts on terminal cards.

## What's broken

`_cmd_move` loads neither the schema nor the card frontmatter before mutating. The only pre-mutation checks are the jargon-antipattern guard on the *new* title, the title-pattern regex, source-exists, and dest-does-not-exist:

```python
def _cmd_move(args):
    """Rename a title and rewrite known cross-references."""
    old_title = args.old_title
    new_title = args.new_title
    ...
    src = DECK_DIR / old_title
    dst = DECK_DIR / new_title
    if not src.exists():
        print(f"ERROR: {src} does not exist", file=sys.stderr)
        sys.exit(2)
    if dst.exists():
        print(f"ERROR: {dst} already exists", file=sys.stderr)
        sys.exit(2)
    ...
    subprocess.run(["git", "mv", str(src), str(dst)], cwd=REPO_ROOT, check=True, capture_output=True)
    ...
    _move_rewrite_tracked_files(old_title, new_title)
    ...
```

The recently-added guard in `_cmd_decide` (`goc/engine.py:4862-4867`) is the shape the move verb is missing — except `_cmd_decide` rejects with `gate already 'none'`, which is the gate analogue of the status analogue we want here. The terminal-status guard that `_cmd_decide` carries via its closed-status rejection sibling, and that `goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard` proposes to add to `_cmd_wait`, is absent from `_cmd_move`.

Compare also to `_cmd_status` (`goc/engine.py:4252-4258`), which has the inverse — refusing to move a terminal card *backward* through `goc status`:

```python
if prior in TERMINAL_STATUSES:
    print(
        f"ERROR: {title}: status is {prior!r} (terminal);"
        f" terminal cards cannot be moved backward through `goc status`",
        file=sys.stderr,
    )
    sys.exit(2)
```

The closed-card immutability principle is enforced at every state-flip verb except `move`, `wait`, `attest`, and (until recently) `decide` and `quality-pass`. `move` is the last of the cluster without a closed-card audit.

## Empirical evidence

Reachable in two ways:

1. **Direct.** A maintainer running `uv run goc move <closed-title> <new-title>` is the unit case. The CLI prints `<old> → <new>` and the rename + cross-reference rewrites land in the worktree (uncommitted, per the separate `goc-move-leaves-cross-reference-rewrites-uncommitted` defect). The closed card's directory name, frontmatter title, log.md headings, and every cross-reference in the tracked tree are now retconned.

2. **Via quality-pass.** `_apply_verdict_interactive` shells out to `goc move` when the Sonnet pass proposes a title rewrite (see `_apply_verdict_interactive` at engine.py:3300-3313). The parent card `goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards` proposes guarding the entry point of `_cmd_quality_pass` (Layer-2 LLM sample filter) or the summary/DoD helpers; even with that guard in place, the title-rewrite branch reaches `_cmd_move` via subprocess and there is no inherited protection. The quality-pass card's DoD step 4 explicitly flags this as a follow-up audit:

> **PROCESS: sibling sweep** — confirm `_cmd_move` (engine.py:4487) does or does not need its own terminal-status guard; file a follow-up card if the audit reveals `goc move` standalone is also unguarded (the quality-pass path invokes `move` via subprocess and would benefit from defense-in-depth).

This card is that follow-up. (The line-number reference 4487 in the parent card is stale — `_cmd_move` is now at engine.py:4780. The function is unchanged in behavior.)

## Why it matters

A closed card is the kanban system's durable artefact: it records the title (and therefore the slug, the directory name, the URL fragments, every backref in the tracked tree) that the work was filed under. The deck-as-record axis depends on stable identifiers — a future reader following a closed card's `superseded_by` pointer or scanning `log.md` for archived deliberation expects the slug they were given to still resolve. Silently retitling a closed card breaks every existing pointer to it.

The same principle was codified in `closed-cards-stay-editable-with-cross-references` (closed): *appending* to `log.md` when new evidence surfaces is encouraged; silently rewriting the frontmatter contract is not. The move verb's reference-rewrite pass goes further — it edits other cards' bodies and arbitrary tracked files to substitute the new slug, so a single `goc move` call on a closed card can rewrite history across the whole repo.

Reachability: the most concerning path is the quality-pass subprocess hop (above). A maintainer who runs `goc quality-pass --status all --llm --yes` to clean up jargon-titles project-wide, after the parent card lands its entry-point filter for summary/DoD, would still silently rename closed cards through the `move` subprocess unless this card lands its guard too.

## Decision required

The cluster of unguarded mutation verbs has three documented fix shapes (see the sibling cards' decision sections). For `_cmd_move` specifically:

- **(a) Verb-level error**: `_cmd_move` loads the card via `load_card_or_exit`, checks `t.status in TERMINAL_STATUSES`, and rejects with a clear message pointing to the supersede workflow. Matches the post-fix `_cmd_decide` shape — fail loudly. Cost: a `goc move` on a closed card during a legitimate batch retitle (e.g. a deck-wide slug normalization) becomes a per-card override.
- **(b) Verb-level warning + `--force`**: `_cmd_move` warns when the target is terminal but proceeds, with a `--force` flag to silence the warning. Cost: defaulting to `proceed` keeps the silent-mutation hazard; the warning lives only in the operator's terminal scrollback.
- **(c) Verb-level error with `--force` escape hatch**: `_cmd_move` rejects on terminal status by default and accepts `--force` to bypass. Combines (a)'s defense-in-depth with (b)'s ergonomic escape for the deck-wide-rename case. Matches the `goc done` shape (`--force` bypasses DoD-checkbox enforcement for free-form DoD cards).

Recommendation: **(c)** — reject by default with `--force` to bypass. The kanban record-axis defaults to immutability; deliberate retitles of closed cards (slug normalization sweeps, post-hoc clarifications) are rare enough that an explicit `--force` per call is the right ergonomic. Aligns with the `goc done --force` precedent for the orthogonal DoD-enforcement bypass.

Independent of (a/b/c), record the chosen shape's interaction with the quality-pass subprocess (DoD step 4): does the new guard surface back through the subprocess exit code, and does `_apply_verdict_interactive`'s `r.returncode == 0` check at engine.py:3309 already DTRT (printing the failure to stderr and skipping the title-applied bookkeeping) or does it need its own log line clarifying that the closed-card path is the intended rejection rather than a generic move failure?

## Sibling sweep

The same root cause — mutation verb missing terminal-status guard — has cards in flight across the family:

- [goc-decide-accepts-decisions-on-already-closed-cards](../goc-decide-accepts-decisions-on-already-closed-cards/) (closed) — guard added at engine.py:4862
- [goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard](../goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard/) (open)
- [goc-attest-mutates-log-md-on-already-closed-cards](../goc-attest-mutates-log-md-on-already-closed-cards/) (open)
- [goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards](../goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards/) (open; parent card whose DoD step 4 commissioned this audit)

Five sibling instances now (decide + wait + attest + quality-pass + move) is the threshold the audit-deck guidance treats as a meta-fix candidate. An umbrella `terminal-status-guard-missing-across-mutation-verbs` epic that collects these into one design decision (one guard shape applied to all five verbs at once, with a shared helper) is a defensible follow-up, but is out of scope for this card's filing — file it separately if the decision-resolution pass on these five cards converges on a single shape.
