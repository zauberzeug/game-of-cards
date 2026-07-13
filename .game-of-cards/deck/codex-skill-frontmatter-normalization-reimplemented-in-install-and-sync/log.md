## 2026-06-22 — filed (audit-deck, empty ready queue)

Surfaced while draining the pull queue: no `human_gate: none` open card was
ready (the three none-gate cards all carry an active `waiting_on` overlay), so
an audit pass ran. The strongest defect lead (the `render_table -vv`
bare-string char-explosion) was already documented in the
`bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`
meta-fix umbrella, so it was not re-filed.

This card is the genuinely-uncarded finding: `_write_codex_skill`
(`goc/install.py`) and `_codex_skill_text` (`scripts/sync_plugin_assets.py`)
are two independent copies of the Codex frontmatter transform, both carrying
the same `split("---", 2)` truncation bug. The existing truncation card scopes
only the install site. Filed as decision-gated to match the repo's other
`reimplements-and-keeps-drifting` cards; not fix-through-eligible because
consolidation fans out across `install.py` (mirrored to four plugin payloads)
plus the sync script.

## 2026-07-13 — Deck hygiene pass

Stripped the `meta-fix` tag: per the card-schema predicate, `meta-fix` applies iff the literal appears in title/summary/body or the card carries an edge to a meta-fix-tagged card — neither holds here (zero edges, no literal). The consolidation framing stands on its own; re-add the tag with a `meta-fix` literal in the summary if the family framing is wanted.
