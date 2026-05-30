## 2026-05-29T16:21:00Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Three credible options:

### Option A — auto-commit only the parent-edge mutations when `--advances` / `--advanced-by` is used

Leave the new card itself untracked (preserving today's behavior of
"scaffold for editing"), but auto-commit the parent README updates
under a `deck: <child> advances <parent>` message — mirroring the
existing `advance` / `unadvance` commit messages.

- Pros: minimal behavior change. The user's typical "scaffold, fill
  in body, commit" loop is untouched. Half-edge gap closed.
- Cons: asymmetric — `goc new` commits something only sometimes.
  Two commits in the agent flow when the agent later commits the
  new card itself (one autocommit for the parent edge, one explicit
  commit for the child body).

### Option B — auto-commit everything: the new card directory AND any parent-edge mutations, in one commit

Mirror `goc advance` exactly. After `goc new child --advances parent`,
the worktree is clean.

- Pros: symmetric with the four sibling edge-mutating verbs.
  Single commit per `goc new` invocation. The agent's job
  simplifies to "fill in the README, then `goc done` or
  `goc advance ...`-driven follow-up".
- Cons: significant default-behavior change. Today users expect
  `goc new` to scaffold a card they then fill in and commit
  themselves; auto-committing an empty-body card creates noise in
  `git log` and a "fix up the placeholder DoD" follow-up commit
  per card.

### Option C — add `--commit` / `--no-commit` flags with default `no-commit`, leave today's behavior unchanged

Match the flag surface of the four sibling verbs but keep the
current "user commits explicitly" default. Agents opt in via
`goc new --commit ...`; `Skill(create-card)` Step 4 recommends
`--commit` for wired filings.

- Pros: zero default-behavior surprise. Maximum control. Cheapest
  to land.
- Cons: still wrong-by-default for the common case (an agent
  forgets the flag and ships a half-edge anyway). Skill-body
  guidance becomes the only enforcement, which AGENTS.md's
  predecessor history shows is not sufficient — guidance drift is
  why this family of bugs recurs.

The implementer should pick one; the DoD already encodes the
neutral set of asserts (status clean for the parent path; new card
directory tracked OR explicitly untracked, matching the chosen
option).


## 2026-05-30T13:56:48Z: decision recorded

Option C: add --commit/--no-commit flags to goc new (matching the sibling edge verbs' flag surface), default no-commit so today's scaffold-then-fill-in behavior is unchanged; create-card Step 4 recommends --commit for wired filings — preserves the zero-default-surprise scaffold workflow that is the point of goc new while giving agents an explicit opt-in to close the half-edge; the maintainer accepts that skill-body guidance is the enforcement surface for the common case. Gate decision → none.
