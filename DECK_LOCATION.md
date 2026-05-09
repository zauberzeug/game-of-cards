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

## The gitignored-deck recipe (solo OSS maintainers)

A simpler path than sibling-repo or submodule for OSS maintainers who want their commit history clean: keep the deck inside the repo, but `.gitignore` it. The recorded decision on [`support-external-game-of-cards-state-location`](.game-of-cards/deck/support-external-game-of-cards-state-location) explicitly allows this — the deck is checked-in by default, gitignore is opt-in.

**This recipe serves the solo OSS maintainer.** It does *not* serve OSS projects with multiple maintainers — see "What stops working" below and skip ahead to "When the recipe is wrong for you".

### The recipe

1. Add `.game-of-cards/` to your repo's `.gitignore` (do this *before* `goc install`, so the install's first commit doesn't accidentally track the deck):

   ```gitignore
   # Personal task state — local-only, see https://github.com/zauberzeug/game-of-cards
   .game-of-cards/
   ```

2. Run `goc install` as usual. The CLI does not touch `.gitignore` and does not check whether the deck path is ignored at install time — it just writes the files. Because the path is ignored, git won't track them.

3. That's it. There is no separate config flag. `goc` detects on every command whether the deck is git-tracked (via `git check-ignore`) and adapts automatically.

### What `goc install` does when the deck is gitignored

- Writes `.game-of-cards/config.yaml` and creates `.game-of-cards/deck/` exactly as it would otherwise.
- Writes the `<!-- BEGIN GOC -->` block into `AGENTS.md` (and `CLAUDE.md` if you opt in). These files *are* tracked — that's intentional, because the marker is the canonical signal to agent runtimes that GoC is in use, even when the deck itself is local.
- Does not modify `.gitignore`. You added the line in step 1; the install respects it implicitly by writing files git already ignores.

### What stops working

- **Collaborator visibility.** Other contributors cloning the repo see no cards. They cannot review what work you have queued, claimed, or closed. They cannot pick up a card you started.
- **Cross-machine sync.** Switching from your laptop to a CI runner, a workstation, or a fresh clone gives you an empty deck. There is no automatic sync — `git push` skips ignored files.
- **CI-scheduled `pull-card`.** GitHub Actions / scheduled runners that clone the repo afresh have no deck to operate on. Background autonomous loops cannot run from CI.
- **Autocommit.** `goc` detects the deck is not git-tracked and silently disables autocommit (`auto_commit_enabled()` returns `False` whenever `_deck_is_git_tracked()` is false). Status flips, claims, and closures still happen — they just don't generate commits. You don't need to set `workflow.auto_commit: false` yourself.
- **`closure_on_integration` enforcement.** The opt-in "card cannot close until HEAD is on `origin/main`" check skips when the deck is not git-tracked. There's nothing to enforce against.

### What still works

- **Solo task state.** Cards, DoD enforcement, status flips, and the `goc done` closure check all work locally. The CLI's per-card semantics are unchanged.
- **Cross-session memory on the same machine.** The agent re-reads the deck on every session, so picking up where you left off tomorrow works exactly as in the same-repo default.
- **The local `goc` queue and Definition-of-Done enforcement.** `goc` (open queue), `goc --board`, `goc validate`, `goc done <title>` — all unchanged.
- **The `<!-- BEGIN GOC -->` marker in `AGENTS.md`.** Agent plugins still discover GoC is in use. Skill availability is independent of whether the deck itself is tracked.

### When the recipe is wrong for you

If any of the following apply, the gitignored-deck path will silently bite:

- **Multiple maintainers on the OSS project.** Your collaborators cannot see or contribute to the deck. Wait for [`support-external-game-of-cards-state-location`](.game-of-cards/deck/support-external-game-of-cards-state-location) to ship a real external-state path, or for [`explore-saas-deck-hosting-with-optional-tracker-sync`](.game-of-cards/deck/explore-saas-deck-hosting-with-optional-tracker-sync) to land hosted-deck support.
- **You run scheduled background agents in CI.** A fresh CI clone has no deck. The autonomous loop cannot operate against state that isn't there.
- **You work from multiple machines.** There is no sync mechanism. The two decks diverge silently.

The recipe is honest about being local-only. It is the right answer when you are one person, on one machine, who happens to maintain an OSS library and does not want to publish your task list to every contributor reviewing your PRs.

### Why this is documented but not the default

Making `.gitignore` the default would reverse the multi-agent coordinator's primary use case (deck visible across machines and CI runners), which is the persona GoC is most validated for today. The decision to keep checked-in as the default and gitignore as opt-in lives on [`support-external-game-of-cards-state-location`](.game-of-cards/deck/support-external-game-of-cards-state-location); this section is the recipe for picking the opt-in.

## Where to read more

- [`PERSONAS.md`](PERSONAS.md) — who GoC is for; classical-development team (§4) is the persona most affected by this decision.
- [`support-worktrees-and-multi-agent-deck-sync`](.game-of-cards/deck/support-worktrees-and-multi-agent-deck-sync) — the parent epic that frames this card.
- [`design-claim-protocol-with-branch-and-author-metadata`](.game-of-cards/deck/design-claim-protocol-with-branch-and-author-metadata) — the sibling card that designs the protocol for the same-repo path GoC actually ships.
- [`explore-saas-deck-hosting-with-optional-tracker-sync`](.game-of-cards/deck/explore-saas-deck-hosting-with-optional-tracker-sync) — the SaaS path, scoped as its own epic.
- [`evaluate-deck-as-separate-repo-or-submodule`](.game-of-cards/deck/evaluate-deck-as-separate-repo-or-submodule) — the card whose decision this doc records.
