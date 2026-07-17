---
name: codex-kickoff
description: Codex-specific complement to the generic kickoff skill — install the GoC Codex plugin from the repo marketplace, explain hook activation, verify the goc CLI path. AUTO-INVOKE after Skill(kickoff) completes in Codex, or on "finish kickoff for Codex" / "set up Codex plugin".
---

## When to invoke

Invoke after `Skill(kickoff)` completes in Codex, or when the user says "finish kickoff for Codex", "set up Codex plugin", "install the GoC Codex plugin", or "enable GoC hooks in Codex".

# Finish kickoff on Codex

The generic `kickoff` skill is host-agnostic: it introduces GoC, asks
where the briefing should live, and scaffolds `.game-of-cards/`.
This complement handles Codex-specific plugin setup.

Run this skill after the generic kickoff returns, or when a user wants
to switch from checked-in Codex skills to the plugin path.

## Stage 0 — state detection sweep

Check the project state:

```bash
ls .game-of-cards/deck/ 2>/dev/null && echo "DECK_EXISTS" || echo "deck_missing"
command -v goc >/dev/null 2>&1 && echo "GOC_ON_PATH" || echo "goc_missing"
test -f .agents/plugins/marketplace.json && echo "REPO_MARKETPLACE" || true
test -f .codex/config.toml && grep -q 'plugin_hooks *= *true' .codex/config.toml && echo "PLUGIN_HOOKS_ON" || true
```

If `DECK_EXISTS` is missing, run `Skill(kickoff)` first. This skill
finishes a Codex setup; it does not replace the generic setup.

## Stage 1 — install from the repo marketplace

The Game of Cards Codex plugin is published from this repository's
marketplace file at `.agents/plugins/marketplace.json`. Add or refresh
the marketplace, then install the plugin from Codex's plugin browser:

```bash
codex plugin marketplace add zauberzeug/game-of-cards
codex plugin marketplace upgrade game-of-cards
```

If Codex was previously using the shared `zauberzeug-claude`
marketplace, remove that GoC plugin after the direct marketplace
install. The shared marketplace can pin GoC to an older release even
after this repository has published a fixed payload:

```bash
codex plugin add game-of-cards@game-of-cards
codex plugin remove game-of-cards@zauberzeug-claude
```

Then open Codex's plugin browser:

```text
/plugins
```

Select the `Game of Cards` marketplace source and install the
`game-of-cards` plugin. Start a new thread after installation so Codex
loads the plugin's bundled skills.

For local development against a checkout, use:

```bash
codex plugin marketplace add ./path/to/game-of-cards
```

## Stage 2 — resolve the `goc` command

The Codex plugin supplies:

- GoC skills from `goc/templates/skills/`, filtered for Codex and
  packaged under the plugin's `skills/` directory.
- Lifecycle hooks under `hooks/hooks.json`.
- A bundled `goc/` engine mirror, a `bin/goc` wrapper that runs it, and
  a `skills/_goc-bootstrap.sh` helper that can invoke the bundled
  engine even when Codex does not put plugin binaries on shell `PATH`.

Every GoC skill body is written with bare `goc ...` commands. Codex
does **not** put a plugin's `bin/` directory on shell PATH, so in a
plugin-only install `goc` is *not* a callable command even though the
engine is bundled and working. Running a bare `goc ...` (or `uv run
goc ...` outside a checkout) fails with `command not found` / `Failed
to spawn: goc`, and the agent should NOT fall back to editing deck
files by hand — that bypasses the schema, edge, and DoD contracts the
engine enforces.

Before running any `goc ...` line a skill gives you, resolve which of
three cases you are in. Do **not** create a global `~/.local/bin/goc`
shim — the engine is already bundled:

1. **Global CLI on PATH** — `command -v goc` succeeds. Run `goc ...`
   verbatim.
2. **Game-of-Cards source checkout** — you are inside the
   `game-of-cards` repo (a `pyproject.toml` naming `game-of-cards`
   beside a `goc/` package). Translate every bare `goc ...` to
   `uv run goc ...`, as the repo's `AGENTS.md` requires.
3. **Codex plugin-only install** — neither of the above. The bundled
   engine is reachable by absolute path; no global install is needed.
   Use the shipped helper, which locates and execs the sibling
   `bin/goc` wrapper. You loaded THIS skill from
   `<plugin-root>/skills/codex-kickoff/SKILL.md`, so the plugin root
   is the grandparent of this skill's own directory:

   ```bash
   <plugin-root>/skills/_goc-bootstrap.sh --help
   ```

   If you cannot derive the plugin root from the loaded skill path,
   locate the helper in the plugin cache:

   ```bash
   GOC_BOOTSTRAP=$(find "$HOME/.codex/plugins/cache" -path '*/game-of-cards/*/skills/_goc-bootstrap.sh' -type f -perm -111 -exec ls -t {} + 2>/dev/null | head -n 1)
   test -n "$GOC_BOOTSTRAP" || { echo "GoC Codex plugin bootstrap not found" >&2; exit 127; }
   "$GOC_BOOTSTRAP" --help
   ```

   The helper execs the bundled wrapper; the direct invocations work
   too. Codex substitutes `${PLUGIN_ROOT}` into plugin hook commands —
   prefer it when your shell already exports it:

   ```bash
   PLUGIN_ROOT="${PLUGIN_ROOT:-<grandparent of this skill's directory>}"

   "$PLUGIN_ROOT/bin/goc" --help
   # If the wrapper is not executable in your sandbox, invoke the engine
   # module directly — this is exactly what the wrapper does internally:
   PYTHONPATH="$PLUGIN_ROOT" python3 -m goc.cli --help
   ```

Substitute the resolved invocation for every bare `goc ...` the other
skills tell you to run. Only install the CLI with `pipx install
game-of-cards` or `uv tool install game-of-cards` when you want a real
`goc` binary on PATH (case 1), e.g. when using vendored Codex skills
without the plugin payload.

## Stage 3 — optional plugin hooks

Codex plugin hooks are opt-in in the current runtime. To enable the
GoC active-card reminder, prompt router, and pattern-generalization
check, add this to project `.codex/config.toml` or user
`~/.codex/config.toml`:

```toml
[features]
plugin_hooks = true
```

Restart Codex after changing the config. If hooks stay disabled, the
skills still work; only the automatic lifecycle reminders are absent.

## Stage 4 — confirm ready

Report:

```text
Codex-specific GoC setup is ready. The plugin provides the GoC skills;
plugin hooks run when `[features].plugin_hooks = true`.
```
