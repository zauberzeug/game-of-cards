---
title: goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards
summary: "`goc quality-pass --status all|done|disproved|superseded --llm [--yes]` runs the Sonnet rewrite pass over terminal-status cards (done/disproved/superseded). Accepted verdicts mutate `summary` and `definition_of_done` frontmatter in place via `_apply_summary_rewrite` / `_apply_dod_rewrite`, and propose title renames via `goc move` (which also lacks a terminal guard). Closed cards are immutable records of what was contracted and met; the verb has no terminal-status guard at the entry point or in the mutation helpers. Sibling pattern to `goc-decide-accepts-decisions-on-already-closed-cards` (closed, guard added at engine.py:4556), `goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard` (open), and `goc-attest-mutates-log-md-on-already-closed-cards` (open)."
status: open
stage: null
contribution: medium
created: "2026-05-29T18:59:23Z"
closed_at: null
human_gate: decision
advances:
  - terminal-status-guard-missing-across-mutation-verbs
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: pick the guard shape — (a) `_cmd_quality_pass` filters terminal-status cards out of the LLM sample regardless of `--status` value (Layer-1 antipattern scan still runs over them; Layer-2 LLM rewrites do not), OR (b) `_cmd_quality_pass` errors when `--llm` is combined with a `--status` value that selects terminal cards, OR (c) the mutation helpers (`_apply_summary_rewrite`, `_apply_dod_rewrite`) refuse with a clear error when the target card is terminal. Record the choice + reasoning in `## Decision required` (see body).
  - [ ] TDD: reproduce.py exits zero — a two-card deck (one open, one done) runs `goc quality-pass --status all --llm --yes` with a stub Sonnet response that proposes summary + DoD rewrites for both cards; the open card is rewritten, the done card's `summary` and `definition_of_done` are unchanged on disk.
  - [ ] MECHANICAL: implement the chosen guard in `goc/engine.py` and re-sync plugin mirrors via `python scripts/sync_plugin_assets.py`.
  - [ ] PROCESS: sibling sweep — confirm `_cmd_move` (engine.py:4487) does or does not need its own terminal-status guard; file a follow-up card if the audit reveals `goc move` standalone is also unguarded (the quality-pass path invokes `move` via subprocess and would benefit from defense-in-depth).
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` stays green.
---

# `goc quality-pass --llm` mutates summary and DoD on terminal-status cards

## Location

- `goc/engine.py:3132-3211` — `_cmd_quality_pass` (no terminal filter when `--status` selects terminal cards)
- `goc/engine.py:3051-3056` — `_apply_summary_rewrite` (no terminal guard)
- `goc/engine.py:3059-3076` — `_apply_dod_rewrite` (no terminal guard)
- `goc/engine.py:3079-3129` — `_apply_verdict_interactive` (orchestrator; no terminal guard)
- `goc/engine.py:2576` — argparser: `--status` default is `open` (safe); `all|done|disproved|superseded` open the hole

## What's broken

`_cmd_quality_pass` loads cards and applies the `--status` filter, defaulting to `open`. With `--status all`, terminal cards (`done`, `disproved`, `superseded`) flow through to the Layer-2 LLM sample. With `--status done` / `--status disproved` / `--status superseded`, the sample is exclusively terminal. The `_apply_verdict_interactive` orchestrator then offers — and with `--yes` auto-applies — three rewrite operations against those cards:

```python
# goc/engine.py:3140-3142
cards = load_all_cards()
if status_flag != "all":
    cards = [c for c in cards if c.status == status_flag]
```

```python
# goc/engine.py:3194-3205
for verdict in verdicts:
    if _render_verdict(verdict):
        rewrite_count += 1
        if not dry_run:
            card = by_title.get(verdict.get("title", ""))
            if card is None:
                print("    (card not found in sample; skipping apply)", file=sys.stderr)
                continue
            applied = _apply_verdict_interactive(card, verdict, auto_yes=auto_yes)
```

`_apply_summary_rewrite` and `_apply_dod_rewrite` mutate the README frontmatter directly with no status check:

```python
# goc/engine.py:3051-3056
def _apply_summary_rewrite(card: Card, new_summary: str) -> None:
    """In-place YAML-safe rewrite of the `summary:` field on this card's README.md."""
    readme = card.path / "README.md"
    text = readme.read_text()
    rewritten = mutate_frontmatter_field(text, "summary", _yaml_inline(new_summary))
    readme.write_text(rewritten)
