---
name: bootstrap
description: "Bootstrap GoC in a fresh repo — detect if `.game-of-cards/deck/` exists, install the `goc` CLI if missing, then run `goc install` to scaffold project state and merge AGENTS.md / CLAUDE.md GoC blocks. AUTO-INVOKE when the user says \"use GoC here\", \"set up game of cards\", \"initialize GoC\", or when any GoC skill is first used in a repo with no `.game-of-cards/deck/` directory."
---

# Bootstrap GoC in this repo

This skill is the **plugin-first entry point**: the plugin is already installed,
and now the repo needs project state. It runs **idempotently** — if GoC is
already set up, it exits silently in a single sentence.

## What is checked, what is created, what confirmations to expect

| Step | Check | If absent | User confirmation? |
|---|---|---|---|
| 1 | `.game-of-cards/deck/` exists | Run bootstrap | — |
| 2 | `goc` on PATH | Offer CLI install | **Yes — Confirmation 1** |
| 3 | Project state scaffolded | Run `goc install` | **Yes — Confirmation 2** |

At most **two confirmations** on first use in a fresh environment. Zero
confirmations on subsequent repos once `goc` is already installed.

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

## Step 3 — scaffold project state

Tell the user: "Set up Game of Cards in this repo? This creates
`.game-of-cards/` and updates `AGENTS.md` / `CLAUDE.md`."

Wait for **Confirmation 2**.

Run:

```bash
goc install
```

`goc install` (default, plugin path) writes project state and merges GoC
guidance blocks into `AGENTS.md` and `CLAUDE.md`, but does NOT install
`.claude/skills/` or `.claude/hooks/` — those come from the plugin.

## Step 4 — confirm ready and suggest next step

Report to the user:

```
GoC is set up. All skills are live. What should the first card be?
```

The deck is now live. `Skill(create-card)`, `Skill(scan-deck)`, and all
other GoC skills work immediately — no further bootstrap needed.
