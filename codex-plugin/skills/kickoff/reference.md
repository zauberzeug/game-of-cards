# kickoff reference — install inventory and opt-in details

Companion to `SKILL.md`. Each section below is routed from the core
skill; read the one that matches the situation at hand.

## What gets installed

`goc install --briefing-target <file>` writes:

- `.game-of-cards/deck/` — the card deck (planning history; check this in).
- `.game-of-cards/config.yaml` — closure checks and workflow config
  (check this in).
- `<!-- BEGIN GOC -->` block in the chosen briefing file (`AGENTS.md`,
  `CLAUDE.md`, or `CLAUDE.local.md`) — discovery marker plus the
  agent-neutral runtime briefing (CLAUDE.md additionally inlines
  Claude-specific setup notes). Check the chosen file in unless it is
  `CLAUDE.local.md`, which is gitignored by default.

When Claude is installed and the chosen file is `AGENTS.md` or
`CLAUDE.local.md`, the install primitive also writes or refreshes
`CLAUDE.md` as an `@<chosen file>` import so Claude Code can load the
briefing. `--briefing-target CLAUDE.md` is the Claude-only path: the
full briefing lives inline there and `AGENTS.md` may be omitted.
Host-specific files like `.claude/skills/` are not written by the
kickoff flow — host-specific complement skills handle those.

Host-specific runtime affordances are **optional** and not strictly
required in source control:

- Claude Code skills, hooks, and `goc` CLI — install via the GoC Claude
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

## Team tip: external deck location

For teams that keep the deck outside the repo (e.g., a shared network
drive or separate Git repo), see the card
`support-external-game-of-cards-state-location` — it tracks the design
work for configurable deck paths. Offer this tip after the Stage 3
question when the persona is **Classical team**.

## Worktrees

By default each git worktree sees its own checkout's deck. Set
`workflow.worktree_deck: shared` in `.game-of-cards/config.yaml` (or
export `GOC_WORKTREE_DECK=shared`) to make all linked worktrees share
the deck in the primary working tree. Useful when one person juggles
multiple branches on the same project and wants a single queue. When
auto-commit is on, deck mutations from a worktree commit to the
primary working tree's branch, not the worktree's branch.

## Multi-team coordination opt-ins

Both default off; turn on for setups where several humans and agents
work the same deck across branches:

- `workflow.claim_push: true` — `goc status <title> active` pushes the
  claim commit and retries once on non-fast-forward; aborts with the
  racing worker's identity when a rebase conflict reveals a concurrent
  claim.
- `workflow.closure_on_integration: true` — `goc done` refuses to close
  unless HEAD is reachable from `origin/main`, so `done` means visible
  to every participant rather than locally DoD-complete.
