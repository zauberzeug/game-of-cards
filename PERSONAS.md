# Who Game of Cards is for

This document names the audiences Game of Cards is built for, the audiences it is *not* built for yet, and the trade-offs each persona accepts.

It exists because most disagreement about GoC's positioning is downstream of unspoken persona mismatch — an OSS-library evaluator with strict commit hygiene hits invasive-install pain, but libraries are not the target persona today; an evaluator looking for a linear feature-planner finds the autonomous loop oversized; an evaluator with a non-code domain misses the to-do-engine framing.

The website features three of these personas prominently. The full list is here so evaluators can map themselves precisely.

## Personas (in priority order)

### 1. The vibe-coder

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

---

### 2. The solo developer

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

### 3. The multi-agent coordinator

**Who.** Has multiple AI agents — local Claude sessions plus scheduled background agents on GitHub Actions or similar — converging on the same codebase. Wants them to not collide. This is also the maintainer's primary use case for GoC.

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

---

### 4. The classical-development team (transitional)

**Who.** A team with branch-per-feature, mandatory PR review, and OSS-grade commit hygiene. Curious about GoC but uneasy about checking deck state into the main repo.

**What they need from GoC.**
- Deck stored *outside* the repo, or in a sibling location that doesn't trigger PR review noise.
- The CLAUDE.md / AGENTS.md merge to be opt-in, not default.
- A way to review the deck without reviewing it as part of every feature PR.

**Status today.** Partially served. The deck has moved under `.game-of-cards/deck/` (less noise than top-level `deck/`), the CLAUDE.md merge is opt-in via the kickoff flow, and [`support-external-game-of-cards-state-location`](.game-of-cards/deck/support-external-game-of-cards-state-location) is the active epic finishing the rest. If you live here, the website's "not for you yet" warning is honest — try GoC on a side project first. **Solo OSS maintainers** willing to keep their deck local-only have a working recipe today: see "The gitignored-deck recipe" in [`DECK_LOCATION.md`](DECK_LOCATION.md). Multi-maintainer OSS projects need to wait for the active epic.

**Workflow shape (when the epic ships).** External deck (sibling directory or separate repo). No CLAUDE.md merge. Skills and hooks installed via plugin, not committed.

---

### 5. The agent runtime as to-do engine (future)

**Who.** A chatbot, customer-support assistant, or domain-specific agent that needs structured task management for a *non-code* domain — sales pipelines, research workflows, multi-stage approvals.

**What they need from GoC.**
- Card lifecycle without the assumption that closure equals a code commit.
- Custom statuses and workflows beyond the current `open → active → done`.
- Decoupled from git: the deck's authority is its own files, not a git history.

**Status today.** Not yet served. The CLI presumes `git` and a code repo. [`support-custom-card-workflows-and-statuses`](.game-of-cards/deck/support-custom-card-workflows-and-statuses) is the relevant story; until it ships, agent runtimes that try to use GoC for non-code domains will fight the tool.

---

## Anti-personas — who GoC is *not* for yet

### Teams already deeply invested in Jira, Linear, or similar trackers

GoC overlaps with the tracker function: it stores tasks, has statuses, supports queries, holds an audit trail. If your team has internalized a tracker workflow — sprints, story points, board automation, integrations into Slack and PRs — GoC will feel like a duplicate.

The integration story exists ([`integrate-github-issues-discussions-and-pull-requests`](.game-of-cards/deck/integrate-github-issues-discussions-and-pull-requests), [`explore-saas-deck-hosting-with-optional-tracker-sync`](.game-of-cards/deck/explore-saas-deck-hosting-with-optional-tracker-sync)) but is not the current focus. If you can't run GoC alongside your tracker (rather than replacing it), wait for those cards.

### OSS library maintainers with strict commit hygiene

Until [`support-external-game-of-cards-state-location`](.game-of-cards/deck/support-external-game-of-cards-state-location) ships fully, the deck lives inside the repo and shows up in every PR diff. For libraries where every commit is reviewed by external contributors, that's noise you don't want. **Solo OSS maintainers** can adopt the gitignored-deck recipe in [`DECK_LOCATION.md`](DECK_LOCATION.md) — local-only task state, no PR noise. **Multi-maintainer OSS projects** are not served by that recipe (collaborators don't see your cards); try GoC on internal services first, or wait for the external-deck path.

### Anyone wanting a feature planner without an autonomous loop

The agent-pull loop and the gate model are core to the methodology. If you want a static planning doc with no agent participation, GoC is heavier than you need — a markdown checklist or a Notion page is fine.

---

## How to choose

If your situation matches multiple personas, pick the one closest to **how the work is delivered**, not how the work is described.

- "Solo dev with one agent assistant" → solo developer.
- "Solo dev driving three parallel sessions" → multi-agent coordinator.
- "Vibe-coder building a SaaS but committed to clean releases" → vibe-coder for daily flow, classical-dev considerations only at release time. (The "transitional" caveats apply.)
- "Multi-agent setup but the domain is non-code" → today, neither persona quite fits. File an issue describing your case.

The personas are the lens GoC uses to decide which features to prioritize. They are not a contract — your situation can sharpen the list, and feedback is welcome.
