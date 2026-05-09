# Where the deck lives

Game of Cards stores its state in a directory of markdown files (the "deck"). That directory has to live *somewhere* — and there are four places it could plausibly live, each with different trade-offs.

This doc names the four configurations, evaluates each on the dimensions that matter, and records which one GoC actually ships.

**Bottom line.** Same-repo (deck on the mainline of the code repo) is the only configuration GoC ships as supported. Sibling-repo, submodule, and hosted SaaS are documented here as **possible but unsupported** — wire them up yourself if your situation demands it, but the CLI, plugins, and skills are tuned for the same-repo path.

## The four configurations

| Configuration | Where the deck lives | Who maintains the link |
|---|---|---|
| **Same repo** *(shipped)* | `<code-repo>/.game-of-cards/deck/` | Implicit — `goc` reads `Path.cwd() / ".game-of-cards" / "deck"` |
| Sibling repo | `<sibling-clone>/.game-of-cards/deck/` next to `<code-clone>/` | User runs two clones; agents need a path resolver |
| Git submodule | `<code-repo>/.game-of-cards/` is a submodule pointed at a deck repo | Git submodule machinery |
| Hosted SaaS | A server holds the canonical deck; clients sync via HTTP | The service |

## Evaluation

### Setup cost

| Configuration | Cost |
|---|---|
| Same repo | None. `goc install` writes the deck into the working tree. |
| Sibling repo | Two clones to coordinate. Need a convention for where the sibling lives, plus a way for `goc` to find it (env var, config file, walk-up search). |
| Submodule | One-time `git submodule add` per code repo, plus contributor onboarding cost — every contributor has to learn the submodule update commands or the deck silently goes stale. |
| Hosted SaaS | Account creation, auth setup, and an offline story. Server-side cost on the maintainer if self-hosted; subscription if not. |

### OSS commit-history cleanliness

| Configuration | Effect on the code repo's commit log |
|---|---|
| Same repo | Card lifecycle commits (`open → active`, `active → done`) appear in `git log` next to code commits. With autocommit on (the default for multi-agent setups), this can be 3–10 deck commits per code commit. External contributors reading the history see the noise. |
| Sibling repo | Code repo's history stays pure. Deck history lives in its own repo. |
| Submodule | Code repo only sees submodule-pointer bumps, not individual card changes. Cleaner than same-repo, noisier than sibling. |
| Hosted SaaS | Code repo is untouched. Deck history is whatever the service exposes. |

### Claim and sync semantics

The single invariant that makes claims meaningful is: **`.game-of-cards/` must be in sync across all participants.** A claim that one agent makes has to be visible to every other agent before they decide what to pull. The four configurations achieve this differently.

| Configuration | Sync mechanism | Failure mode |
|---|---|---|
| Same repo | Git on main. `goc status active` autocommits and pushes; other agents pull before claiming. | A worker that forgets to pull races a stale view of the queue. Last-writer-wins on the file resolves it (per the recorded decision in `design-claim-protocol-with-branch-and-author-metadata`). |
| Sibling repo | Same — git on the sibling's main. Plus the path-resolver layer to find the sibling. | Same as same-repo, plus the new failure mode where the sibling clone is missing or out of date. |
| Submodule | Submodule pointer bumps in the code repo + git on the deck repo. | Two-step staleness: deck repo can be ahead of submodule pointer, or submodule pointer can be ahead of working-tree submodule contents. Both confuse `goc`. |
| Hosted SaaS | Server is the source of truth. Clients write through. | Network partition or auth expiry blocks all claim activity, not just one agent's. Offline degrades to read-only or breaks entirely. |

### Offline behavior

| Configuration | Offline |
|---|---|
| Same repo | Fully functional. Git push deferred; `goc` keeps working. |
| Sibling repo | Fully functional, same as same-repo. |
| Submodule | Fully functional. |
| Hosted SaaS | Degraded or broken depending on the service's offline story. |

## Why GoC ships only the same-repo path

Each alternative buys cleaner commit history at the cost of substantial path-resolution and discovery code in `goc`, plus a documentation surface for users to learn. That cost is justified only if the persona it serves is validated and non-trivial in count.

### Sibling repo

