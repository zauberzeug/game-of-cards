---
name: advance-card
description: Mutate a card's status (open / active / blocked / disproved / superseded — everything except `done`). AUTO-INVOKE when user says "I'll start on X", "I'm working on", "this is blocked by Y", "mark this disproved", "supersede with Z", "unblock", or describes any non-done status change. Status transitions are documented agreements (Kanban explicit policies, Anderson).
---

# Advance a card

Kanban's **explicit policies** (Anderson): every status transition is
a documented agreement, not a silent flag flip. The lane a card sits
in says what's true about it; the move between lanes carries a
reason — recorded in the body for terminal transitions, in the commit
message for mid-flight ones. A swarm of /loop iterations cannot
audit-trail conversational context, so the rule is: the policy lives
on disk.

Mutate a card's status — everything except `done`, which is
the `finish-card` skill's DoD-gated contract. Read the card first to
confirm the transition is legal under those policies, then run the
matching CLI.

Optional argument — `<title> <new-status> [--by <other-title>]`.

## Step 1 — read the card

`goc show <title>`

Confirm:
- Current status matches the transition you're about to make
  (e.g. `open → active` requires current `open`).
- The `human_gate` is appropriate for the new state. If you're
  flipping a `session`-gated card to `active` autonomously, stop —
  that's a research-impacting move and needs the human in the
  loop.
- For `disproved` / `superseded`, the body documents the rebuttal /
  replacement before you flip.

`status` and `human_gate` are orthogonal — see the `card-schema` skill
"human_gate scale". A card can be `blocked` with `human_gate: none`
when the blocker is an agent-observable external condition. Setting
`blocked` does NOT require raising the gate; raising the gate does
NOT require `blocked`.

## Step 2 — match the transition to the CLI

| transition | CLI | notes |
|---|---|---|
| `open → active` | `goc status <title> active` | "claiming" the card |
| `active → blocked` | `goc status <title> blocked` (+ optionally `goc advance <title> --by <other>` if a specific card is what's needed) | flip status; optional edge. Keep `human_gate: none` when an agent can re-check the blocker (upstream release, PR merge, dependency publication); raise to `decision`/`session` only when a human must unblock. |
| `blocked → active` | `goc status <title> active` (+ optionally `goc unadvance <title> --by <other>` if removing an obsolete edge) | flip status; optional edge. An autonomous agent MAY make this transition when it observes the external condition has cleared on a `human_gate: none` card (re-check confirms the upstream change). |
| `blocked → open` | `goc status <title> open` | re-queue when the blocker clears but the card is not yet being worked. Same agent-autonomy rule as `blocked → active`: gate `none` means an agent may flip; gate `decision`/`session` means the human owns the unblock. |
| `* → open` | `goc status <title> open` | re-queue (rare) |
| `* → disproved` | `goc status <title> disproved` | populate rebuttal first; CLI stamps `closed_at` |
| `* → superseded` | `goc status <title> superseded` | log replacement rationale in old card's `log.md`; CLI stamps `closed_at` |

`goc advance` and `goc unadvance` maintain the bidirectional
value-flow edge atomically (validator-enforced — if `A.advances`
contains `B`, `B.advanced_by` MUST contain `A`). The status `blocked`
is independent — set it via `goc status` when the card is parked
on external input.

## Step 3 — populate the body for transitions

Every transition has two writing surfaces — the README dashboard
(latest state) and `log.md` (the journal of how we got here). Each
status flip routes information to the right file:

| Transition | README dashboard (rewrite in place) | `log.md` journal (append entry) |
|---|---|---|
| `open → active` | no change required (claim adds `worker` field, not body content) | optional one-line "claimed by X on DATE" entry; usually skipped — the git commit suffices |
| `active → blocked` | update the relevant body section to reflect the blocker (e.g. "Fix" → "Blocked on upstream release of X") | append entry: when blocked, what the blocker is, expected unblock signal |
| `blocked → active` | rewrite the body section that named the blocker to reflect the new state of the world | append entry: when unblocked, what changed externally that cleared it |
| `* → open` (re-queue) | rewrite the body sections that are no longer accurate to match the new framing | append entry: why the card was re-queued (scope reset, evidence superseded, etc.) |
| `* → disproved` | rewrite body to document the rebuttal (see below) | append entry: when disproved, by what evidence |
| `* → superseded` | leave the body as the historical record; do NOT rewrite to point at the successor | append entry naming and linking the successor card and one-line why |

Rule of thumb: **state-of-the-world updates rewrite the README
dashboard; transition narrative, decisions, and timestamps append to
`log.md`.** See the `card-schema` skill's "What goes where" subsection.

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
`goc status <title> superseded` on the old card.

Append an entry to the old card's `log.md` to record the replacement:
name the replacement card, link it as
`[<new-title>](../<new-title>/)`, and note one-line why (different
approach, scope split, reframing). The relationship is forensic-only
— once a card is on the discard pile, the link lives in the journal,
not frontmatter (see the `card-schema` skill, "Replacement" section).
Leave the old README body as the historical dashboard; do NOT
rewrite it to point at the successor (that's the journal's job).

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
goc status <title> superseded
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
commits. The work commit, when it lands later after the `finish-card` skill,
contains the actual code/doc changes — NOT the status flip.

If the configured/forced auto-commit is skipped (no git repo, mid-merge /
mid-rebase, no diff), the CLI prints a one-line note. The on-disk state
still mutated; only the visibility-to-other-branches step deferred.

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

- the `finish-card` skill — for `done` transitions (DoD-gated).
- the `card-schema` skill — full transition semantics, bidirectional
  edge invariants, `human_gate` rules.
- the `create-card` skill — when the supersession needs a new card to
  point at.
