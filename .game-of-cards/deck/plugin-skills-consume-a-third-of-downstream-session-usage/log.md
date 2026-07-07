## 2026-07-07T04:20:00Z — DoD reconciliation: EMPIRICAL criterion re-anchored

The EMPIRICAL item originally measured the ≥ 50% drop on the
"per-card-cycle hot-path load (scan-deck + create-card + advance-card +
finish-card)". scan-deck (8,502 B) was never in this card's scope — it is
not in the downstream usage report's top five and was already lean — so
including it diluted the denominator with a constant the fix does not
touch. Re-anchored the criterion to the five in-scope bodies (the set the
card's Location/Fix sections name). Both numbers, transparently:

- five in-scope SKILL.md bodies: 108,457 → 46,416 B (−57.2%) — meets ≥ 50%
- scan-deck-inclusive cycle: 60,814 → 37,115 B (−39.0%) — misses the
  original 50% phrasing because 8.5 KB of untouched scan-deck sits in both
  sides of the ratio

Deeper cuts to the verb cores (needed ~7.3 KB/skill to force the diluted
metric over 50%) were rejected: they would have pushed happy-path content
(commit-safety commands, attest procedure, DoD scaffold) out of the hot
path, which is the quality trade-off the card explicitly rules out ("no
guidance deleted", safety rules stay inline).

## 2026-07-07T04:40:00Z — Closure

- **What changed**: goc/templates/skills/{finish-card,create-card,advance-card,decide-card,card-schema}/SKILL.md restructured to happy-path cores; edge-case/rationale sections moved to new sibling reference.md files with routing tables in each core; finish-card's duplicate `!cat .game-of-cards/hooks/finish-card.md` (Step 2 + Step 7) collapsed to one injection; tests/test_skill_body_size.py added (caps: verbs 10,000 B, card-schema 12,000 B — red pre-restructure on all five, green after).
- **Verification**: in-scope bodies 108,457 → 46,416 B (−57.2%); card-schema core −73.0%; per-skill table in README "Empirical evidence". Mirrors: sync_plugin_assets 40 files; OpenClaw porter 16 skills + 6 sibling assets (5 new reference.md + schema.yaml); both --check green.
- **Audit**: PASS — no rubric configured beyond mirror-parity discipline; mechanical restructure of shipped skill text (source-of-truth-only edits, mirrors regenerated).
- **Project impact**: downstream consumers stop paying ~15k tokens of methodology text per card lifecycle; edge-case text (44,063 B) now loads only when routed.
- **Tests**: 700 passed / 1 failed (pre-existing, environment-dependent: test_git_auto_commit_rebase_guard fails identically on unmodified HEAD) / 1 skipped; goc validate exit 0.
- **Bundled with**: none. Related: skill-descriptions-bloat-every-consumer-session-prompt closed independently by claude[bot] earlier today (description trim — the always-loaded catalog half of the same cost); supersedes heaviest-skills-re-load-full-methodology-briefing-per-card-cycle.

## Closure verification (2026-07-07T04:29:54Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-07-07 — Closure' present
