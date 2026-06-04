## 2026-06-04T04:56:54Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py:38,250` — added `_FOLDED_INDICATOR_RE = re.compile(r"^>(\d+)?([-+]?)$")` mirroring `_BLOCK_INDICATOR_RE`, and replaced the exact-string `rest == ">"` guard with a match against it, so every folded-scalar variant raises ParseError instead of only the bare `>`.
- **Verification**: reproduce.py exits 0 (was 1) — all 6 variants (`>`, `>-`, `>+`, `>2`, `>2-`, `>2+`) now raise; `FoldedScalarRejectionTest` (3 cases) added to `tests/test_yaml_lite.py`.
- **Audit**: PASS — no principle touched, mechanical fix (restores the documented "unsupported syntax raises, never silently mis-parses" contract).
- **Project impact**: n/a
- **Tests**: 375 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

Plugin mirrors (`claude-plugin/goc`, `codex-plugin/goc`, `openclaw-plugin/goc`) regenerated via `scripts/sync_plugin_assets.py`.

## Closure verification (2026-06-04T04:57:12Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-04 — Closure' present
