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

## 2026-06-09T06:48:55Z — Closure

- **What changed**: `goc/install.py`, `scripts/sync_plugin_assets.py`, `goc/templates/bootstrap/_goc-bootstrap.sh`, `goc/templates/skills/codex-kickoff/SKILL.md`, `codex-plugin/README.md` — Codex-rendered skills now carry a command resolver and the Codex plugin payload ships `skills/_goc-bootstrap.sh`, which invokes the sibling bundled `bin/goc` wrapper.
- **Verification**: Added downstream-style bootstrap regression with no `goc` on `PATH`; full regression suite passed.
- **Audit**: PASS — no project rubric configured; mechanical fix.
- **Project impact**: Codex plugin-only downstream users get an explicit no-global-shim path to the bundled GoC engine.
- **Tests**: 410 passed / 0 failed / 1 skipped; `uv run goc validate` passed.

## Closure verification (2026-06-09T06:49:39Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-09 — Closure' present

## 2026-06-10 — Merge reconciliation

Two agents closed this card in parallel with complementary solutions, and
the merge of both branches conflicted on this card and on
`codex-kickoff/SKILL.md`. Reconciled by keeping both contributions:

- Infrastructure (local branch): `codex-plugin/skills/_goc-bootstrap.sh`
  shipped in the plugin payload, the `## Codex GoC Command` resolver block
  injected into every Codex-rendered skill, and the bootstrap's
  sibling-`bin/goc` detection — with its `tests/test_install.py` regression.
- Guidance + test (remote branch): the three-case Stage 2 framing in
  `codex-kickoff` ("`goc` is *not* a callable command" in plugin-only
  installs, no `~/.local/bin/goc` shim, no direct deck-file edits, direct
  `"$PLUGIN_ROOT/bin/goc"` / `PYTHONPATH=<root> python3 -m goc.cli`
  invocations) — with `tests/test_codex_plugin_bundled_cli.py`.

The merged Stage 2 leads the plugin-only case with the bootstrap helper and
documents the direct invocations it wraps. `closed_at` keeps the later of
the two closure timestamps; both closure entries above are preserved.
