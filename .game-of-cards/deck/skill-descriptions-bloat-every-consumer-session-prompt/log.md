## 2026-07-04 — filed

Measured on the shipped plugin payload v0.0.24: sum of `description:` fields
across all 16 skills = 8,128 chars ≈ 2,032 tokens, injected into every
consumer session prompt by the host's skill catalog. Worst offender:
advance-card (868 chars, mostly an exhaustive AUTO-INVOKE phrase list).
Motivated by a consumer-side prompt-cost audit that found the static skill
catalog to be a significant share of the per-session prompt prefix on
Anthropic-billed models. Fix path: cap descriptions (~300 chars), move
trigger detail into skill bodies, guard with a regression test.

## 2026-07-07 — implemented

The catalog had grown to 18 skills since filing (codex-kickoff and
openclaw-kickoff were added), and advance-card's description had already
shrunk from the 868 chars measured at filing to 775 — both figures over
the cap, so the TDD sequence held as written.

- **TDD:** added `tests/test_skill_description_length.py` — parses each
  `goc/templates/skills/*/SKILL.md` frontmatter via
  `goc.install._frontmatter_value` and fails on any description over
  300 chars. Red on 17 of 18 skills before the rewrite (advance-card at
  775 the worst; only pull-card at 282 already passed), green after.
- **MECHANICAL:** rewrote all 17 over-cap descriptions to one sentence of
  purpose + the 2–4 strongest AUTO-INVOKE cues (max is now card-schema at
  297 chars). Each skill's full former trigger enumeration and tail
  guidance moved into a new `## When to invoke` section at the top of the
  SKILL.md body, which hosts load on demand. Mirrors re-synced
  (`scripts/sync_plugin_assets.py`) and OpenClaw skills re-ported
  (`scripts/port_skills_to_openclaw.py`); both `--check` guards green.
- **EMPIRICAL:** template descriptions total 8,250 chars (18 skills)
  before → 4,668 chars ≈ 1,167 tokens after. On the like-for-like
  16-skill set from the filing baseline: 8,128 → 4,117 chars = 51%,
  matching the "≤ ~50%" expectation.

Full regression suite (697 tests) and `goc validate` green.

## 2026-07-07T01:25:23Z — Closure

- **What changed**: `goc/templates/skills/*/SKILL.md` — 17 frontmatter
  descriptions rewritten to ≤300 chars with a `## When to invoke` body
  section carrying the former trigger enumerations;
  `tests/test_skill_description_length.py` added as the cap guard;
  mirrors re-synced and OpenClaw skills re-ported.
- **Verification**: description total 8,250 → 4,668 chars (18 skills);
  like-for-like 16-skill set 8,128 → 4,117 chars = 51% of baseline;
  max description now 297 chars (card-schema).
- **Audit**: PASS — no rubric configured; mechanical fix (routing
  metadata slimmed, methodology unchanged in skill bodies).
- **Project impact**: every consumer session prompt sheds ~865 tokens of
  static skill-catalog prefix.
- **Tests**: 697 passed / 0 failed.

## Closure verification (2026-07-07T01:25:33Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-07-07 — Closure' present
