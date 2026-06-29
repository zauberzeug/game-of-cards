---
name: advance-card
description: "Mutate a card's status (open / active / disproved / superseded — everything except `done`), record relationship edges between cards (`goc advance` / `goc unadvance`), or set the impediment overlay (`goc wait`). AUTO-INVOKE when user says \"I'll start on X\", \"I'm working on\", \"mark this disproved\", \"supersede with Z\", \"this is part of X\", \"make this depend on Y\", \"these should be linked\", \"should this be an edge or a tag?\", \"remove this dependency\", \"unlink these\", or describes any non-done status change or relationship-modeling intent. For \"this is blocked by Y\" / \"unblock\", set or clear the impediment overlay with `goc wait` (Step 6) instead of flipping status. Status transitions and relationship edges are documented agreements (Kanban explicit policies, Anderson)."
---

## Codex GoC Command

When this skill says `goc ...`, resolve the executable before running the
command:

- In the `game-of-cards` source checkout, use `uv run goc ...`.
- If `goc` is already on `PATH`, use `goc ...`.
- If this skill is loaded from the Game of Cards Codex plugin, use the
  bundled helper at `<plugin-root>/skills/_goc-bootstrap.sh ...`; the plugin
  root is the parent directory that contains both `skills/` and `bin/`.
- If the plugin root is not obvious from the loaded skill path, locate the
  helper with:

```bash
GOC_BOOTSTRAP=$(find "$HOME/.codex/plugins/cache" -path '*/game-of-cards/*/skills/_goc-bootstrap.sh' -type f -perm -111 2>/dev/null | sort | tail -n 1)
test -n "$GOC_BOOTSTRAP" || { echo "GoC Codex plugin bootstrap not found" >&2; exit 127; }
"$GOC_BOOTSTRAP" --help
```

Use that helper path in place of bare `goc` for the rest of the skill. Do not
edit deck files directly just because `goc` is not on `PATH`.


## Preflight

If any `!` block below shows `goc: command not found`, `Permission for this action has been denied`, or `no such file or directory: .game-of-cards/deck/`, **stop and invoke `Skill(kickoff)` first**. Kickoff detects which setup step is missing (CLI not installed, Bash allowance not granted, project state not scaffolded) and walks the user through it. Re-invoke this skill only after kickoff completes.

# Advance a card

Kanban's **explicit policies** (Anderson): every status transition is
a documented agreement, not a silent flag flip. The lane a card sits
in says what's true about it; the move between lanes carries a
reason — recorded in the body for terminal transitions, in the commit
message for mid-flight ones. A swarm of /loop iterations cannot
audit-trail conversational context, so the rule is: the policy lives
on disk.

Mutate a card's status — everything except `done`, which is
`Skill(finish-card)`'s DoD-gated contract. Read the card first to
confirm the transition is legal under those policies, then run the
matching CLI.

User argument: $ARGUMENTS — `<title> <new-status> [--by <other-title>]`.

## Step 1 — read the card

Run `goc show <title>` yourself with the real title bound. Confirm:
- Current status matches the transition you're about to make
  (e.g. `open → active` requires current `open`).
- The `human_gate` is appropriate for the new state. If you're
  flipping a `session`-gated card to `active` autonomously, stop —
  that's a research-impacting move and needs the human in the
  loop.
- For `disproved` / `superseded`, the body documents the rebuttal /
  replacement before you flip.

`status` and `human_gate` are orthogonal — see `Skill(card-schema)`
"human_gate scale". A `decision` or `session` gate parks a card for
human input; it does NOT depend on a separate "blocked" status.

The **impediment overlay** (`waiting_on` + `waiting_until`) is the
stored signal for exogenous waits the dependency graph cannot derive
(vendor delivery, a specific person, a calendar-based defer). It
composes with `status`: a card may be `active` AND carry
`waiting_on`. Set or clear via `goc wait` (see "Step 6").

> Deprecated: the legacy `status: blocked` value. Three-axis model
> (see `Skill(card-schema)` "Three-axis 'stuck' model") splits the
> old `blocked` meaning into derived dependency-readiness (an
> `advanced_by` prereq still open — self-clears when the prereq
> closes) and the stored `waiting_on` overlay (exogenous wait).
> Authors should set the overlay (`goc wait …`) or rely on derived
> readiness instead of flipping status to `blocked`. The enum value
> still parses for backwards compatibility but is being removed in a
> follow-up release.

