# Background — context for Game of Cards

This document collects the "why" that doesn't belong on the front page: where the name comes from, which agile lineage the methodology inherits, and how it relates to other agent-coding tools.

The CLI reference is in [`goc.md`](goc.md). The methodology's day-to-day surface is in the [README](README.md).

## Why the name "Game of Cards"

The name is a deliberate Game-of-Thrones echo. The match isn't the fantasy setting — it's GRRM's narrative grammar, which is the most-cited literary reference for complex political systems with many semi-autonomous actors and emergent outcomes.

### Why this analogy and not "agile" or "Kanban"

Traditional agile methodologies (Scrum, Kanban, XP) presume a team can:

1. See the full backlog
2. Prioritize predictably
3. Execute plans without major surprise
4. Recover from disruption via team coordination

That worldview maps onto small co-located human teams shipping features. It does *not* map onto a swarm of AI agents working a complex codebase, which is the operating environment Game of Cards is designed for. In that environment:

- **Many actors, private agendas.** N parallel Claude sessions + M scheduled background agents are simultaneously claiming, working, parking, and committing cards. Each has local context the others can't see. Each agent's "small good decision" can ripple into another agent's blocker.
- **Events surface; you don't drive.** An agent doing a literature audit on card X discovers a blocker in card Y that nobody filed. A wake-time test fails and reveals a regime breach in an axiom that closed six months ago. You don't plan these events; they arrive, and the only question is how the system responds.
- **No protagonist safety.** Any card can be superseded, any decision can be reconsidered when fresh evidence lands, any closed bug can be reopened by a regression. GRRM's "main characters die in chapter 9" maps onto "this card you closed last week is now superseded by today's audit."
- **High stakes, irreducible uncertainty.** When the codebase is a research substrate rather than a feature factory, wrong derivation closures compound; technical debt accumulates as accepted-then-contradicted decisions; the wrong abstraction at axiom level breaks every downstream demo.

### What this changes about agent behavior

Specific patterns Game of Cards requires that traditional agile doesn't:

1. **The Andon-cord (decision-gate / session-gate cards).** A card can park itself with `human_gate: decision` when it hits a question only a human can resolve (framework derivation, mechanism choice, lit-anchored default). The autonomous swarm does *not* decide on the human's behalf. The human's lowering action (`goc decide`) is the "council scene" — work pauses, an authority decides, the line resumes. Lean's actual Andon-cord pattern, but with GRRM's "you cannot make this call without the right authority in the room" framing.
2. **Cards survive in supersession chains, not deletion.** When a card is wrong, it doesn't get deleted — it gets `status: superseded` with a pointer to its successor. The deck preserves the political history: who decided what, when, why, what new evidence retired it. Like GRRM's chapter structure, the past stays on the record even after the present has moved on.
3. **The user's words ARE the briefing.** A human typing "I want a CSV export button" produces, silently, a card filed with the user's framing as the body. The system never announces "I'll file a card now…" — bookkeeping is invisible. From the user's seat: they see the button. From the deck's seat: every persistent decision has a card with its own audit trail. Vibe coders never need to learn the methodology; the rigor is preserved invisibly.
4. **Multiple parallel realities are normal.** N sessions + M scheduled agents working the same project is the default mode, not the exception. The `status: active` field is the soft lock; git's merge handles claim-races. The deck design assumes the swarm is heterogeneous and partially-coordinated — exactly like GRRM's Westeros: nobody has the full picture, decisions are made on partial information, and the realm muddles forward anyway.

### What an LLM reading the deck should internalize

- **Don't expect the queue to be "finishable"** — new cards arrive faster than old ones close, because new cards surface from old ones' completions. That's not a bug; that's the system working.
- **Don't decide on the human's behalf when a card is gate-parked.** Raising the gate is a feature; lowering it is the human's action.
- **Don't delete cards or rewrite history.** Supersession chains are sacred. Future agents reconstruct the political history by walking them.
- **Trust the deck over the conversation.** Memory is fast and lossy; the deck is slow and authoritative. When in doubt, scan the deck.
- **Surprise findings during audits are expected.** The five-agent literature audit that surfaced three follow-on cards from a two-line prose bug isn't unusual — it's how the methodology surfaces what the swarm couldn't see from one angle alone.

The single-line summary: **Game of Cards treats AI-swarm software work as a political-emergent system rather than a planned-execution pipeline, and the Game-of-Thrones name is a load-bearing signal of that worldview.**

## The agile lineage

Three ideas from the 1990s, none of them Game of Cards' own, all still in use:

- **One card, one thing** — XP, Beck 1999. Small enough to fit on an index card. Enough context that anyone, or anything, can pick it up.
- **Definition of Done** — Scrum, Sutherland & Schwaber. A card isn't closed because someone said so. It's closed because a checklist is satisfied.
- **Status, not location** — Kanban, Anderson, after Toyota. A card stays at `deck/<title>/` while it moves through *open → active → done*. Cross-references don't break.

