---
name: kickoff
description: "Kick off GoC in a fresh repo — introduce GoC, pick a persona, confirm the AGENTS.md merge, scaffold via goc install. AUTO-INVOKE on \"kickoff\", \"use GoC here\", \"set up game of cards\", or when any GoC skill runs in a repo with no deck directory."
---

## Codex GoC Command

When this skill says `goc ...`, resolve the executable before running the
command:

- In the `game-of-cards` source checkout, use `uv run goc ...`.
- If `goc` is already on `PATH`, use `goc ...`.
- If this skill is loaded from the Game of Cards Codex plugin, use the
  bundled helper at `<plugin-root>/skills/_goc-bootstrap.sh ...`; the plugin
  root is the parent directory that contains both `skills/` and `bin/`.
- If the plugin root is not obvious from the loaded skill path, locate the
  helper with:

```bash
GOC_BOOTSTRAP=$(find "$HOME/.codex/plugins/cache" -path '*/game-of-cards/*/skills/_goc-bootstrap.sh' -type f -perm -111 -exec ls -t {} + 2>/dev/null | head -n 1)
test -n "$GOC_BOOTSTRAP" || { echo "GoC Codex plugin bootstrap not found" >&2; exit 127; }
"$GOC_BOOTSTRAP" --help
```

Use that helper path in place of bare `goc` for the rest of the skill. Do not
edit deck files directly just because `goc` is not on `PATH`.


## When to invoke

Invoke when the user says "kickoff", "use GoC here", "set up game of cards", "initialize GoC", or when any GoC skill is first used in a repo with no `.game-of-cards/deck/` directory. Host-agnostic: per-host complements (`claude-kickoff`, `codex-kickoff`, `openclaw-kickoff`) handle host-specific UX.

# Kick off GoC in this repo

This skill is the **host-agnostic onboarding dialog**: it introduces GoC,
asks a few focused questions, then runs `goc install` to scaffold project
state. It runs **idempotently** — every stage detects on-disk state before
asking, so a re-run on a partially set-up repo only asks for the answers
it cannot already derive.

The body covers what every host needs. Host-specific UX (permission
prompts, plugin install cadence, private-notes file) lives in a
complementary per-host skill that runs after this one — for example,
`claude-kickoff` on Claude Code.

**Details live in `reference.md`** — a sibling file in this skill's
directory. Read the named section only when the situation applies:

| Situation | `reference.md` section |
|---|---|
| The user asks what install will write / wrote | What gets installed |
| Stage 3 persona is Classical team | Team tip: external deck location |
| The repo uses git worktrees | Worktrees |
| Several humans + agents share one deck | Multi-team coordination opt-ins |

## Stage 0 — state detection sweep

Read all of the on-disk signals at once. Each subsequent stage will skip
its question(s) when the corresponding signal is already present.

```bash
ls .game-of-cards/deck/ 2>/dev/null && echo "DECK_EXISTS" || echo "deck_missing"
which goc 2>/dev/null && echo "GOC_ON_PATH" || echo "goc_missing"
grep -l '<!-- BEGIN GOC' AGENTS.md CLAUDE.md CLAUDE.local.md 2>/dev/null && echo "BRIEFING_MERGED" || true
grep -E '^autonomy:' .game-of-cards/config.yaml 2>/dev/null && echo "AUTONOMY_SET" || true
[ -d .git ] && echo "GIT_REPO" || echo "git_missing"
```

Route on the results:

- **`DECK_EXISTS` + `AUTONOMY_SET`** → report "GoC is already initialized
  in this repo — deck is live." and **stop**. Do not continue. This is
  the silent-exit branch the skill description promises.
- **`DECK_EXISTS` without `AUTONOMY_SET`** → install completed previously
  but the autonomy question was deferred. Skip Stages 1–5 and jump
  directly to Stage 6 so the user can pick a mode now.
- **`goc_missing`** → halt at this stage. Tell the user: "`goc` CLI is
  not installed. Install it (e.g. `pipx install game-of-cards`, or use
  whatever plugin/runtime ships goc for your host) and re-run kickoff."
  Do not proceed without `goc`.
- **`git_missing`** → surface this one-line notice once, then continue:
  "No git repository here — version control is not set up. The deck
  assumes git (auto_commit, claim history, closure logs); run `git init`
  if you want the deck tracked." Do not explain further; the user
  decides whether to `git init` before or after kickoff completes.
- **Otherwise** → continue. Hold the detected flags in mind through the
  rest of the flow.

---

## Stage 1 — introduce GoC

Skip this stage if `BRIEFING_MERGED` was detected in Stage 0 — it means
the user has engaged with kickoff before, and replaying the intro is
noise.

Otherwise, deliver this paragraph verbatim (no edits, no summarising):

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

Skip this stage if `BRIEFING_MERGED` was already detected (Stage 3 has
nothing left to ask, so persona is moot).

Otherwise, ask the user **one question**:

> Which description best fits how you'll use GoC here?
>
> 1. **Solo / vibe-coder** — I'm the only contributor; I want a lightweight
>    personal task tracker with AI-agent help.
> 2. **Classical team** — We have a shared repo, multiple humans, and want
>    the deck as a shared source of truth alongside PRs and reviews.
> 3. **OSS / library evaluator** — I'm exploring GoC before deciding whether
>    to adopt it; I'd prefer to keep the repo footprint minimal.
> 4. **Agent-runtime / CI** — This repo is driven primarily by AI agents;
>    I want the CLI plus a runtime briefing that any agent can read.

