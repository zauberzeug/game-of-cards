# Marketplace submission draft (2026-05-08)

Draft text for the Anthropic community plugin directory submission form
at `clau.de/plugin-directory-submission`. Saved here so the wording
survives form drafts being lost or rejected and can be iterated against
by future card pickup.

## Plugin description

**Game of Cards (GoC)** — agile for the age of agents. GoC turns work
into durable, inspectable Markdown cards that humans and AI agents
collaborate on. Agents pull cards autonomously, work them under a
per-card Definition of Done, and close them via a DoD-gated
`finish-card` skill; humans steer by curating the queue and resolving
decision gates. Lineage: XP user stories + Kanban pull + Scrum DoD.
The plugin ships 14 skills (`kickoff`, `scan-deck`, `create-card`,
`finish-card`, `pull-card`, `audit-deck`, `refine-deck`, `standup`,
`retrospective`, …) and 3 runtime hooks that surface active cards,
route work-initiating prompts, and prompt the agent to consider
filing a generalization card after code-mutating turns. Self-contained
— no separate `pipx install`; the GoC CLI is bundled and runs via
`uv`.

## Example use-cases

1. **Solo developer / vibe-coder personal task tracker.** Backlog
   lives in the repo, not a separate SaaS. Saying "let's add X"
   auto-files a card; the agent claims it, works it, and closes it
   under DoD gating. The developer reviews diffs and resolves any
   decision-gated cards.

2. **Small team — deck as shared source of truth alongside PRs.**
   Cards capture both the work and the decisions that drove it. New
   contributors (human or AI) read the deck cold to understand
   what's in flight. The DoD-checkbox closure contract keeps "done"
   honest across reviewers.

3. **Autonomous agent runtime (`/loop` or scheduled cron).** Agents
   drain the highest-leverage `human_gate: none` card off the queue
   via `Skill(pull-card)`, work it end-to-end, and commit.
   Decision-class problems raise the gate (Andon cord) and park the
   card; humans resolve them later via `Skill(decide-card)` and the
   loop resumes.

4. **OSS / library evaluation without commitment.** A developer
   tries GoC on a real codebase before merging anything into
   AGENTS.md or CLAUDE.md. The `kickoff` skill defaults all merges
   to "no" for this persona; the deck still works locally;
   abandonment leaves nothing behind in checked-in docs.
