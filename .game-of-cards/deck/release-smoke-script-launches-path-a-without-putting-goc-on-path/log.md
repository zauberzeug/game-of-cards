## 2026-07-26T07:35:00Z — Closure

- **What changed**: `scripts/smoke_release.sh:42-62` — `run_path_a` now prepends
  `uv tool dir --bin` to `PATH` after `uv tool install` (mirroring the CI job's
  `echo "$HOME/.local/bin" >> $GITHUB_PATH` at `release.yml:503`) and aborts with
  an actionable error when `goc` still does not resolve, reusing the script's
  existing `command -v claude` prerequisite-guard idiom.
- **Verification**: `reproduce.py` exits 0 (was 1); all three structural
  assertions in the new test fail against the pre-fix script. The new test
  executes the shipped guard under `set -euo pipefail` with a `PATH` holding
  only an empty directory and asserts exit 1 + `goc not on PATH` on stderr,
  without reaching the agent launch.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 765 passed / 0 failed / 0 xfailed (`uv run python -m unittest
  discover -s tests`). `goc validate`, `sync_plugin_assets.py --check`, and
  `port_skills_to_openclaw.py --check` all clean.
- **Bundled with**: n/a

Note for the next reader: the first draft of the fix interpolated
`${goc_bin_dir:-uv's tool-bin directory}` in the error message. The apostrophe
opens a quote inside `${var:-word}` even within double quotes, so `bash -n`
rejected the whole file (`unexpected EOF while looking for matching '`). The
`bash -n` assertion in the regression test is therefore part of the contract,
not decoration — it is what caught it.

The remaining Path A / Path B `--allowedTools` and Path B assertion divergence
from the CI job stays open on
[local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job](../local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job/)
at `human_gate: decision` — whether bare `Bash` under `--permission-mode
dontAsk` is acceptable on a developer machine is a human call, not a derivation.

## Closure verification (2026-07-26T07:28:05Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-26 — Closure' present