Record the user's answer. It drives the briefing-target recommendation
in Stage 3.

| Persona | Recommended briefing target |
|---|---|
| Solo / vibe-coder | `CLAUDE.local.md` — gitignored, no commit footprint |
| Classical team | `CLAUDE.md` — checked-in Claude Code guidance (or `AGENTS.md` if cross-runtime visibility matters) |
| OSS / library evaluator | `AGENTS.md` — cross-runtime visible, minimal Claude assumption |
| Agent-runtime / CI | `AGENTS.md` — read by every modern agent runtime |

---

## Stage 3 — pick a briefing home

Skip this question if Stage 0 detected `BRIEFING_MERGED` — read the
existing target off disk (`grep -l '<!-- BEGIN GOC' AGENTS.md CLAUDE.md
CLAUDE.local.md`) and pass that file to Stage 4.

Otherwise, ask the user **one question**, ordering the options by
persona but always offering all three:

> Where should the GoC briefing live in this repo? The briefing is one
> marker-bounded `<!-- BEGIN GOC -->` block — agent-neutral runtime
> instructions plus, when CLAUDE.md is the home, the Claude-specific
> setup notes inline. Future `goc upgrade` re-syncs only the chosen
> file.
>
> 1. **AGENTS.md** — read by Codex, Cursor, Copilot, OpenCode, Aider, and
>    Claude Code (via the `@AGENTS.md` import that `goc install` /
>    `goc upgrade` writes into CLAUDE.md when Claude is installed).
>    Recommended for cross-runtime,
>    agent-runtime, and OSS-eval personas.
> 2. **CLAUDE.md** — read only by Claude Code; the host-agnostic body
>    plus the Claude-specific extras live inline. **Cross-runtime
>    visibility is given up** (Codex/Cursor/etc. won't see the
>    briefing). Recommended for Claude-only teams.
> 3. **CLAUDE.local.md** — read only by Claude Code, gitignored by
>    default. Recommended for solo/personal use where the deck is
>    private and you don't want a checked-in briefing.

Lead with the persona's recommended option but show all three. Record
the answer (one of `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`) for
Stage 4. If the persona is **Classical team**, follow with the tip in
`reference.md` § Team tip: external deck location.

---

## Stage 4 — scaffold project state

Summarise the briefing-target answer collected in Stage 3, then ask:

> Ready to scaffold? This will create `.game-of-cards/` and merge the GoC
> briefing into `<chosen file>`. Confirm? [yes/no]

On confirmation, run `goc install --briefing-target <chosen file>` (the
flag tells the install primitive which file holds the briefing block;
omit it only when the user wants the default `AGENTS.md`).

> **Note for this repo (game-of-cards source tree):** Translate bare `goc`
> commands to `uv run goc` when working in the goc package source tree itself.

The command writes project state and merges the briefing block into
the chosen file (creating it if absent) — full inventory and the
CLAUDE.md-import behaviour in `reference.md` § What gets installed.
After `goc install` returns, verify `.game-of-cards/deck/` exists and
the chosen file contains a `<!-- BEGIN GOC -->` block before
continuing.

---

## Stage 5 — confirm ready

Report to the user:

```
GoC is set up. The deck is live; `goc` and `goc validate` work.
```

Continue to Stage 6.

---

## Stage 6 — pick an autonomy mode

Skip this stage if Stage 0 detected `AUTONOMY_SET` — the user already
chose a mode on a previous run and re-asking is noise.

Otherwise, ask the user **one question**:

> How would you like cards to be pulled off the queue? GoC's whole point
> over a plain task list is that the deck is designed to be drained
> autonomously when `human_gate: none`. Pick a mode (you can change
> later by editing `.game-of-cards/config.yaml`):
>
> 1. **Manual** — you file cards and work them by hand. No setup.
> 2. **Supervised loop** — your host runs `pull-card` on a timer inside
>    a session you watch (e.g. `/loop /pull-card 30m` on Claude Code).
>    Best for trying GoC before automating further.
> 3. **Local cron** — a cron job runs `pull-card` unattended on your
>    machine. Best for solo workflows that trust the agent to drain
>    `human_gate: none` cards overnight.
> 4. **CI / GitHub Action** — a workflow runs `pull-card` on a schedule
>    in CI. Best for shared decks across a team.
> 5. **Skip for now** — defer the choice; kickoff will ask again on
>    next run.

Record the answer in `.game-of-cards/config.yaml` as a top-level
`autonomy:` key with one of these values: `manual`, `loop`, `cron`,
`action`. For the **Skip for now** option, do not write the key — its
absence is what makes the next kickoff re-ask. Stage 0 detects the
written key on re-run and skips this stage.

If the host has its own kickoff complement (Claude Code ships
`claude-kickoff`, OpenClaw ships its own equivalent when present),
invite the user to run it now — the complement provides the
host-specific recipe for the chosen mode (e.g., wiring `/loop`,
suggesting a cron line, or scaffolding a workflow file). Otherwise
recommend the next step:

```
What should the first card be?
```

The deck is now live. All other GoC skills work immediately — no further
generic kickoff needed.
