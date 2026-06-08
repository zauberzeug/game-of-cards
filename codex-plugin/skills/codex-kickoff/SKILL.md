---
name: codex-kickoff
description: "Codex-specific complement to the generic kickoff skill — install the GoC Codex plugin from the repo marketplace, explain plugin hook activation, and verify the goc CLI path. AUTO-INVOKE after `Skill(kickoff)` completes in Codex, or when the user says \"finish kickoff for Codex\", \"set up Codex plugin\", \"install the GoC Codex plugin\", or \"enable GoC hooks in Codex\"."
---

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

## Stage 2 — know what the plugin provides

The Codex plugin supplies:

- GoC skills from `goc/templates/skills/`, filtered for Codex and
  packaged under the plugin's `skills/` directory.
- Lifecycle hooks under `hooks/hooks.json`.
- A bundled `goc/` engine mirror and `bin/goc` wrapper for hosts or
  future Codex builds that expose plugin binaries.

Codex does not currently document plugin `bin/` auto-PATH behavior.
When a skill tells you to run `goc`, prefer the normal project command:

```bash
goc --help
```

Inside the `game-of-cards` source checkout itself, follow the repo
guidance and translate bare `goc ...` examples to:

```bash
uv run goc ...
```

If neither command works, install the CLI with `pipx install
game-of-cards` or use the plugin's bundled engine directly from a
checked-out plugin payload:

```bash
PYTHONPATH=/path/to/game-of-cards/codex-plugin python3 -m goc.cli --help
```

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
