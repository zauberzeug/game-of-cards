---
title: release-smoke-script-launches-path-a-without-putting-goc-on-path
summary: "`scripts/smoke_release.sh` Path A installs the `goc` CLI with `uv tool install` but never adds uv's tool-bin directory to `PATH` and never checks that `goc` resolves, while the prompt it then sends asserts \"goc is on PATH and Bash(goc:*) is allowed\". The CI job it mirrors adds `$HOME/.local/bin` to `PATH` explicitly. On any machine where uv's bin directory is not already on `PATH`, Path A burns a 30-turn LLM run and then fails with \"FAIL Path A: deck dir not created\", blaming the plugin payload for a harness gap."
status: done
stage: null
contribution: medium
created: "2026-07-26T07:19:27Z"
closed_at: "2026-07-26T07:28:09Z"
human_gate: none
advances:
  - local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — Path A either extends `PATH` to uv's tool-bin directory or fails fast when `goc` does not resolve
  - [x] TDD: a regression test asserts `scripts/smoke_release.sh` cannot launch Path A's agent run while asserting a `goc`-on-`PATH` premise it has not established
  - [x] MECHANICAL: the fix reuses the script's existing prerequisite-guard idiom (the `command -v claude` block) so a missing `goc` reports an actionable error instead of a 30-turn agent run
  - [x] PROCESS: cross-referenced from [local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job](../local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job/) as one confirmed instance of the mirror drift
  - [x] PROCESS: `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
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

`uv run python .game-of-cards/deck/release-smoke-script-launches-path-a-without-putting-goc-on-path/reproduce.py`
against the script **before** the fix (exit 1):

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

**After** the fix, the same script exits 0 with steps 1–4 unchanged and:

```
[5] smoke_release.sh, structurally:
    extends PATH for uv's tool-bin dir?  True
    guards that `goc` resolves?          True
    guards that `claude` resolves?       True   <- the idiom it already uses
    Path A prompt asserts goc on PATH?   True

[OK] Path A closes the gap: it extends PATH to uv's tool-bin dir and/or fails
fast when `goc` does not resolve.
```

`tests/test_smoke_release_path_a_goc_on_path.py` executes the shipped
guard in isolation under the script's own `set -euo pipefail` with a
`PATH` containing only an empty directory — so neither `uv` nor `goc`
resolves — and asserts it exits 1 with `goc not on PATH` on stderr
without reaching the agent launch. All three structural assertions fail
against the pre-fix script; the suite is 765 tests green with the fix.

That test also caught a defect in the first version of the fix: the
error message interpolated `${goc_bin_dir:-uv's tool-bin directory}`,
whose apostrophe opens a quote inside `${var:-word}` even within double
quotes, so `bash -n` rejected the whole file with `unexpected EOF while
looking for matching '`. Hence the `bash -n` assertion is part of the
regression contract, not incidental.

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

## Fix (landed)

In `run_path_a`, immediately after the `uv tool install` step, make the
installed `goc` reachable and fail fast if it is not — mirroring both
`release.yml:503` and the script's existing `command -v claude` guard:

```bash
local goc_bin_dir
goc_bin_dir="$(uv tool dir --bin 2>/dev/null || true)"
if [ -n "$goc_bin_dir" ]; then
    export PATH="$goc_bin_dir:$PATH"
fi
if ! command -v goc >/dev/null 2>&1; then
    echo "error: goc not on PATH after 'uv tool install $REPO_ROOT'." >&2
    echo "       Add ${goc_bin_dir:-the uv tool-bin directory} to PATH (e.g. 'uv tool update-shell')." >&2
    exit 1
fi
```

Three details are load-bearing:

- The directory comes from `uv tool dir --bin` rather than a hardcoded
  `$HOME/.local/bin`, so a custom `UV_TOOL_BIN_DIR` still works.
- The `if [ -n ... ]` is an explicit conditional, not an
  `[ -n ... ] && export ...` chain. The chain does survive `set -e` (the
  `&&`-list exemption applies) but leaves `$?` at 1, which would turn
  into a spurious non-zero return if anything were ever appended after
  it.
- The guard aborts rather than warns. A warning would still spend the
  30-turn agent run, which is the cost this card exists to avoid.

`goc` remains reachable to the agent through the prompt's own claim
because Path A's allowlist already grants `Bash(goc:*)`; the remaining
Path A / Path B allowlist divergence from CI is out of scope here and
sits on
[local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job](../local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job/).
