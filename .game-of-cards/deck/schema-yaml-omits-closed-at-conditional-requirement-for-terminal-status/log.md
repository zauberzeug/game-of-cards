## 2026-11-09T01:58:14Z — Staleness re-check

As-filed anchor gone from HEAD: `goc/templates/skills/card-schema/SKILL.md:123`
(`` ## Timestamps (`created`, `closed_at`) ``), moved by `6e501d2f`.
Reproducer: none.
Verdict: not verified (no reproducer) — needs a human re-read. Not
re-anchored: `goc/templates/skills/card-schema/SKILL.md:123-128` — the section
was split into a condensed `SKILL.md:71-76` and `reference.md:34-50`, and the
quoted "Validator rule is symmetric" sentence now lives only in
`reference.md`, so the cited file has no single home for it. Seen in HEAD,
not verified: `goc/schema.yaml` still lists `closed_at` flat under
`optional_fields`.
Gate unchanged.
