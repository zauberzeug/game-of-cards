# Who Game of Cards is for

Game of Cards is for **AI-first projects** — work where a human collaborates with one or more AI agents in a project folder. The deck is files at `.game-of-cards/deck/`; optionally git-backed so memory survives sessions and agents see each other's work.

Three on-ramps illustrate how that fit shows up today: vibe-coders, solo developers, and multi-agent coordinators. They share the use case and the deck — different reasons to start, same tool. Below the on-ramps: variations in how the audience configures the tool, and the audiences GoC does *not* serve yet.

This file exists because most disagreement about GoC's positioning is downstream of unspoken mismatch. An evaluator with strict commit hygiene hits invasive-install pain; an evaluator looking for a static feature planner finds the autonomous loop oversized; an evaluator with a non-code domain wonders whether the engine cares. Naming the audience precisely — and the situations it doesn't yet cover — saves that round-trip.

## The three on-ramps

The on-ramps share the use case and the deck. They differ only in *what makes GoC worth picking up* — different value props, same fit. You may be all three on different days; nothing in the engine cares which on-ramp you came in through.

### The vibe-coder (AI-first)

**Who.** Doesn't read code. Builds apps by describing what they want and letting the agent ship it. Comfortable in plain English; uncomfortable in a terminal.

**What they need from GoC.**
- The agent should hold context between sessions — not start from zero each time.
- Decisions the human made yesterday should still be visible today.
- "What's left to do?" should be a question the agent can answer without re-reading the whole project.

**What they don't care about.**
- Branch hygiene, commit messages, CI gates.
- Reading the cards themselves. Cards are scaffolding the agent uses; the human stays at the prompt.

**Workflow shape.** Mainline-only. Agent commits autonomously. Deck lives inside the repo (default: `.game-of-cards/deck/`). CLAUDE.md / AGENTS.md merge is fine — the agent reads it, the human doesn't.

**Trade-off they accept.** Partial features in `main`. Faster forward motion in exchange for less guarantee that any single commit is releasable.

> **Non-code AI-first projects use the same on-ramp.** A recipe-book
> author orchestrating Claude on draft / test / publish, a researcher
> using an agent to manage a long literature review, a writer running
> a novel-revision pipeline — these are vibe-coders in non-code
> domains. The engine is domain-agnostic; the deck is files; the
> CLI tolerates non-git directories. The one real gap today is
> custom statuses (e.g. `drafting → review → published` instead of
> `open → active → done`), tracked by
> [`support-custom-card-workflows-and-statuses`](.game-of-cards/deck/support-custom-card-workflows-and-statuses).
> Until that ships, non-code users map their workflow onto the built-in
> statuses or wait. Examples and skills throughout this repo currently
> assume a code project; that's documentation shape, not engine shape.

---

### The solo developer (AI-augmented)

**Who.** Knows code. Has used `TODO.md` files, GitHub issues for personal projects, or a Notion board — and found all of them lossy. Wants their AI to keep state across the half-hour gaps between coding sessions.

**What they need from GoC.**
- Structured replacement for `TODO.md`: each card has a Definition of Done that the CLI refuses to close until satisfied.
- Cross-session memory: re-opening the project tomorrow, the agent can scan the deck and know what's in flight.
- Multi-step features: a card can hold a week of work without losing the original framing.

**What they don't care about.**
- Multi-agent coordination — they're alone.
- Background autonomous loops — they drive every session themselves.

**Workflow shape.** Mainline or branch-per-feature, both work. Deck inside the repo. Autocommit is optional — many solo devs prefer to review what the agent did before committing.

**Trade-off they accept.** A small per-card overhead (two minutes to file the card, frontmatter plus a DoD checklist) in exchange for never losing context between sessions.

---

### The multi-agent coordinator

**Who.** Has multiple AI agents — local Claude sessions plus scheduled background agents on GitHub Actions or similar — converging on the same project. Wants them to not collide. This is also the maintainer's primary use case for GoC.