## Step 2 — match the transition to the CLI

| transition | CLI | notes |
|---|---|---|
| `open → active` | `goc status <title> active` | "claiming" the card |
| `active → open` | `goc status <title> open` | release the claim (re-queue) when stepping away mid-flight without disproving the work |
| `* → open` | `goc status <title> open` | re-queue (rare) |
| `* → disproved` | `goc status <title> disproved` | populate rebuttal first; CLI stamps `closed_at` |
| `* → superseded` | `goc status <title> superseded --by <successor>` | sets typed `superseded_by` / `supersedes` link bidirectionally; log replacement rationale in old card's `log.md`; CLI stamps `closed_at` |

`goc advance` and `goc unadvance` maintain the bidirectional
value-flow edge atomically (validator-enforced — if `A.advances`
contains `B`, `B.advanced_by` MUST contain `A`). An `advanced_by`
prereq that is still non-terminal is what the **derived
dependency-readiness** signal reads — it self-clears when the prereq
closes, so no status flip is needed to park the card on an upstream
sibling.

**Draft cards.** `open → active` also clears any `draft: true` flag —
claiming a card proves it is authored. To release an authored draft to the
queue *without* claiming it for work, use `goc publish <title>` (not a status
change; it only clears the flag, and refuses on an unwritten placeholder). A
draft cannot be moved to `superseded` / `disproved`: the CLI refuses, since a
title-only scaffold has no authored scope to judge as a duplicate — the
dedup/supersede race the draft state guards against. See
`Skill(card-schema)` "Draft".

**Parking a card on an external wait:** use the impediment overlay
(Step 6), not `status: blocked`. For an agent-observable wait
(upstream release, PR merge, dependency publication) the card stays
`status: open` with `waiting_on: external` and an optional
`waiting_until` date — a future autonomous run re-checks the
condition and `goc wait <title> --clear`s the overlay when the wait
resolves. For a human-judgement wait, raise `human_gate` to
`decision` / `session` and write the framing into the body; no
status flip required.

## Step 3 — populate the body for transitions

Every transition has two writing surfaces — the README dashboard
(latest state) and `log.md` (the journal of how we got here). Each
status flip routes information to the right file:

| Transition | README dashboard (rewrite in place) | `log.md` journal (append entry) |
|---|---|---|
| `open → active` | no change required (claim adds `worker` field, not body content) | optional one-line "claimed by X on DATE" entry; usually skipped — the git commit suffices |
| `set `waiting_on` overlay` | update the relevant body section to reflect the wait (e.g. "Fix" → "Waiting on upstream release of X, expected YYYY-MM-DD") | append entry: when the overlay was set, what the wait is for, expected return signal |
| `clear `waiting_on` overlay` | rewrite the body section that named the wait to reflect the new state of the world | append entry: when the wait cleared, what changed externally |
| `* → open` (re-queue) | rewrite the body sections that are no longer accurate to match the new framing | append entry: why the card was re-queued (scope reset, evidence superseded, etc.) |
| `* → disproved` | rewrite body to document the rebuttal (see below) | append entry: when disproved, by what evidence |
| `* → superseded` | leave the body as the historical record; do NOT rewrite to point at the successor | append entry naming and linking the successor card and one-line why |

Rule of thumb: **state-of-the-world updates rewrite the README
dashboard; transition narrative, decisions, and timestamps append to
`log.md`.** See `Skill(card-schema)`'s "What goes where" subsection.

The CLI stamps `closed_at` automatically for every terminal flip
(`done`, `disproved`, `superseded`); `status` names the outcome.
The body work below is what the CLI does NOT do for you.

### Disproved

Rewrite `deck/<title>/README.md` body to document the resolved state:

