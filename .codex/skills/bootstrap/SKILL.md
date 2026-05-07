---
name: bootstrap
description: "Bootstrap GoC in a fresh repo — detect if `.game-of-cards/deck/` exists, install the `goc` CLI if missing, then run `goc install` to scaffold project state and merge AGENTS.md / CLAUDE.md GoC blocks. AUTO-INVOKE when the user says \"use GoC here\", \"set up game of cards\", \"initialize GoC\", or when any GoC skill is first used in a repo with no `.game-of-cards/deck/` directory."
---

# Bootstrap GoC in this repo

This skill is the **plugin-first entry point**: the plugin is already installed,
and now the repo needs project state. It runs **idempotently** — if GoC is
already set up, it exits silently in a single sentence.

> **Updating the plugin?** Run `/plugin marketplace update zauberzeug/game-of-cards`
> before `/plugin install` — Claude Code reuses its local marketplace clone and does
> not refresh it automatically. Skipping this step silently installs the old bytes.

## What is checked, what is created, what confirmations to expect

| Step | Check | If absent | User confirmation? |
|---|---|---|---|
| 1 | `.game-of-cards/deck/` exists | Run bootstrap | — |
| 2 | `goc` on PATH | Offer CLI install | **Yes — Confirmation 1** |
| 3 | `Bash(goc:*)` in `permissions.allow` | Ask user to add it manually | **Yes — Confirmation 2** |
| 4 | Project state scaffolded | Run `goc install` | **Yes — Confirmation 3** |

At most **three confirmations** on first use in a fresh environment. Zero
confirmations on subsequent repos once `goc` is allowed and installed.

Created by this skill (via `goc install`):
- `.game-of-cards/deck/` — the card deck directory
- `.game-of-cards/config.yaml` — closure checks and workflow config
- GoC block in `AGENTS.md` — discovery marker + methodology briefing
- GoC block in `CLAUDE.md` — Claude Code-specific guidance

NOT created (these come from the plugin already installed):
- `.claude/skills/` — lives in the plugin cache
- `.claude/hooks/` — lives in the plugin cache

## Step 1 — check if already bootstrapped

```bash
ls .game-of-cards/deck/ 2>/dev/null && echo "exists" || echo "missing"
```

If `.game-of-cards/deck/` exists: report "GoC is already initialized in this
repo — deck is live." and **stop**. Do not re-run install.

## Step 2 — ensure `goc` is on PATH

```bash
which goc 2>/dev/null || echo "missing"
```

If `goc` is missing:

1. Tell the user: "`goc` CLI is not installed. Install it now via
   `uv tool install game-of-cards`?"
2. Wait for **Confirmation 1**.
3. Run `uv tool install game-of-cards`. If `uv` is not available, fall
   back to `pipx install game-of-cards`. If neither is available, tell
   the user to run `pip install game-of-cards` in their environment and
   retry once it's on PATH.
4. Verify with `goc --version` before continuing.

If `goc` is already on PATH: skip this step silently.

## Step 3 — ensure Claude Code allows `goc` to run

Even with `goc` on PATH, Claude Code's bash-permission policy denies
skill-body invocations of unfamiliar commands by default — especially
right after a plugin install. Without an allowance rule, every `!`goc …``
block in every other skill will fail with "Permission for this action has
been denied."

Use the Read tool on `~/.claude/settings.json` (and, if it exists, the
project's `.claude/settings.json`). Look for `"Bash(goc:*)"` inside
`permissions.allow`.

If absent in both, tell the user **verbatim**:

> Claude Code needs explicit permission to run `goc`. Please add
> `"Bash(goc:*)"` to the `permissions.allow` array in
> `~/.claude/settings.json` (or your project's `.claude/settings.json`),
> then **fully restart Claude Code** for the change to take effect.
> I'll wait for you to confirm before continuing.

Wait for **Confirmation 2**. Do not attempt to add the allowance yourself
— Claude Code's policy refuses self-grants on its own settings file.

If `"Bash(goc:*)"` is already present: skip this step silently.

## Step 4 — scaffold project state

Tell the user: "Set up Game of Cards in this repo? This creates
`.game-of-cards/` and updates `AGENTS.md` / `CLAUDE.md`."

Wait for **Confirmation 3**.

Run:

```bash
goc install
```

`goc install` (default, plugin path) writes project state and merges GoC
guidance blocks into `AGENTS.md` and `CLAUDE.md`, but does NOT install
`.claude/skills/` or `.claude/hooks/` — those come from the plugin.

## Step 5 — confirm ready and suggest next step

Report to the user:

```
GoC is set up. All skills are live. What should the first card be?
```

The deck is now live. `Skill(create-card)`, `Skill(scan-deck)`, and all
other GoC skills work immediately — no further bootstrap needed.