**What they need from GoC.**
- A claim protocol — `status: active` is the soft lock; agents check it before claiming new work.
- Decision gates — `human_gate: decision` parks a card so no agent decides on the human's behalf.
- A queue agents can drain autonomously while the human sleeps.
- An audit trail per card so they can reconstruct what an agent did and why.

**What they need that GoC doesn't fully ship yet.**
- Strong multi-branch coordination (cards moving across branches without conflict).
- Multi-human + multi-agent claim metadata. ([`design-claim-protocol-with-branch-and-author-metadata`](.game-of-cards/deck/design-claim-protocol-with-branch-and-author-metadata) covers this.)

**Workflow shape.** Mainline-primary. Agents work the queue. The human raises and lowers gates. Deck in the repo. Autocommit is mandatory — without it, parallel agents fight over the deck file.

**Trade-off they accept.** Some `main`-branch noise from card lifecycle commits, in exchange for visibility every other coordination tool fails to give them.

## Variations within the audience (configuration, not persona)

These are choices any of the three on-ramps can make independently. They don't define a different audience or use case; they shape the install and the day-to-day experience.

- **Runtime channel.** Claude Code (via plugin or pipx), [OpenClaw](https://openclaw.ai) (via ClawHub plugin), or the generic `goc` CLI from PyPI for any other agent runtime, CI, or no agent at all. The deck and the skills are the same across channels; only the integration shape differs (typed tool vs PATH binary vs shell call).
- **Deck visibility.** Checked into the repo (default — agents and reviewers see card state in git history) or gitignored (local-only — no PR-diff noise, no cross-collaborator visibility). See [`DECK_LOCATION.md`](DECK_LOCATION.md) for the four configurations and their trade-offs.
- **Single vs many agents.** A solo developer with one agent assistant and a multi-agent coordinator with three parallel sessions run the same engine. Autocommit and claim discipline scale up; nothing else changes.

## Audiences GoC doesn't serve yet

These groups have a real need that GoC's current engine, distribution, or documentation does not meet. Each links to the open card tracking the work that would change that.

### Teams deeply invested in Jira, Linear, or similar trackers

GoC overlaps with the tracker function: it stores tasks, has statuses, supports queries, holds an audit trail. If your team has internalized a tracker workflow — sprints, story points, board automation, integrations into Slack and PRs — GoC will feel like a duplicate.

Integration is on the roadmap ([`integrate-github-issues-discussions-and-pull-requests`](.game-of-cards/deck/integrate-github-issues-discussions-and-pull-requests), [`explore-saas-deck-hosting-with-optional-tracker-sync`](.game-of-cards/deck/explore-saas-deck-hosting-with-optional-tracker-sync)) but is not the current focus. If you cannot run GoC alongside your tracker (rather than replacing it), wait for those cards.

### Multi-maintainer OSS with strict commit hygiene

A library with branch-per-feature, mandatory PR review, and external-contributor reviewers wants the deck *outside* the repo so it never appears in PR diffs. Today's default keeps the deck inside the repo. The active epic [`support-external-game-of-cards-state-location`](.game-of-cards/deck/support-external-game-of-cards-state-location) is finishing the external-deck path; until it ships, multi-maintainer OSS is not served.

**Solo OSS maintainers willing to keep their deck local-only have a working recipe today.** See "The gitignored-deck recipe" in [`DECK_LOCATION.md`](DECK_LOCATION.md). That recipe does not work for multi-maintainer projects because collaborators cannot see your cards — wait for the epic above, or try GoC on an internal-only project first.

## How to read this doc

If you're working on an AI-first project, GoC is for you today. Pick the on-ramp whose value prop matches what *you* want from the tool — vibe-coders want continuity, solo developers want a DoD-enforced replacement for TODO.md, multi-agent coordinators want a claim protocol. You can use the engine identically whichever on-ramp you came in through; the on-ramps are framing aids for the reader, not switches in the tool.

If you live in one of the "doesn't serve yet" groups, the website's "not for you yet" warning is honest. The relevant cards are linked above — file an issue if your situation sharpens what the cards should cover.

The audience is the lens GoC uses to decide which features to prioritize. It is not a contract — your situation can sharpen the list, and feedback is welcome.
