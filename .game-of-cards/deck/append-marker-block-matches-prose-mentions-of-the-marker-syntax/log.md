
## 2026-07-18 — Fresh real-world instance (agent session, dogfood repo)

While regenerating the dogfood AGENTS.md marker block for
`openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session`, an agent hand-rolled the
same unanchored replacement shape (`str.index("<!-- END GOC -->")`) and hit exactly this
failure: the prose mention of the marker syntax (now at AGENTS.md ~line 400) matched
first and 105 lines were duplicated. `test_version_surfaces` +
`test_release_rewrite_version_format` caught it; the redo used line-anchored (`^...$`)
marker matching — evidence for the line-anchoring fix path. The prose trigger is still
live in this repo's AGENTS.md, so the next `goc upgrade` here reproduces the engine-side
corruption verbatim (re-confirmed today against `goc.install._append_marker_block`:
2 matches, prose rewritten mid-sentence).