- The hypothesis (what was claimed).
- The verdict (FALSE — what's actually in the code).
- The source of error (which agent / partial reading triggered it).
- A one-line lesson if non-obvious.

Then append a journal entry to `log.md` recording when and how the
disproof landed, including the evidence cited. The README rewrite
gives a cold reader the verdict; the journal entry gives a forensic
reader the disproof chain.

This is mandatory. Without it, every scheduled run that spawns the
same agent set may re-propose the same false lead and waste a
verification cycle.

### Superseded

The new card's body explains what it supersedes and why. Run
`goc status <title> superseded --by <successor>` on the old card —
the `--by` flag sets the typed bidirectional `superseded_by` /
`supersedes` link on both endpoints in one atomic operation (same
contract `goc advance` provides for the advances graph).

Append an entry to the old card's `log.md` to record the replacement
*rationale*: one-line why the replacement happened (different
approach, scope split, reframing). The typed field is the
machine-navigable pointer; the journal entry is the prose-only
*why* a graph edge cannot capture. Both, for different jobs — a
cold reader (human or LLM) walks the typed link to find the
successor without parsing prose, and reads the log entry for the
rationale.

Leave the old README body as the historical dashboard; do NOT
rewrite it to point at the successor (the typed link does that
mechanically). The link to the successor stays a one-line `> Later:
[<new-title>](../<new-title>/)` pointer at the top of the body only
if a cold reader would otherwise be misled — see `Skill(card-schema)`
"Replacement axis" for the invariants and emitter conventions.

Plain `goc status <title> superseded` (without `--by`) is still
accepted for backwards compatibility, but leaves the supersession
prose-only and forces forensic readers to grep `log.md`. Prefer the
`--by` form for every new supersession.

## Step 4 — run the transition

```bash
# Open → active (claiming):
goc status <title> active

# Add a value-flow edge (other advances title):
goc advance <title> --by <other>

# Remove a value-flow edge:
goc unadvance <title> --by <other>

# Disproved / superseded:
goc status <title> disproved
goc status <title> superseded --by <successor-title>
```

The CLI prints `<title>: <prior> → <new>` on success and follows the
repo's `.game-of-cards/config.yaml` `workflow.auto_commit` policy.

## Step 5 — claim is its own commit (multi-branch coordination)

Status flips and edge mutations normally commit immediately, separately
from the work commit. Reason: when two branches both work the deck, the
soft lock (`status: active`) should be git-observable so a sibling branch
pulling sees "this card is claimed" before it races on the same YAML.

`goc status` / `advance` / `unadvance` / `decide` read
`workflow.auto_commit` from `.game-of-cards/config.yaml` (default:
`true`). Pass `--no-commit` to skip for one invocation, or `--commit`
to force a state-only commit when the repo config disables automatic
commits. The work commit, when it lands later after `Skill(finish-card)`,
contains the actual code/doc changes — NOT the status flip.

If the configured/forced auto-commit is skipped (no git repo, mid-merge /
mid-rebase, no diff), the CLI prints a one-line note. The on-disk state
still mutated; only the visibility-to-other-branches step deferred.

## Step 6 — set or clear an impediment overlay (`goc wait`)

The dependency-readiness predicate covers card-blocks-card, but cannot
see exogenous waits. Three kinds need a stored signal:

- `external` — vendor, client, hardware, a third party.
- `resource` — a specific person/skill currently unavailable.
- `deferred` — deliberately postponed (a calendar-based defer).

Set the overlay with `goc wait`:

```bash
# Wait on a vendor; expect to retry on 2026-06-15.
goc wait <title> --reason external --until 2026-06-15

# Defer-only (no reason): bare --until implies `deferred`.
goc wait <title> --until 2026-06-15

# Open-ended wait on a specific person; no expected return date.
goc wait <title> --reason resource

# Clear the overlay when the wait resolves.
goc wait <title> --clear
```

Effects:

- A future `waiting_until` (or a reason with no date) hides the card
  from `goc --ready` / `Skill(next-card)` / `Skill(pull-card)`. When
  the date passes the card re-enters the queue with no manual action.
- An elapsed `waiting_until` is surfaced by `goc validate` as
  `WAITING_OVERDUE` — the Kanban SLE escalation: the wait overran its
  expected return, re-triage or clear.
- The overlay is orthogonal to `status` — a card may be `active` AND
  carry a `waiting_on`, e.g. work in progress that is partially gated
  on an external answer.

## Modeling a relationship: edge vs tag

A reader landing here on a relationship question ("this is part of X",
"make this depend on Y", "these should be linked", "should this be an
edge or a tag?", "remove this dependency") is asking *how to express a
link*, not *how to flip a status*. This section is the decision
procedure; the canonical taxonomy and the value-flow invariants live in
`Skill(card-schema)` — link, don't re-derive.

### Decision procedure

1. **Same value chain — does the source's closure deliver a piece of the
   target's value?** → `advances` edge. The dependent inherits the
   source's priority and cannot close until the source closes (see
   `Skill(card-schema)` "Value-flow axis" for the closure semantics).
2. **Same theme, no closure-time dependency — would a future filter
   ("show me all the X cards") want them grouped?** → shared **tag**.
   No edge in either direction.
3. **One card coordinates many others** → see the three-way fork below
   before reaching for `--advances`.

### Three coordinating-card shapes (short form)

Full reasoning, the value-law derivation, and the `BACKWARDS_EPIC_EDGE`
lint live in `Skill(card-schema)` "Coordinating cards — aggregation epic
vs governing cluster". The short form, paired with the verb you reach
for:

- **Aggregation epic** — its value chain *is* its children; closes
  when they close. Encoding: `child.advances: [epic]`. Verb on the
  child (open or after creation):
  `goc advance <child> --by <epic>`.
- **Governing cluster** — a decision or standard-setting card that
  closes when *decided*, independent of the cluster's work. Encoding:
  a **shared tag**, no `advances` edge in either direction. Add the
  tag at `goc new --tag <name>` time on both the governing card and
  each instance; for an existing card, edit `tags:` in the
  frontmatter directly. To register a new project-specific tag, see
  `Skill(card-schema)` "Adding new tags".
- **Backwards aggregation** — `epic.advances: [children]`. **Never.**
  Defeats the value law (children stop inheriting the epic's value,
  so the GRPW sort cannot see the chain) and trips a spurious
  `advanced-by-closed` FAIL on every child at attest time. `goc
  validate` flags this signature as `BACKWARDS_EPIC_EDGE`.

The tell: if the coordinating card closes on its own deliverable
(typically `human_gate: decision`) rather than on its cluster's
completion, it is a governing cluster → tag, not edge.

### Retraction — `goc unadvance` is the honest fix

When an `advanced-by-closed` check fires at closure time, the gate is
reading the value-chain identity (`Skill(card-schema)` "Value-flow
axis"): a true edge cannot coexist with a closeable target. Two
honest resolutions:

1. **Wait** for the upstream contributor(s) to close.
2. **Retract** when the edge was false (the upstream was tangential,
   scope was reframed, or the relationship was authored backwards):
   `goc unadvance <closing-title> --by <upstream>`.

Retraction is graph maintenance, not a bypass. Prefer it to
`goc attest --skip advanced-by-closed`; the skip leaves a dishonest
edge in the deck. Same rule applies in the opposite direction — if
you discover a card should depend on another after filing, add the
edge with `goc advance <title> --by <other>` rather than letting the
relationship live only in prose.

### Verbs

```bash
# Record a value-flow edge (this advances other):
goc advance <title> --by <other>

# Retract a value-flow edge:
goc unadvance <title> --by <other>

# At filing time, both sides at once (--commit so the new card AND
# the epic's edge mutation land in one atomic commit):
goc new <child-title> --advances <epic-title> --commit
```

`goc advance` / `unadvance` maintain the bidirectional invariant
(`A.advances` ⇔ `B.advanced_by`) atomically — same atomicity contract
`goc status … superseded --by` provides for the replacement graph. The
validator refuses half-edges. Cycles are forbidden.

For grouping (the governing-cluster shape and other soft themes), there
is intentionally no `goc add-tag` verb on existing cards — set tags at
`goc new --tag <name>` time, or edit `tags:` in the frontmatter
directly. The unknown-tag error names the file to register a new tag
in (see `Skill(card-schema)` "Adding new tags").

## Worker field — populated at claim time

`goc status <title> active` auto-populates the card's `worker` field
with the current identity. The field is optional and free-form; it
matters when multiple humans or agents share a deck and you want a
runner-scoped queue view.

**Format:**

- Flat string for a single identifier: `worker: rodja`. Sugar for
  `{who: rodja}`.
- Mapping with branch context: `worker: {who: rodja, where: feature/foo}`.

The value is unregistered — pick a person slug, machine name, or
capability tag (`gpu-required`, `human`, `rendering-expert`). The
field persists after close as a historical record.

**Filter the queue by worker:**

- `goc --worker <X>` — limit listings to cards owned by `X`.
- Set `GOC_WORKER` env var so a runner sees only its own queue without
  typing the flag every time.

## Cross-references

- `Skill(finish-card)` — for `done` transitions (DoD-gated).
- `Skill(card-schema)` — full transition semantics, bidirectional
  edge invariants, `human_gate` rules.
- `Skill(create-card)` — when the supersession needs a new card to
  point at.
