## 2026-05-29 — Empirical: standup payload bytes before/after

Captured at HEAD on the closure commit (this card's mutations applied,
deck contains 268 cards):

- `goc --json --status all`             — 343,519 bytes (the prior standup payload).
- `goc --json --closed-since 24h --slim` —     308 bytes (the new standup payload).
- Reduction: 99.91% (343,211 bytes saved per standup invocation).

The 24h window captures only `compute-values-iterates-non-list-advances-character-by-character`
in this run. On a busier day the slim payload grows by ~280 bytes per
closure (eight fields each), so a 10-card-closure standup still ships
< 4 KB instead of the full 343 KB.

## 2026-05-29T05:00:00Z — Closure

- **What changed**: five mechanical token-cost reductions —
  - `goc/engine.py` adds global `--closed-since WINDOW`, `--slim`, `--waiting` flags + `parse_closed_since` + `_closed_at_instant` helpers; `render_json` learns `slim=`; `_cmd_default` runs the new filters and emits a `render_leverage_line` after `--ready`.
  - `goc/engine.py` `_cmd_done` becomes title-list-aware with `--bundle`; `_cmd_done_bundle` writes a shared `## Closure verification (...) — bundled` block + per-card `Bundled with:` cross-refs and flips every member atomically.
  - `goc/templates/skills/standup/SKILL.md` Section 3 swaps the inline 339 KB JSON dump for `goc --json --closed-since 24h --slim`.
  - `goc/templates/skills/finish-card/SKILL.md` documents `goc done --bundle`; `pull-card/SKILL.md` interprets the new leverage line; `audit-deck/SKILL.md` + `create-card/SKILL.md` codify the reachability-naming convention.
  - `.gitattributes` (new) marks the seven mirror trees `linguist-generated`; `AGENTS.md` documents the `[sync auto]` commit-subject convention.
- **Verification**: 343,519 → 308 bytes for the standup payload on this deck (99.91% reduction). `tests/test_done_bundle.py` (4 tests, all green); full regression suite green (182/182).
- **Audit**: PASS — mechanical fixes (no principle touched).
- **Project impact**: token shipment per autonomous-card cycle drops by the difference between the full JSON and the slim window; standup's slim payload + new `--bundle` ceremony folding remove two of the heaviest per-cycle costs.
- **Tests**: 182 passed / 0 failed / 0 xfailed.
- **Bundled with**: (none — single card)
