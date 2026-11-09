

## 2026-07-13 — Deck hygiene pass

Refreshed defunct citations: the `--bundle` paragraph moved from `finish-card/SKILL.md:228-242` to `finish-card/reference.md:79-90` when the skill was split into core + reference (commit 8a1af2f5). Mechanical cite update; claims unchanged.

## 2026-11-09T02:00:01Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/templates/skills/finish-card/SKILL.md:228`
(`**Bundled closures** (one fix resolves multiple cards):`) and `:234`
(`` `--bundle` enforces the unchecked-DoD refusal on every member before ``),
moved to `reference.md` by `6e501d2f` (not `8a1af2f5`, as logged 2026-07-13).
Reproducer: `reproduce.py` → exit 0 (inverted: prints "DEFECT REPRODUCED: bundle
bypassed the attestation that `goc attest` would have failed.").
Verdict: still live. Re-anchored `finish-card/reference.md:79-90` → `:77-93`
and `reference.md:82-90` → `:85-93`.
Gate unchanged.
