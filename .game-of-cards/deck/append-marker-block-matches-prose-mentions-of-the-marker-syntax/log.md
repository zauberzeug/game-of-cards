
## 2026-07-18 — Fresh real-world instance (agent session, dogfood repo)

While regenerating the dogfood AGENTS.md marker block for
`openclaw-plugin-skills-force-repeated-reads-every-session`, an agent hand-rolled the
same unanchored replacement shape (`str.index("<!-- END GOC -->")`) and hit exactly this
failure: the prose mention of the marker syntax (now at AGENTS.md ~line 400) matched
first and 105 lines were duplicated. `test_version_surfaces` +
`test_release_rewrite_version_format` caught it; the redo used line-anchored (`^...$`)
marker matching — evidence for the line-anchoring fix path. The prose trigger is still
live in this repo's AGENTS.md, so the next `goc upgrade` here reproduces the engine-side
corruption verbatim (re-confirmed today against `goc.install._append_marker_block`:
2 matches, prose rewritten mid-sentence).

## 2026-11-09T01:58:21Z — Staleness re-check

As-filed anchor gone from HEAD: `goc/install.py:1181`
(`def _append_marker_block(target: Path, block_body: str, *, header: str) -> None:`), moved by `0be57d4d`
(signature now spans three lines and gained `probe`).
Reproducer: `reproduce.py` → exit 1, "DEFECT REPRODUCED — exiting 1". It tests a local copy of the pattern, still byte-identical to the one in
`_append_marker_block`; calling `goc.install._append_marker_block` itself on the same shape also rewrote the prose mention and left two blocks.
Verdict: still live. Re-anchored `goc/install.py:1508` → `:1594` (`def _append_marker_block(`).
Gate unchanged.
