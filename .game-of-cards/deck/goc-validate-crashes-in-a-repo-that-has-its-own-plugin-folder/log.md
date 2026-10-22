## 2026-10-07T05:06:31Z — Closure

- **What changed**: `goc/engine.py:1593` adds `_is_goc_source_tree()`, true
  when `REPO_ROOT / "goc" / "templates"` is a directory.
  `validate_plugin_hook_registration` (`:1652`) and
  `validate_plugin_mirror_parity` (`:1774`) return `[]` without it, before
  they read any payload folder. Both docstrings now name the gate.
  `AGENTS.md:221-227`: the gate sentence names the source tree and says the
  mirror check shares the gate.
  Tests: two new in `tests/test_plugin_hook_json_registration.py` (three
  consumer layouts stay silent in both checks, plus a source-tree control) and
  one new in `tests/test_plugin_mirror_parity.py` (the gate holds for this
  repo). The real-tree hook test now asserts the gate too. The two OpenClaw
  fixtures build `goc/templates/` through `_engine_pair`. Added
  `reproduce.py`.
  Deck: post-close pointer (README and log) on
  `plugin-payload-hooks-json-never-registers-a-newly-added-hook-script`. Its
  closure recorded the premise that consuming repos have no `claude-plugin/`.
- **Verification**: `reproduce.py` went from exit 1 to exit 0. The hypothesis
  was confirmed, not disproved: the Claude and Codex layouts crashed with
  `FileNotFoundError`, and the hook check on its own reported two false errors.
  Mutation check: with the gate forced open, the consumer test fails on all
  three layouts with the original traceback. With it open for the hook check
  only, the `hooks.json` layout fails with the two false errors.
  `uv run goc validate` exits 0 with no new WARN.
  `scripts/sync_plugin_assets.py --check` is OK. The card-language and
  card-YAML guards are clean (795 cards).
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1245 passed / 0 failed / 0 xfailed

## Closure verification (2026-10-07T05:06:34Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-07 — Closure' present
