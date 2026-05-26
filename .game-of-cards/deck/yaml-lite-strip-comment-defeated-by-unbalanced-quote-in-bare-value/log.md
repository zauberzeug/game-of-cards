## 2026-05-26T23:07:04Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py` `_strip_comment` — only track quote state for a genuinely quoted scalar (value starting with a quote); a lone apostrophe in a bare value no longer suppresses trailing-comment stripping.
- **Verification**: reproduce.py exits 0 — 5/5 cases pass (2 previously-failing bare-value apostrophe cases now strip the comment; quoted-run `#` and post-quote comment still handled correctly).
- **Audit**: PASS — no principle touched, mechanical fix (parser correctness; aligns yaml-lite with real-YAML comment semantics).
- **Project impact**: n/a
- **Tests**: no pytest suite; `goc validate` clean, `sync_plugin_assets.py --check` green after re-sync of the 3 vendored mirrors.
- **Bundled with**: none

## Closure verification (2026-05-26T23:07:07Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