**Persona served.** The classical-development team (PERSONAS.md §4) — branch-per-feature, mandatory PR review, OSS-grade commit hygiene. They want the deck out of the code repo's PR diffs.

**Why deferred, not abandoned.** The active epic [`support-external-game-of-cards-state-location`](.game-of-cards/deck/support-external-game-of-cards-state-location) already explores deck-path indirection (its recorded decision: `.game-of-cards/` is checked-in by default but users may gitignore it). That epic should mature first; sibling-repo discovery is downstream of it. Reconsider when an actual classical-dev team adopts GoC and asks for it — today, the persona is "transitional" precisely because it is not yet validated by adoption.

### Git submodule

**Persona served.** Same as sibling-repo — classical-development teams who want a versioned link from a code commit to the deck state at that commit.

**Why deferred.** Submodules are a UX friction every developer who's used them complains about. Shipping a submodule-based default would make the first-run experience worse for the personas GoC actually targets (vibe-coder, solo developer, multi-agent coordinator) to serve a persona that is not yet validated. The cost-benefit doesn't clear.

### Hosted SaaS

**Persona served.** Two: (a) teams already invested in Jira/Linear (PERSONAS.md anti-personas) who want bidirectional tracker sync — naturally a service feature, not a CLI feature; (b) the multi-agent coordinator persona at scale, where "shared mutable state with strong consistency" is easier to provide as a service than as a git protocol.

**Why deferred.** This is its own epic — see [`explore-saas-deck-hosting-with-optional-tracker-sync`](.game-of-cards/deck/explore-saas-deck-hosting-with-optional-tracker-sync). It is research and business-modeling, not a configuration of the same CLI. The hosted-deck path is essentially "deck-as-separate-storage" with the storage outsourced; a decision to pursue it is a product decision, not a packaging decision.

## What "possible but unsupported" actually means

If your situation demands one of the rejected configurations:

- **Sibling repo.** Set `.game-of-cards/` as a symlink or use a wrapper that `cd`s into the sibling clone before invoking `goc`. There's no env var or config-file resolver today. Multi-agent claim safety is not guaranteed to behave correctly across a sibling — you're on your own to validate it for your workflow.
- **Submodule.** Add `.game-of-cards/` as a submodule. `goc` will read from it as if it were a normal directory. You are responsible for the `git submodule update` discipline.
- **Hosted SaaS.** Doesn't exist. If it does ship one day, it will be through the SaaS card linked above.

If you wire one of these up and it works for you, file a card describing the setup. Adoption signal is what would move one of these from "unsupported" to "shipped".

## Why not just gitignore the deck

A simpler path for OSS maintainers: keep the deck inside the repo, but add `.game-of-cards/` to `.gitignore`. The recorded decision on [`support-external-game-of-cards-state-location`](.game-of-cards/deck/support-external-game-of-cards-state-location) explicitly allows this.

The trade-off: a gitignored deck is purely local. Collaborators don't see your cards. Multi-agent setups that span machines stop working. For a solo OSS maintainer keeping personal task state, this is fine; for an OSS project with multiple maintainers, it is not.

This path is partially documented today and would benefit from a more concrete recipe — see the follow-up card [`document-gitignored-deck-workflow-for-oss-maintainers`](.game-of-cards/deck/document-gitignored-deck-workflow-for-oss-maintainers).

## Where to read more

- [`PERSONAS.md`](PERSONAS.md) — who GoC is for; classical-development team (§4) is the persona most affected by this decision.
- [`support-worktrees-and-multi-agent-deck-sync`](.game-of-cards/deck/support-worktrees-and-multi-agent-deck-sync) — the parent epic that frames this card.
- [`design-claim-protocol-with-branch-and-author-metadata`](.game-of-cards/deck/design-claim-protocol-with-branch-and-author-metadata) — the sibling card that designs the protocol for the same-repo path GoC actually ships.
- [`explore-saas-deck-hosting-with-optional-tracker-sync`](.game-of-cards/deck/explore-saas-deck-hosting-with-optional-tracker-sync) — the SaaS path, scoped as its own epic.
- [`evaluate-deck-as-separate-repo-or-submodule`](.game-of-cards/deck/evaluate-deck-as-separate-repo-or-submodule) — the card whose decision this doc records.
