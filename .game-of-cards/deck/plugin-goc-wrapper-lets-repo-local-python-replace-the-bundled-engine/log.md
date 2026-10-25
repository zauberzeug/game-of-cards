## 2026-09-10T04:50:58Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

The clean fixes are version-gated, and `pyproject.toml` supports Python 3.10:

1. **`-P` / `PYTHONSAFEPATH=1`** — exactly this problem's fix, but both are
   **3.11+**. Requires either raising the floor to 3.11 (a consumer-visible
   break; AGENTS.md and the plugin READMEs all state "Python 3.10+ is the only
   host prerequisite") or branching in the wrapper on the interpreter version,
   which leaves 3.10 hosts unprotected.
2. **Stop using `-m`** — invoke a small launcher inside the payload by absolute
   path, which makes `sys.path[0]` the payload directory instead of the cwd.
   Works on 3.10, but changes how the entry point is reached and needs care so
   `goc.cli`'s own imports still resolve against the payload.
3. **Sanitize inside the entry point** — have `goc/cli.py` drop a `sys.path[0]`
   that is not the payload root before importing the engine. Works on 3.10, but
   it is too late for the stdlib-shadowing variant, which fails at
   `goc.engine` import time.

Options 2 and 3 differ in whether protection covers the stdlib case; option 1
differs in supported-host policy. That is a maintainer call.

Whatever is picked also applies to the OpenClaw handler, which has the same
shape with a less predictable cwd.


## 2026-10-25T05:20:07Z: decision recorded

Option 2: every plugin start and the engine's own re-invocation run goc/_launch.py by absolute path instead of python3 -m goc.cli; the Python 3.10 floor stays — It covers the goc-package takeover and the stdlib-shadowing variant on every supported Python without a version branch; the maintainer (Rodja, 2026-10-25) delegated the pick and asked for the fix on main. Gate decision → none.

## 2026-10-25T05:24:03Z — Closure

- **What changed**: `goc/_launch.py` (new, mirrored into the three payloads) starts the engine by file path and swaps `sys.path[0]` for the package's parent before importing anything else; `claude-plugin/bin/goc` and `codex-plugin/bin/goc` exec it (no `-m`, no trailing empty `PYTHONPATH` element); `openclaw-plugin/index.ts` builds the handler argv with `gocCommand`, `dist/` rebuilt; `goc/engine.py` re-invokes itself through `_goc_command()`; docs and the `codex-kickoff` guidance describe the launcher.
- **Verification**: `reproduce.py` exits 0 (both wrappers print `goc, version 0.0.28` beside an impostor `goc/`); `tests/test_plugin_engine_ignores_working_directory.py` 7/7 — red before on both wrappers and both impostors, green after, also under Python 3.10.20.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: `uv run python -m unittest discover -s tests` 1383 run, 1 failure on the first run (`CONTRIBUTING.md` still counted 6 source files under `goc/`, fixed), `tests.test_guidance_accuracy` green after; `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` clean.
- **Bundled with**: —

## Closure verification (2026-10-25T05:24:05Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-10-25 — Closure' present
