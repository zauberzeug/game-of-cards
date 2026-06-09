## 2026-06-09T04:29:15Z — Closure

- **What changed**: `goc/templates/skills/codex-kickoff/SKILL.md` Stage 2 —
  rewrote "know what the plugin provides" into a three-case command-resolution
  section (global CLI / source checkout / plugin-only). The plugin-only case
  derives the plugin root from the skill's own loaded path (grandparent of the
  skill dir), prefers `${PLUGIN_ROOT}` when Codex exports it, and invokes the
  bundled `"$PLUGIN_ROOT/bin/goc"` wrapper or `PYTHONPATH="$PLUGIN_ROOT"
  python3 -m goc.cli`. Explicitly states `goc` is not callable on PATH in a
  plugin-only install, forbids the `~/.local/bin/goc` shim, and tells agents
  not to fall back to direct deck-file edits. Added
  `tests/test_codex_plugin_bundled_cli.py`.
- **Verification**: bundled `bin/goc --help` and `PYTHONPATH=<root> python3 -m
  goc.cli --help` both exit 0 from a non-GoC temp cwd; guidance assertions pass
  across the template + `.codex/` + `codex-plugin/` mirrors.
- **Audit**: PASS — no principle touched, mechanical guidance + reproduction fix.
- **Project impact**: n/a
- **Tests**: 413 passed / 0 failed (`uv run python -m unittest discover -s
  tests`); `uv run goc validate` OK; sync-plugin-assets + openclaw porter checks OK.

## Closure verification (2026-06-09T04:29:26Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-09 — Closure' present
