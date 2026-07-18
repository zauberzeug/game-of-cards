---
name: advance-card
description: Mutate a card's status (everything except done — that is finish-card's job), record relationship edges, or set the goc wait impediment overlay. AUTO-INVOKE on "I'll start on X", "mark this disproved", "supersede with Z", "make this depend on Y". If the catalog location path is unreadable, fetch the body via the goc tool verb "skill", args ["advance-card"].
---

## When to invoke

Invoke when the user says "I'll start on X", "I'm working on", "mark this disproved", "supersede with Z", "this is part of X", "make this depend on Y", "these should be linked", "should this be an edge or a tag?", "remove this dependency", "unlink these", or describes any non-`done` status change or relationship-modeling intent. For "this is blocked by Y" / "unblock", set or clear the impediment overlay with `goc wait` (Step 6) instead of flipping status. Status transitions and relationship edges are documented agreements (Kanban explicit policies, Anderson).

# Advance a card

Every status transition is a documented agreement, not a silent flag
flip — the reason lives on disk: in the body for terminal
transitions, in the commit message for mid-flight ones. Mutate a
card's status — everything except `done`, which is
the `finish-card` skill's DoD-gated contract. Read the card first to
confirm the transition is legal, then run the matching CLI.

**Edge cases live in `reference.md`** — a sibling file in this
skill's directory. Read the named section only when the situation
actually applies:

| Situation | `reference.md` section |
|---|---|
| Flipping to disproved / superseded (required body work) | Terminal transitions |
| "Should this be an edge or a tag?" / coordinating cards | Edge vs tag |
| A recorded `advances` edge turns out false | Retraction |
| Worker assignment and queue filtering | Worker field |
| A legacy `status: blocked` card | Deprecated blocked status |
| Why transitions are explicit policies | Rationale |

Optional argument — `<title> <new-status> [--by <other-title>]`.

## Step 1 — read the card

Run `goc show <title>` yourself with the real title bound. Confirm:

- Current status matches the transition (e.g. `open → active`
  requires current `open`).
- The `human_gate` fits the move. Flipping a `session`-gated card to
  `active` autonomously is a stop — that needs the human in the loop.
- For `disproved` / `superseded`, the body documents the rebuttal /
  replacement BEFORE you flip (`reference.md` § Terminal
  transitions).

