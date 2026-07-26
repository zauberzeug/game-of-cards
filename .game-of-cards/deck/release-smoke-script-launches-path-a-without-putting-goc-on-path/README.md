---
title: release-smoke-script-launches-path-a-without-putting-goc-on-path
summary: "`scripts/smoke_release.sh` Path A installs the `goc` CLI with `uv tool install` but never adds uv's tool-bin directory to `PATH` and never checks that `goc` resolves, while the prompt it then sends asserts \"goc is on PATH and Bash(goc:*) is allowed\". The CI job it mirrors adds `$HOME/.local/bin` to `PATH` explicitly. On any machine where uv's bin directory is not already on `PATH`, Path A burns a 30-turn LLM run and then fails with \"FAIL Path A: deck dir not created\", blaming the plugin payload for a harness gap."
status: open
stage: null
contribution: medium
created: "2026-07-26T07:19:27Z"
closed_at: null
human_gate: none
advances:
  - local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job
advanced_by: []
tags: [bug, infra]
draft: true
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — Path A either extends `PATH` to uv's tool-bin directory or fails fast when `goc` does not resolve
  - [ ] TDD: a regression test asserts `scripts/smoke_release.sh` cannot launch Path A's agent run while asserting a `goc`-on-`PATH` premise it has not established
  - [ ] MECHANICAL: the fix reuses the script's existing prerequisite-guard idiom (the `command -v claude` block) so a missing `goc` reports an actionable error instead of a 30-turn agent run
  - [ ] PROCESS: cross-referenced from [local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job](../local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job/) as one confirmed instance of the mirror drift
  - [ ] PROCESS: `uv run goc validate` passes
---

# release smoke script launches Path A without putting goc on PATH

## Location

`scripts/smoke_release.sh:43` (inside `run_path_a`):

```bash
echo "  pre-installing goc CLI from $REPO_ROOT..."
uv tool install --force "$REPO_ROOT" >/dev/null
```

Six lines later, the prompt that script sends to the `claude` CLI
(`scripts/smoke_release.sh:49`):

```
2. Run Skill(kickoff) to completion. goc is on PATH and Bash(goc:*) is allowed.
```

## What's broken

`uv tool install` places the `goc` console script in uv's tool-bin
directory (`/home/runner/.local/bin` here). Whether that directory is on
`PATH` is the developer's shell configuration — the install does not
guarantee it, which is why uv itself emits a `not on your PATH` warning
when it is absent.

The CI job this script exists to mirror handles that explicitly.
`.github/workflows/release.yml:500-503`:

```yaml
      - name: Pre-install goc CLI for Path A
        run: |
          uv tool install --force "${{ github.workspace }}"
          echo "$HOME/.local/bin" >> $GITHUB_PATH
```

The local script has no counterpart to that second line. It also never
checks the outcome — even though the very same file guards its *other*
two prerequisites with explicit, actionable errors
(`scripts/smoke_release.sh:26-34`):

```bash
if [ ! -d "$PLUGIN_DIR/.claude-plugin" ]; then
    echo "error: $PLUGIN_DIR is not a Claude Code plugin (missing .claude-plugin/)" >&2
    exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
    echo "error: claude CLI not on PATH. Install with: npm install -g @anthropic-ai/claude-code" >&2
    exit 1
fi
```

So Path A is the one prerequisite the script takes responsibility for
installing (`scripts/smoke_release.sh:12`: "`goc` CLI installable from
this checkout (we install it for Path A)") and the one it neither
establishes nor verifies.

## Empirical evidence

`uv run python .game-of-cards/deck/release-smoke-script-launches-path-a-without-putting-goc-on-path/reproduce.py`:

```
[1] The CI smoke job puts the freshly-installed goc on PATH:
    release.yml:502: uv tool install --force "${{ github.workspace }}"
    release.yml:503: echo "$HOME/.local/bin" >> $GITHUB_PATH
[2] The local mirror installs it and stops there:
    smoke_release.sh:43: uv tool install --force "$REPO_ROOT" >/dev/null
[3] ...then tells the agent goc is already reachable:
    smoke_release.sh:49: 2. Run Skill(kickoff) to completion. goc is on PATH and Bash(goc:*) is allowed.
[4] uv installs the goc executable into: /home/runner/.local/bin
[5] smoke_release.sh, structurally:
    extends PATH for uv's tool-bin dir?  False
    guards that `goc` resolves?          False
    guards that `claude` resolves?       True   <- the idiom it already uses
    Path A prompt asserts goc on PATH?   True
[6] resolving `goc` for the agent run (minimal PATH, uv's bin dir stands in as tmp):
    with the tool-bin dir OFF PATH: None
    with the tool-bin dir ON  PATH: '/tmp/tmp3k7kpp7e/goc'

[FAIL] Path A asserts `goc` is on PATH but neither extends PATH nor guards
resolvability; on a machine without uv's bin dir on PATH it burns a 30-turn
agent run and reports 'FAIL Path A: deck dir not created' -- blaming the plugin
payload for a harness gap.
```

## Why it matters

`scripts/smoke_release.sh` is the documented pre-tag check — its own
header says to "Use this before pushing a release tag to catch
regressions without burning CI minutes." Its failure mode is therefore
read as a verdict on the plugin payload.

When uv's bin directory is not on `PATH`, the run instead goes: the
prompt asserts `goc` is available → kickoff's `goc install` hits
`command not found` → kickoff correctly emits its "install goc first"
remediation instead of scaffolding a deck → `test -d
"$workdir/.game-of-cards/deck"` fails → the script prints
`FAIL Path A: deck dir not created`. That message names the payload, but
the payload was never exercised. The maintainer either loses time
chasing a non-defect or, worse, "fixes" the plugin to satisfy a check CI
does not make — and the 30-turn agent run is spent either way.

The reachability path is ordinary first use: a developer who installed
`uv` but never ran `uv tool update-shell` (or whose shell rc does not
already export `~/.local/bin`) hits it on the first invocation. The GitHub
runner used to gather this evidence happens to have `~/.local/bin` on
`PATH` already, which is exactly why the gap has stayed latent.

This is one confirmed instance of the broader divergence tracked on
[local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job](../local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job/);
that card carries the parts of the drift that need a human call on
dev-machine tool posture. This one does not — the script already has an
established idiom for prerequisite guards, and the CI job already shows
the `PATH` step.

## Fix

In `run_path_a` (`scripts/smoke_release.sh:36-60`), make the installed
`goc` reachable and fail fast if it is not, mirroring both
`release.yml:503` and the script's existing `command -v claude` guard:

```bash
uv tool install --force "$REPO_ROOT" >/dev/null
PATH="$(uv tool dir --bin):$PATH"
export PATH
if ! command -v goc >/dev/null 2>&1; then
    echo "error: goc not on PATH after 'uv tool install $REPO_ROOT'." >&2
    echo "       Add $(uv tool dir --bin) to PATH (e.g. 'uv tool update-shell')." >&2
    exit 1
fi
```

Deriving the directory from `uv tool dir --bin` rather than hardcoding
`$HOME/.local/bin` keeps the guard correct under a custom
`UV_TOOL_BIN_DIR`. The guard is what makes the fix testable: the failure
becomes a named prerequisite error before any agent turn is spent.
