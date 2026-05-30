## 2026-05-30 — filed

Filed from a commit-history review: the last ~200 commits showed a heavy
file-then-fix-minutes-later pattern. Measured the deck and confirmed
median time-to-close = 6.3 min, 60% < 10 min, authored fix ~48 lines / 2
files, filing rate 28–53/day vs audit cron 1/day (so pull-card sessions
do ~97% of the filing as a side effect of their work).

Decision: Rodja chose **"fix-through, keep the card"** from four options
(fix-through-keep-card / inline-fix-no-card / overhead-only /
analysis-defer). Keep the card (record axis + TDD test are load-bearing,
this repo dogfoods goc's record); cut the wasteful *separate run* by
letting the filing session close small/mechanical/gate-free findings
in place. Threshold-gated so subtle/cross-cutting work still gets a
fresh-context second look. `audit-deck` stays flag-don't-fix.

## 2026-05-30T12:32:21Z — Closure

- **What changed**: `goc/templates/skills/pull-card/SKILL.md` — added a "Fixing what you surface (fix-through)" section (eligibility: gate-free + small/single-site + not-a-meta-fix + close-to-loaded-context; action: file the card via create-card, then claim→implement→close in the same session); rewrote the "Queue empty" bullet to route fix-through-eligible findings through the same session instead of unconditionally file-then-exit; added a fix-through report form. `audit-deck` ("flag, don't fix") deliberately untouched.
- **Verification**: drift checks green (sync_plugin_assets --check + port_skills_to_openclaw --check both "no drift"); OpenClaw port retained the fix-through content; 276 tests pass (1 skipped); `goc validate` clean (only pre-existing UNTAGGED_DOD_ITEM WARNs on other cards). 4 mirrors regenerated (.claude, .codex, claude-plugin, codex-plugin) + openclaw re-ported.
- **Audit**: PASS — no project rubric configured (finish-card hook empty); skill-body/methodology change, no code-principle binding beyond the card's own resolved design.
- **Project impact**: every consumer's autonomous loop inherits the fix-through path; targets the median 6.3-min / ~48-line card by collapsing two fresh-context runs into one while preserving the card record + TDD test.
- **Tests**: 276 passed / 0 failed / 1 skipped
- **Bundled with**: n/a

## Closure verification (2026-05-30T12:32:24Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
