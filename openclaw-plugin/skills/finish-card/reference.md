# finish-card reference — edge cases and rationale

Companion to `SKILL.md`. Each section below is routed from the core
skill; read the one that matches the situation at hand.

## Rationale

The DoD is the agreement, set when the card was filed, that the work
is actually complete — not "the test passed once," but every named
criterion satisfied. An LLM agent reading the card at 3 AM in a /loop
iteration must not be able to mark the work done by accident; the
contract is enforced by `goc done`, which counts unchecked boxes and
refuses to flip the status if any remain. The human-typed checkbox
list is the audit trail.

Why the audit (Step 2) exists: a fix that turns its tests green but
encodes a default the project's documented principles disagree with,
silently disables a primitive to mask a side-effect, or drifts a
documented contract is debt-accumulating even when "green". The audit
forces the closer to articulate *which* project principle the closure
aligns with — or to honestly note that no principle is touched
(mechanical fixes: cache invalidation, bounds checks, field-symmetric
serialization).

Why attest (Step 5) exists: implicit DoD layers — project-wide rules
("tests pass, ruff green, audit pass") and GoC-wide rules ("schema
valid, advanced_by closed, log.md has closure entry, DoD 100%") — are
the *meta*-contract applying to every closure regardless of what the
card does. Without a recorded verification block, a 6-month-old reader
sees the layer-1 ticked boxes but no record of whether layer-2 or
layer-3 was actually verified. `goc attest` makes that record.

## Attest details and skip policy

`goc attest <title>` reads `.game-of-cards/config.yaml` and runs each
layer-2 + layer-3 check:

- **Automated checks** run as subprocesses (`pytest`, `ruff check`,
  `ruff format --check`, `goc validate`). Non-zero exit fails.
- **Derived checks** compute from card state (DoD %, advanced_by
  closure, log.md grep for the closure section).
- **Manual checks** (`audit`, `no-debug-code`) prompt the closer
  interactively for pass/fail + a one-line rationale, recorded
  verbatim in the log block.
- **Agent checks** (`doc-consistency-checker`) prompt the closer to
  confirm the subagent was run separately and what it reported.
  Accept `n/a` for pure code/no-doc closures.
- On any failure: exits non-zero, closure blocks. Fix the failing
  check, re-run `attest`. Per the 2026-05-03 decision, no waivers.

To skip a single check (rare — e.g. a genuinely flaky automated
check): `--skip <name>`. The skip is recorded as
`[~] SKIPPED — <description>` in the block. Do not skip casually.

## Retraction vs waiting (`advanced-by-closed` failures)

When this check fails, two honest resolutions exist (see
`Skill(card-schema)` "Value-flow axis"):

1. **Wait** for the named upstream contributors to close, then re-run
   `attest`.
2. **Retract a false edge** with
   `goc unadvance <closing-title> --by <upstream-title>`. The
   value-chain identity ("X advances Y" ⇔ Y's value chain includes X)
   says a true edge cannot coexist with a closeable Y; so if Y is
   genuinely closeable, the edge was modeling the wrong relationship
   and the right action is to remove it, not skip the check.

`--skip advanced-by-closed` should be the last resort, never the
first — it leaves a dishonest edge in the deck (the closure log shows
SKIPPED, the graph still claims X is in Y's value chain, and the next
reader cannot tell which it was).

## Bundled closures

One fix resolving multiple cards:

```bash
goc done --bundle <title-A> <title-B> [<title-C> ...]
```

`--bundle` enforces the unchecked-DoD refusal on every member before
mutating disk (any failure aborts the bundle), then writes one shared
`## Closure verification (TIMESTAMP) — bundled` block plus a
`## TIMESTAMP — Closure (bundled)` entry with `Bundled with:`
cross-references into every member's `log.md`, and flips each card to
`done` with the same `closed_at`. Use this in place of running
`goc attest` + `goc done` once per card when the closures genuinely
share an attestation. For mixed-attestation closures (different
verification per card), keep the per-card flow.

## Parallel-agent commit safety

On shared local `main`, other agents may be using the same worktree
and the same Git index. Before staging, run
`git diff --cached --name-only`; if it lists files you did not stage,
another agent is between `git add` and `git commit` — wait with a
short backoff or surface the collision; do not bundle or unstage
their files.

When the index is free, stage only the explicit paths owned by this
closure (`git add <path>...`, verify with `git diff --cached --stat`,
then `git commit -- <path>...`). The `git commit -- <path>...`
pathspec is intentional: it restricts the commit to this closure's
files even if the index becomes contaminated. Never use `git add .`,
`git add -A`, directory-wide adds, `git stash`, or destructive cleanup
(`git restore`, `git checkout --`, `git reset --hard`, `git clean`) as
a commit-isolation technique. For non-trivial commits on a busy shared
`main`, prefer a temporary worktree for commit prep.

## Commit conventions

- **Subject:** `fix(<scope>): <one-line subject> — closes <title>`.
  Examples:
  - `fix(api/csv-export): stream rows without 10000-row cap — closes csv-export-button-truncates-rows-over-10000`
  - `fix(auth/cookie): bump cookie max-age to 24h — closes auth-cookie-expires-too-soon`
- For bundled closures, append additional slugs:
  `fix(<scope>): <subject> — closes <title-A>, <title-B>, <title-C>`.
- **Body:** explain WHY (which user-visible problem this resolves;
  what measurement bias it removed). Include verification numbers and
  the closure log. Reference the `deck/<title>/` archive.
- **Trailer:** follow the consuming repo's authorship convention, if
  one exists.

If the commit workflow fails *because of this work* (newly broken
test, lint error you introduced, deck-validate rejection), fix and
re-run it. If it fails on a pre-existing issue, surface that in chat
and stop — that's a separate concern.

## After closure — closure is not frozenness

A closed card is the entry point a cold reader navigates to when
asking "what was decided about X." If new evidence surfaces after the
card closes — a bug found later, an assumption invalidated, a
follow-up that reframes the original — file a new card for the new
work AND amend the closed card to point readers forward. Strict
immutability orphans the original anchor: future readers walk away
with stale context, and the kanban accumulates orphan threads.

Two-file routing still applies (see `Skill(card-schema)` "What goes
where"):

- **`log.md` (append a dated entry).** The post-close amendment IS a
  valid append — the journal is append-only, and a new entry at the
  bottom does not rewrite history. Format:

  ```
  ## YYYY-MM-DDTHH:MM:SSZ — Post-close amendment

  Superseded / extended by [`<new-card-title>`](../<new-card-title>/)
  — <one-line reason>.
  ```

- **`README.md` (optional pointer at the top).** If the new evidence
  materially changes how a reader should interpret the closed card,
  add a single one-line `> Later evidence: see …` pointer near the
  top of the body so cold readers see it before the closure
  narrative. Do NOT rewrite the closure entry itself; treat the
  amendment as additive.

Update only the **original** card — do not retroactively edit other
closed cards' bodies to reference the new one. The forward pointer
from the new card's body, plus the back-reference appended here, is
the full bidirectional link.
