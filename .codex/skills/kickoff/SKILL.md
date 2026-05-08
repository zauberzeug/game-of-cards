---
name: kickoff
description: "Kick off GoC in a fresh repo — introduce GoC, ask which persona fits, confirm per-file AGENTS.md / CLAUDE.md / CLAUDE.local.md merges, run infrastructure preflight, then scaffold project state. AUTO-INVOKE when the user says \"kickoff\", \"use GoC here\", \"set up game of cards\", \"initialize GoC\", or when any GoC skill is first used in a repo with no `.game-of-cards/deck/` directory."
---

# Kick off GoC in this repo

This skill is the **project onboarding dialog**: it introduces GoC, asks a
few focused questions, checks that the infrastructure is ready, then runs
`goc install` with the flags that match the user's answers. It runs
**idempotently** — if GoC is already set up, it exits silently in a single
sentence.

> **Updating the plugin?** Run `/plugin marketplace update zauberzeug/game-of-cards`
> before `/plugin install` — Claude Code reuses its local marketplace clone and does
> not refresh it automatically. Skipping this step silently installs the old bytes.

## Stage 0 — already bootstrapped?

```bash
ls .game-of-cards/deck/ 2>/dev/null && echo "exists" || echo "missing"
```

If `.game-of-cards/deck/` exists: report "GoC is already initialized in this
repo — deck is live." and **stop**. Do not re-run install.

---

## Stage 1 — introduce GoC

Deliver this paragraph verbatim (no edits, no summarising):

> **Game of Cards (GoC)** is a lightweight, file-based methodology layer
> for software projects. It keeps a deck of cards — each card is a plain
> Markdown file with YAML frontmatter — that records every piece of
> persistent work: features, bugs, decisions, and experiments. The deck
> tracks status, value, and dependency edges between cards, so AI agents
> and human contributors share one authoritative view of what's in flight
> and what's next. GoC borrows from XP (user stories, spike experiments),
> Kanban (pull-based intake, explicit WIP limits), and Scrum (definition
> of done, backlog refinement). The CLI (`goc`) validates cards, renders
> board views, and gates closure on a per-card definition of done.

Then pause — do not continue to Stage 2 until the user acknowledges or
responds.

---

## Stage 2 — persona question

Ask the user **one question**:

> Which description best fits how you'll use GoC here?
>
> 1. **Solo / vibe-coder** — I'm the only contributor; I want a lightweight
>    personal task tracker with AI-agent help.
> 2. **Classical team** — We have a shared repo, multiple humans, and want
>    the deck as a shared source of truth alongside PRs and reviews.
> 3. **OSS / library evaluator** — I'm exploring GoC before deciding whether
>    to adopt it; I'd prefer not to merge anything into AGENTS.md or CLAUDE.md
>    yet.
> 4. **Agent-runtime / CI** — This repo is driven primarily by AI agents;
>    I want hooks and the CLI but minimal checked-in documentation overhead.

Record the user's answer. It drives routing in Stage 3.

| Persona | Stage 3 default |
|---|---|
| Solo / vibe-coder | Skip CLAUDE.md merge; offer AGENTS.md only |
| Classical team | Offer all three files; surface the external-deck-location guidance |
| OSS / library evaluator | Default all three to **No** — user must opt in explicitly |
| Agent-runtime / CI | Default CLAUDE.md and AGENTS.md to **No**; offer CLAUDE.local.md only |

---

## Stage 3 — per-file merge opt-in

Ask three separate yes/no questions. Use the persona defaults from Stage 2,
but always ask — never silently skip based on the persona.

**Question A — CLAUDE.md**

> Merge GoC guidance into `CLAUDE.md`? This adds a `<!-- BEGIN GOC -->` block
> with Claude Code-specific instructions (skill surface, hook descriptions,
> first-use setup). The block is marker-bounded and survives future `goc upgrade`
> runs. Your existing content above and below the markers is untouched.
>
> Add to CLAUDE.md? [yes/no]