```

```python
# goc/engine.py:3059-3076
def _apply_dod_rewrite(card: Card, issues: list[dict]) -> None:
    """Replace specific DoD items by 0-based index. Other items preserved verbatim."""
    readme = card.path / "README.md"
    text = readme.read_text()
    fm, body = parse_frontmatter(text)
    ...
    fm["definition_of_done"] = "\n".join(lines) + ("\n" if not dod_text.endswith("\n") else "")
    readme.write_text(emit_frontmatter(fm, body=body))
```

Compare the recently-added guard in `_cmd_decide` (engine.py:4556):

```python
if t.status in TERMINAL_STATUSES:
    print(
        f"ERROR: {title}: status is {t.status!r} (terminal); "
        f"`goc decide` records a *pending* decision — terminal cards "
        f"cannot be re-decided. To replace a recorded decision, file "
        f"a new card and link it via `goc status <old> superseded --by <new>`.",
        file=sys.stderr,
    )
    sys.exit(2)
```

The same shape is missing from `_cmd_quality_pass` and its mutation helpers.

## Why it matters

A closed card is the kanban system's durable artefact: it records the title, summary, and DoD contract the work was held to. The sibling card `closed-cards-stay-editable-with-cross-references` (closed) endorses *appending* `log.md` entries when new evidence surfaces — explicitly so a future reader can reconstruct the learning thread without the frontmatter contract being silently retconned. Quality-pass's LLM rewrite path silently retcons the frontmatter contract instead.

Reachability: a maintainer running `goc quality-pass --status all --llm --yes` to clean up jargon-titles project-wide will silently rewrite closed cards' summaries and DoD items along with the open ones. The Layer-1 antipattern scan (title check + missing-summary scan) is informational only and safe across all statuses; the Layer-2 LLM rewrite path is the unsafe one.

`_cmd_move` (engine.py:4487) also lacks a terminal-status guard, so the title-rename branch in `_apply_verdict_interactive` (engine.py:3091-3104) would rename closed cards too — but that's a separate sibling defect (see DoD process step). The quality-pass entry point is the right place to gate Layer-2 LLM mutations.

## Decision required

The cluster of unguarded mutation verbs (`_cmd_quality_pass`, `_cmd_wait`, `_cmd_attest`) suggests two distinct fix shapes worth picking between:

- **(a) Verb-level filter at quality-pass entry**: `_cmd_quality_pass` always filters terminal-status cards out of the *LLM sample* (the variable `sample` at engine.py:3179), regardless of `--status` value. Layer-1 antipattern/missing-summary scan continues to include terminal cards (read-only, useful for hygiene reporting). Layer-2 LLM rewrite path never sees them. Simple, defense at the boundary.
- **(b) Verb-level error**: `_cmd_quality_pass` rejects `--llm` combined with `--status all|done|disproved|superseded` with an explicit error message. Matches the `_cmd_decide` shape — fail loudly. Slightly less ergonomic if the user wanted Layer-1 hygiene reporting on terminal cards.
- **(c) Helper-level guards**: `_apply_summary_rewrite` and `_apply_dod_rewrite` refuse with a `ValueError` when the card is terminal. Defense-in-depth: protects any future caller, not just quality-pass. Matches the post-fix `_cmd_decide` shape but applied to the helpers.

Recommendation: **(a) + (c) combined** — filter at the verb so the common path silently does the right thing, and guard the helpers so any new caller (a future `goc rewrite-summary` verb, an internal tool) inherits the protection.

## Sibling sweep

The same root cause — mutation verb missing terminal-status guard — already has cards in flight:

- [goc-decide-accepts-decisions-on-already-closed-cards](../goc-decide-accepts-decisions-on-already-closed-cards/) (closed) — guard added at engine.py:4556
- [goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard](../goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard/) (open)
- [goc-attest-mutates-log-md-on-already-closed-cards](../goc-attest-mutates-log-md-on-already-closed-cards/) (open)

This is the fourth instance of the same family. If a fifth surfaces, file an architectural meta-fix umbrella that codifies the guard as a decorator or shared helper across all mutation verbs (per the audit-deck sibling-sweep rule at `Skill(audit-deck)` Phase 3).
