## 2026-06-20T05:05:00Z — Filed (parked at decision gate)

Surfaced by an audit-deck hunter during a queue-empty `pull-card` run.
Confirmed empirically: a temp-deck card with `wating_on: external` (typo
of `waiting_on`) plus `totally_made_up_field: 7` validates `OK` / exit 0.
`grep -rn optional_fields goc/` shows the schema's closed set is loaded
into the `Schema` dataclass but never read by `validate_card`.

Parked at `human_gate: decision` rather than fixed through because the
enforcement model (hard error / warn-only / near-miss typo detection)
is a design choice entangled with the open
`support-custom-frontmatter-fields-with-enum-and-required-when-rules`
feature. See the `## Decision required` section in README.md.
