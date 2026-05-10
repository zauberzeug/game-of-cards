---
name: kickoff
description: Kick off GoC in a fresh repo — introduce GoC, ask which persona fits, confirm AGENTS.md merge, scaffold project state via `goc install`. AUTO-INVOKE when the user says "kickoff", "use GoC here", "set up game of cards", "initialize GoC", or when any GoC skill is first used in a repo with no `.game-of-cards/deck/` directory. Host-agnostic: per-host complements (`claude-kickoff`, future `openclaw-kickoff`) handle host-specific UX.
---

# Kick off GoC in this repo

This skill is the **host-agnostic onboarding dialog**: it introduces GoC,
asks a few focused questions, then runs `goc install` to scaffold project
state. It runs **idempotently** — every stage detects on-disk state before
asking, so a re-run on a partially set-up repo only asks for the answers
it cannot already derive.

The body covers what every host needs. Host-specific UX (permission
prompts, plugin install cadence, private-notes file) lives in a
complementary per-host skill that runs after this one — for example,
`claude-kickoff` on the host.

## Stage 0 — state detection sweep

Read all of the on-disk signals at once. Each subsequent stage will skip
its question(s) when the corresponding signal is already present.

```bash
ls .game-of-cards/deck/ 2>/dev/null && echo "DECK_EXISTS" || echo "deck_missing"
which goc 2>/dev/null && echo "GOC_ON_PATH" || echo "goc_missing"
grep -l '<!-- BEGIN GOC' AGENTS.md CLAUDE.md CLAUDE.local.md 2>/dev/null && echo "BRIEFING_MERGED" || true
[ -d .git ] && echo "GIT_REPO" || echo "git_missing"
```

Route on the results:

- **`DECK_EXISTS`** → report "GoC is already initialized in this repo —
  deck is live." and **stop**. Do not continue. This is the silent-exit
  branch the skill description promises.
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
| Classical team | `CLAUDE.md` — checked-in the host guidance (or `AGENTS.md` if cross-runtime visibility matters) |
| OSS / library evaluator | `AGENTS.md` — cross-runtime visible, minimal the agent assumption |
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
> instructions plus, when CLAUDE.md is the home, the the agent-specific
> setup notes inline. Future `goc upgrade` re-syncs only the chosen
> file.
>
> 1. **AGENTS.md** — read by Codex, Cursor, Copilot, OpenCode, Aider, and
>    the host (via `@AGENTS.md` import that `claude-kickoff` writes
>    into a minimal CLAUDE.md). Recommended for cross-runtime,
>    agent-runtime, and OSS-eval personas.
> 2. **CLAUDE.md** — read only by the host; the host-agnostic body
>    plus the the agent-specific extras live inline. **Cross-runtime
>    visibility is given up** (Codex/Cursor/etc. won't see the
>    briefing). Recommended for the agent-only teams.
> 3. **CLAUDE.local.md** — read only by the host, gitignored by
>    default. Recommended for solo/personal use where the deck is
>    private and you don't want a checked-in briefing.

Lead with the persona's recommended option but show all three. Record
the answer (one of `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`) for
Stage 4.

If the persona is **Classical team**, add after the question:

> **Team tip:** For teams that keep the deck outside the repo (e.g., a shared
> network drive or separate Git repo), see the card
> `support-external-game-of-cards-state-location` — it tracks the design work
> for configurable deck paths.

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

`goc install --briefing-target <file>` writes project state and merges
the briefing block into the chosen file (creating it if absent). The
other two candidate files are not touched. Host-specific files like
`.claude/skills/` are not written by this skill — host-specific
complement skills handle those.

After `goc install` returns, verify `.game-of-cards/deck/` exists and
the chosen file contains a `<!-- BEGIN GOC -->` block before
continuing.

---

## Stage 5 — confirm ready and hand off to host complement

Report to the user:

```
GoC is set up. The deck is live; `goc` and `goc validate` work.
```

If the host has its own kickoff complement (the host ships
`claude-kickoff`, OpenClaw ships its own equivalent when present), invite
the user to run it for host-specific finishing touches (permission
grants, agent-runtime hook registration, private notes files). Otherwise
recommend the next step:

```
What should the first card be?
```

The deck is now live. All other GoC skills work immediately — no further
generic kickoff needed.

---

## Reference: what gets installed

`goc install --briefing-target <file>` writes:

- `.game-of-cards/deck/` — the card deck (planning history; check this in).
- `.game-of-cards/config.yaml` — closure checks and workflow config
  (check this in).
- `<!-- BEGIN GOC -->` block in the chosen briefing file (`AGENTS.md`,
  `CLAUDE.md`, or `CLAUDE.local.md`) — discovery marker plus the
  agent-neutral runtime briefing (CLAUDE.md additionally inlines
  the agent-specific setup notes). Check the chosen file in unless it is
  `CLAUDE.local.md`, which is gitignored by default.

Host-specific runtime affordances are **optional** and not strictly
required in source control:

- the host skills, hooks, and `goc` CLI — install via the GoC the agent
  Code plugin (recommended) or `goc install --agents claude
  --local-skills` to vendor them.
- Codex skills — install via `goc install --agents codex`.
- OpenClaw skills, tool, and hooks — install via the OpenClaw plugin
  (ClawHub: `openclaw skills install game-of-cards`; npm:
  `game-of-cards`). Bundles the goc engine; only `python3` (3.10+) is
  required on the host. The OpenClaw plugin exposes `goc` as a
  registered tool rather than a shell-PATH binary — the model invokes
  it as it would any typed function.

The `<!-- BEGIN GOC -->` block is the canonical repo-visible signal
that GoC is in use. Agent plugins discover GoC through this marker
without requiring skills or hooks to be checked in.

## Reference: worktrees

By default each git worktree sees its own checkout's deck. Set
`workflow.worktree_deck: shared` in `.game-of-cards/config.yaml` (or
export `GOC_WORKTREE_DECK=shared`) to make all linked worktrees share
the deck in the primary working tree. Useful when one person juggles
multiple branches on the same project and wants a single queue. When
auto-commit is on, deck mutations from a worktree commit to the
primary working tree's branch, not the worktree's branch.

## Reference: multi-team coordination opt-ins

Both default off; turn on for setups where several humans and agents
work the same deck across branches:

- `workflow.claim_push: true` — `goc status <title> active` pushes the
  claim commit and retries once on non-fast-forward; aborts with the
  racing worker's identity when a rebase conflict reveals a concurrent
  claim.
- `workflow.closure_on_integration: true` — `goc done` refuses to close
  unless HEAD is reachable from `origin/main`, so `done` means visible
  to every participant rather than locally DoD-complete.