The argument for taking these seriously *now* is that AI coding agents are a harder handoff problem than the human teams those ideas were built for. Agents read the full backlog every session, re-derive context from scratch, and never remember yesterday. A card with a stable URL, a machine-checkable closure contract, and a self-contained body stops being "discipline" and starts being how the agent finds its bearings. The 1990s primitives were right; AI agents make their handoff value more obvious.

## Where it fits among agent-coding tools

The current agent-development ecosystem is real and useful. [Spec Kit](https://github.com/github/spec-kit) gives spec-driven development templates and bootstrapping. [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) brings AI-driven agile workflows and specialized agent roles. [Agent OS](https://github.com/buildermethods/agent-os) captures project standards and specs. [Ruler](https://github.com/intellectronica/ruler) distributes one instruction set to many agent config files. [AGENTS.md](https://agents.md/) is the shared markdown guidance format many agents read.

Game of Cards is narrower than those. It gives a repo-local backlog lifecycle: stable card paths, explicit status and gate fields, append-only logs, and a Definition of Done that the CLI refuses to close while unchecked boxes remain.

That means it can sit underneath other tools. It does not choose your planning method, author a PRD, pick personas, or orchestrate a swarm. It gives humans and agents a durable place to put work and a mechanical rule for when that work is actually done.

## Agent harnesses

`goc install` output is split into three layers:

- **Project state** — `deck/`, `.game-of-cards/` — always written. This is the methodology's durable state; no agent runtime required.
- **Guidance** — `AGENTS.md`, `.pre-commit-config.yaml` — written by default, readable by any agent that follows `AGENTS.md` conventions.
- **Runtime affordances** — skills, hooks, and agent-specific guidance files — written only when an agent harness is selected.

Harness selection controls which runtime affordances are installed:

- `--agents claude` writes `.claude/skills/`, `.claude/hooks/` (one script per file under `goc/templates/hooks/`), and `CLAUDE.md`.
- `--agents codex` writes Codex-readable skills under `.codex/skills/`, without Claude-only hooks.
- `--no-harness` installs project state and guidance only — no skills, no hooks, no agent-specific files.

Detection is intentionally simple: Claude markers such as `CLAUDE.md` or `.claude/` select the Claude harness; Codex markers such as `AGENTS.md` or `.codex/` select the Codex harness; both marker families install both harnesses. Explicit `--agents`, `--claude`, `--codex`, and `--no-harness` flags override detection for scripted installs.

OpenCode is a free path: it already reads `.claude/skills/`, so `goc install --agents claude` gives OpenCode the skill files without a separate OpenCode shim. The Claude `UserPromptSubmit` hook is not part of that compatibility path; hooks remain Claude Code-specific.

[OpenClaw](https://openclaw.ai) is the other supported runtime, but it sits beside the `--agents` matrix rather than inside it. OpenClaw plugins are TypeScript entry points that register typed tools and event handlers — there is no shell-PATH binary, no auto-discovered `.claude/skills/` directory, and no `goc install` step on the consumer side. So OpenClaw ships as a separate plugin payload (`openclaw-plugin/`) that bundles the goc engine inside the npm package and registers `goc` as an OpenClaw tool. Skills are workspace-tier `SKILL.md` directories ported once via `scripts/port_skills_to_openclaw.py`; the three Claude lifecycle hooks (`SessionStart`, `UserPromptSubmit`, `Stop`-equivalent) are reimplemented as TypeScript event handlers registered via `api.on()`. Consumers install with `openclaw skills install game-of-cards`; the only host prerequisite is `python3` (3.10+).

To add another agent, file an issue or PR that adds `goc/templates/agents/<agent>/manifest.json`, any renderer support needed for that agent's file format, and installer tests covering `goc install --agents <agent>` plus `goc upgrade --agents <agent>`.

## Contributing

When working from a checkout of this repo, use the repo-local form so you run the checked-out code instead of any globally installed `goc`:

```bash
uv run goc install --agents codex
```

This repo uses Game of Cards to track its own work. The `deck/` directory is the backlog; each card is a directory under that with a frontmatter-validated `README.md` and an append-only `log.md`. If you want to contribute to existing work, pick an open card and update that card as part of your change. If you want to propose new work, run `uv run goc new "card title"` to scaffold the card directory.

We are open to contributions of all sizes, from fixing typos to implementing new features. If you're not sure where to start, ask your LLM to check the open cards in `deck/` and see if anything catches your eye. If you want to propose a new feature or improvement, feel free to file an issue or PR; we will convert issues into cards quickly.