**Question B — AGENTS.md**

> Merge GoC guidance into `AGENTS.md`? This adds a `<!-- BEGIN GOC -->` block
> with agent-neutral instructions (deck philosophy, CLI verb table, operating
> modes). Suitable for Codex, OpenAI Code, and any runtime that reads AGENTS.md.
>
> Add to AGENTS.md? [yes/no]

**Question C — CLAUDE.local.md** (only prompt if the user answered No to both A and B, or if persona is agent-runtime)

> Add a minimal `CLAUDE.local.md` stub? This gives Claude Code a private,
> untracked file to record project-local notes without touching checked-in
> docs.
>
> Create CLAUDE.local.md stub? [yes/no]

If the persona is **Classical team**, add after all three questions:

> **Team tip:** For teams that keep the deck outside the repo (e.g., a shared
> network drive or separate Git repo), see the card
> `support-external-game-of-cards-state-location` — it tracks the design work
> for configurable deck paths.

Record the three answers. Pass them to Stage 4 as flags for `goc install`.

---

## Stage 4 — infrastructure preflight

Run both checks in sequence.

### Check A — `goc` on PATH

```bash
which goc 2>/dev/null || echo "missing"
```

If `goc` is missing:

1. Tell the user: "`goc` CLI is not installed. Install it now via
   `uv tool install game-of-cards`?"
2. Wait for confirmation.
3. Run `uv tool install game-of-cards`. If `uv` is not available, fall back to
   `pipx install game-of-cards`. If neither is available, tell the user to run
   `pip install game-of-cards` in their environment and retry once it's on PATH.
4. Verify with `goc --version` before continuing.

If `goc` is already on PATH: report "`goc` is on PATH — OK." and continue.

### Check B — `Bash(goc:*)` permission

Use the Read tool on `~/.claude/settings.json` (and, if it exists, the
project's `.claude/settings.json`). Look for `"Bash(goc:*)"` inside
`permissions.allow`.

If absent in both, tell the user **verbatim**:

> Claude Code needs explicit permission to run `goc`. Please add
> `"Bash(goc:*)"` to the `permissions.allow` array in
> `~/.claude/settings.json` (or your project's `.claude/settings.json`),
> then **fully restart Claude Code** for the change to take effect.
>
> ```json
> {
>   "permissions": {
>     "allow": ["Bash(goc:*)"]
>   }
> }
> ```
>
> I'll wait for you to confirm before continuing.

Wait for confirmation. Do not attempt to add the allowance yourself — Claude
Code's policy refuses self-grants on its own settings file.

If `"Bash(goc:*)"` is already present: report "Permission is set — OK." and
continue.

---

## Stage 5 — scaffold project state

Summarise the three merge answers collected in Stage 3, then ask:

> Ready to scaffold? This will create `.game-of-cards/` and the files you
> selected above. Confirm? [yes/no]

On confirmation, build the `goc install` invocation from the Stage 3 answers:

- If the user said **Yes** to CLAUDE.md and AGENTS.md: `goc install` (defaults merge both)
- If the user said **No** to CLAUDE.md only: `goc install --no-claude-md`
- If the user said **No** to AGENTS.md only: `goc install --no-agents-md`
- If the user said **No** to both: `goc install --no-claude-md --no-agents-md`
- If CLAUDE.local.md was requested: create a minimal stub after `goc install` runs

> **Note for this repo (game-of-cards source tree):** Translate bare `goc`
> commands to `uv run goc` when working in the goc package source tree itself.

`goc install` writes project state and merges GoC guidance blocks into the
requested files, but does NOT install `.claude/skills/` or `.claude/hooks/`
— those come from the plugin.

---

## Stage 6 — confirm ready and suggest next step

Report to the user:

```
GoC is set up. All skills are live. What should the first card be?
```

The deck is now live. `Skill(create-card)`, `Skill(scan-deck)`, and all
other GoC skills work immediately — no further kickoff needed.
