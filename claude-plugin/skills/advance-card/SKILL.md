---
name: advance-card
description: Mutate a card's status (open / active / blocked / disproved / superseded — everything except `done`). AUTO-INVOKE when user says "I'll start on X", "I'm working on", "this is blocked by Y", "mark this disproved", "supersede with Z", "unblock", or describes any non-done status change. Status transitions are documented agreements (Kanban explicit policies, Anderson).
argument-hint: <title> <new-status: active|blocked|open|disproved|superseded> [--by <other-title>]
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
`Skill(finish-card)`'s DoD-gated contract. Read the card first to
confirm the transition is legal under those policies, then run the
matching CLI.

User argument: $ARGUMENTS — `<title> <new-status> [--by <other-title>]`.

## Step 1 — read the card

!`.claude/skills/_goc-bootstrap.sh show <title>`

Confirm:
- Current status matches the transition you're about to make
  (e.g. `open → active` requires current `open`).
- The `human_gate` is appropriate for the new state. If you're
  flipping a `session`-gated card to `active` autonomously, stop —
  that's a research-impacting move and needs the human in the
  loop.
- For `disproved` / `superseded`, the body documents the rebuttal /
  replacement before you flip.

## Step 2 — match the transition to the CLI

| transition | CLI | notes |
|---|---|---|
| `open → active` | `goc status <title> active` | "claiming" the card |
| `active → blocked` | `goc status <title> blocked` (+ optionally `goc advance <title> --by <other>` if a specific card is what's needed) | flip status; optional edge |
| `blocked → active` | `goc status <title> active` (+ optionally `goc unadvance <title> --by <other>` if removing an obsolete edge) | flip status; optional edge |
| `* → open` | `goc status <title> open` | re-queue (rare) |
| `* → disproved` | `goc status <title> disproved` | populate rebuttal first |
| `* → superseded` | `goc status <title> superseded` | log replacement rationale in old card's `log.md` |

`goc advance` and `goc unadvance` maintain the bidirectional
value-flow edge atomically (validator-enforced — if `A.advances`
contains `B`, `B.advanced_by` MUST contain `A`). The status `blocked`
is independent — set it via `goc status` when the card is parked
on external input.

## Step 3 — populate the body for terminal transitions

### Disproved

Edit `deck/<title>/README.md` body to document:

- The hypothesis (what was claimed).
- The verdict (FALSE — what's actually in the code).
- The source of error (which agent / partial reading triggered it).
- A one-line lesson if non-obvious.

This is mandatory. Without it, every scheduled run that spawns the
same agent set may re-propose the same false lead and waste a
verification cycle.

### Superseded

The new card's body explains what it supersedes and why. Run
`goc status <title> superseded` on the old card.

Edit the old card's `log.md` to record the replacement: name the
replacement card, link it as `[<new-title>](../<new-title>/)`, and
note one-line why (different approach, scope split, reframing). The
relationship is forensic-only — once a card is on the discard pile,
the link lives in prose, not frontmatter (see `Skill(card-schema)`,
"Replacement" section).

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
commits. The work commit, when it lands later after `Skill(finish-card)`,
contains the actual code/doc changes — NOT the status flip.

If the configured/forced auto-commit is skipped (no git repo, mid-merge /
mid-rebase, no diff), the CLI prints a one-line note. The on-disk state
still mutated; only the visibility-to-other-branches step deferred.

## Cross-references

- `Skill(finish-card)` — for `done` transitions (DoD-gated).
- `Skill(card-schema)` — full transition semantics, bidirectional
  edge invariants, `human_gate` rules.
- `Skill(create-card)` — when the supersession needs a new card to
  point at.