`status`, `human_gate`, and the impediment overlay (`waiting_on` +
`waiting_until`) are orthogonal axes — a card may be `active` AND
carry `waiting_on: external` (see the `card-schema` skill "Three-axis
stuck model"). The legacy `status: blocked` is deprecated; set the
overlay (Step 6) or rely on derived readiness instead
(`reference.md` § Deprecated blocked status).

## Step 2 — match the transition to the CLI

| transition | CLI | notes |
|---|---|---|
| `open → active` | `goc status <title> active` | "claiming" the card; also clears `draft: true` |
| `active → open` | `goc status <title> open` | release the claim (re-queue) when stepping away mid-flight without disproving the work |
| `* → open` | `goc status <title> open` | re-queue (rare) |
| `* → disproved` | `goc status <title> disproved` | populate rebuttal first; CLI stamps `closed_at` |
| `* → superseded` | `goc status <title> superseded --by <successor>` | sets the typed `superseded_by` / `supersedes` link bidirectionally; CLI stamps `closed_at` |

- To release an authored draft to the queue *without* claiming it:
  `goc publish <title>`. A draft cannot be moved to `superseded` /
  `disproved` — a title-only scaffold has no authored scope to judge
  (see the `card-schema` skill "Draft").
- Parking on an external wait is the overlay's job (Step 6), never a
  status flip; a human-judgement wait raises `human_gate` instead.
- An `advanced_by` prereq that is still open needs NO status change —
  derived dependency-readiness shows it and self-clears when the
  prereq closes.

## Step 3 — populate the two writing surfaces

Each transition routes writing to the README dashboard (rewrite in
place) and/or the `log.md` journal (append):

| Transition | README dashboard | `log.md` journal |
|---|---|---|
| `open → active` | no change required | optional; the claim commit usually suffices |
| set / clear `waiting_on` | update the affected section to reflect the wait / its resolution | append: what the wait is for and the expected return signal / what changed |
| `* → open` (re-queue) | rewrite sections no longer accurate | append: why re-queued |
| `* → disproved` | rewrite body to document the rebuttal | append: when disproved, by what evidence |
| `* → superseded` | leave body as the historical record | append: successor link + one-line why |

Rule of thumb: state-of-the-world updates rewrite the README;
transition narrative, decisions, and timestamps append to `log.md`
(see the `card-schema` skill "What goes where"). The required body
content for `disproved` (hypothesis / verdict / source of error) and
`superseded` (typed link, journal rationale, no README rewrite) is
specified in `reference.md` § Terminal transitions — read it before
your first terminal flip.

## Step 4 — run the transition

```bash
# Open → active (claiming):
goc status <title> active

# Add / remove a value-flow edge:
goc advance <title> --by <other>
goc unadvance <title> --by <other>

# Disproved / superseded:
goc status <title> disproved
goc status <title> superseded --by <successor-title>
```

The CLI prints `<title>: <prior> → <new>` on success and follows the
repo's `.game-of-cards/config.yaml` `workflow.auto_commit` policy.

## Step 5 — claim is its own commit

Status flips and edge mutations commit immediately, separately from
the work commit, so a sibling branch pulling sees `status: active`
before it races on the same YAML. `--no-commit` skips once;
`--commit` forces a state-only commit when the repo config disables
auto-commit. If the commit is skipped (no repo, mid-merge, no diff),
the CLI prints a note — the on-disk state still mutated.

## Step 6 — set or clear an impediment overlay (`goc wait`)

For exogenous waits the dependency graph cannot see: `external`
(vendor / third party), `resource` (person or skill unavailable),
`deferred` (calendar-postponed).

```bash
goc wait <title> --reason external --until 2026-06-15
goc wait <title> --until 2026-06-15    # bare --until implies deferred
goc wait <title> --reason resource     # open-ended wait
goc wait <title> --clear
```

A future `waiting_until` (or a reason with no date) hides the card
from `--ready` / next-card / pull-card and re-enters it automatically
when the date passes; an elapsed date is surfaced by `goc validate`
as `WAITING_OVERDUE`. The overlay is orthogonal to `status`.

## Edge vs tag (short form)

1. **Same value chain** — closing the source delivers a piece of the
   target's value → `advances` edge: `goc advance <title> --by
   <other>` (maintains both sides atomically; half-edges are
   validator errors; cycles forbidden).
2. **Same theme, no closure dependency** — a future filter would want
   them grouped → shared **tag**, no edge.
3. **One card coordinates many** — aggregation epic (closes when its
   children close) → `child.advances: [epic]`; governing cluster
   (closes when *decided*) → shared tag, NO edge; never
   `epic.advances: [children]` (`BACKWARDS_EPIC_EDGE`). The tell: a
   coordinator that closes on its own deliverable is a governing
   cluster.

At filing time, `goc new <child> --advances <epic> --commit` wires
both sides in one atomic commit. Full decision procedure, the
value-law reasoning, and the retraction contract: `reference.md`
§ Edge vs tag and § Retraction.

## Worker field

`goc status <title> active` auto-populates `worker` with the current
identity at claim time. Free-form: flat string (`worker: rodja`) or
mapping (`worker: {who: rodja, where: feature/foo}`). Filter queue
views with `goc --worker <X>` or the `GOC_WORKER` env var. Details:
`reference.md` § Worker field.

## Cross-references

- `reference.md` (this skill's directory) — edge cases routed in the
  table above.
- the `finish-card` skill — `done` transitions (DoD-gated).
- the `card-schema` skill — transition semantics, edge invariants,
  `human_gate` rules.
- the `create-card` skill — when a supersession needs a new card to
  point at.

## Sibling files on this host

This skill ships `reference.md` alongside its body. If a direct file read fails (sandboxed sessions cannot see the plugin install path), fetch the file through the goc tool: `{verb: "skill", args: ["advance-card", "<file>"]}`.
