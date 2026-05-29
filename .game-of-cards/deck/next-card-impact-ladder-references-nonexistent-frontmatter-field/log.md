## 2026-05-29T12:01:08Z — Closure

- **What changed**: `goc/templates/skills/next-card/SKILL.md:49-61` renamed "Impact ladder" → "Contribution ladder" with `impact: high|medium|low` → `contribution: high|medium|low`; `goc/templates/skills/pull-card/SKILL.md:123` example `impact:high` → `contribution:high`. Mirrors regenerated via `scripts/sync_plugin_assets.py` and `scripts/port_skills_to_openclaw.py`.
- **Verification**: `reproduce.py` exits 0 — zero ``` `impact: <level>` ``` occurrences in next-card SKILL.md (previously 4); zero `impact:<level>` propagated examples in pull-card SKILL.md (previously 1).
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: reproduce.py PASS; `uv run goc validate` clean; `scripts/sync_plugin_assets.py --check` OK; `scripts/port_skills_to_openclaw.py --check` OK.

## Closure verification (2026-05-29T12:01:17Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present

## 2026-05-29 — Later evidence

Forward pointer: [skill-prose-still-calls-queue-impact-sorted-after-impact-contribution-rename](../skill-prose-still-calls-queue-impact-sorted-after-impact-contribution-rename/) extends this rename to the surviving prose occurrences. This card's `reproduce.py` regex was narrowly scoped to the field-name form `\`impact:\s*(high|medium|low)\``, which is why five prose drift hits ("impact-sorted queue", "sorted by impact desc", "Impact ladder" header in audit-deck, etc.) survived the fix. Resolved by the new card.
