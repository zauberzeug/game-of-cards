## 2026-07-04 — filed

Measured on the shipped plugin payload v0.0.24: sum of `description:` fields
across all 16 skills = 8,128 chars ≈ 2,032 tokens, injected into every
consumer session prompt by the host's skill catalog. Worst offender:
advance-card (868 chars, mostly an exhaustive AUTO-INVOKE phrase list).
Motivated by a consumer-side prompt-cost audit that found the static skill
catalog to be a significant share of the per-session prompt prefix on
Anthropic-billed models. Fix path: cap descriptions (~300 chars), move
trigger detail into skill bodies, guard with a regression test.
