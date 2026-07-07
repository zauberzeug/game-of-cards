---
name: card-schema
description: "Card schema reference — fields, status/stage/contribution/human_gate enums, canonical tags, DoD detection, relationship invariants, title convention. AUTO-INVOKE when other deck skills need schema context, or when the user asks about field semantics, status lifecycle, DoD format, or card titling."
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


## When to invoke

Invoke when other deck skills need schema context, or when the user asks about field semantics, status lifecycle, DoD format, canonical tags, the decision-gate body contract, or how to title a card.

# Card Schema

The shared vocabulary that makes the deck a **contract**: every field
has defined semantics, a defined enum, and a validator that refuses
unknown values. Read-only reference; mutations go through
`Skill(create-card)` / `Skill(advance-card)` / `Skill(finish-card)`.
The machine-readable schema ships as the sibling `schema.yaml`.

**Deep dives live in `reference.md`** (sibling file in this skill's
directory) — read the named section only when needed:

| Question | `reference.md` section |
|---|---|
| Why can't this close with an open `advanced_by`? | Value-chain rule |
| Epic vs governing cluster — reasoning + lint | Coordinating cards |
| Why do closed cards keep their edges? | Deck as scheduler vs record |
| What goes in `## Decision required`? | Decision-gate body contract |
| Stuck-model semantics + `blocked` migration | Three-axis model |
| Draft / DoD layers / timestamps / example | (same-named sections) |

## Layout

```
deck/<title>/             # one dir per card; never moves on state change
  README.md               # frontmatter + dashboard body — latest state
  log.md                  # append-only journal — history, decisions, flow
  reproduce.py, *.html …  # OPTIONAL artifacts, opaque to the engine
```

Status changes mutate frontmatter, never directories — references
survive every transition (artifacts: `Skill(create-card)` Step 7).

### What goes where (dashboard vs journal)

| File | Role | Edit discipline |
|---|---|---|
| `README.md` | **Dashboard** — latest knowledge, current state; a cold reader sees only what is true now | rewritten in place; outdated content replaced, never amended below |
| `log.md` | **Append-only journal** — history, decisions, flow for forensic readers | strictly appended; existing entries never rewritten |

If the README alone would mislead, update the dashboard; if the
value is in the sequence, append to the journal — most operations
want both. "Latest finding (DATE)" blocks appended to a README are
the antipattern: rewrite in place. Closure does not freeze the card
(`Skill(finish-card)` "After closure").

## Status semantics

| value | meaning |
|---|---|
| `open` | candidate for work; in the queue |
| `active` | work in progress (one author/agent at a time, by convention) |
| `done` | terminal; DoD all ticked — `goc done <title>` enforces this |
| `disproved` | terminal; hypothesis ruled out, body documents the rebuttal |
| `superseded` | terminal; replaced by another card, typed link routes forward |

`blocked` is deprecated — split into derived dependency-readiness and
the `waiting_on` overlay (`reference.md` § Three-axis model). There
is no `unverified` status: that is `status: open` +
`tags: [unverified]`.

## Field reference

### `created` / `closed_at` — timestamps

`created` at birth; `closed_at` on **every** terminal transition,
required iff terminal. Two ordering-compatible shapes: ISO 8601 UTC
datetime `YYYY-MM-DDTHH:MM:SSZ` (what the CLI writes) and legacy
date-only `YYYY-MM-DD`. UTC only (`reference.md` § Timestamps).

### `summary`

Optional free-form, ≤ 3 sentences, what + why (not the fix path), so
triage views (`goc -v`) can prioritize without opening the body.
Plain prose; renders inline. Convention, not validator-enforced.

### `stage`

Optional KEP-style maturity ladder for research items: `null` (the
default — no tracking) → `alpha` → `beta` → `stable`. `status: done`
+ `stage: alpha` is valid; subsequent maturity work files a new card.

### `contribution`

How much does closing this card *alone* deliver or unlock? `high` —
terminal milestone OR load-bearing infrastructure many cards depend
on; `medium` — improves a working system (optimization, hardening,
guard rail); `low` — editorial polish. The sort composes it across
the `advances` graph (Bellman discount γ=0.7) into the `value` score
driving `pull-card` — a `medium` card on a chain to a `high` sink can
outrank an isolated `high`.

### `human_gate`

Orthogonal to `status`: does progress require a human?

- `none` — autonomous-loop-safe; cron may auto-pick. An
  agent-checkable external wait is the `waiting_on` overlay, not a
  gate.
- `decision` — ONE human go/no-go. The body MUST already carry a
  `## Decision required` section: reasoning, ≥ 2 named options with
  pros/cons and a file:line preview, one-line recommendation
  (`reference.md` § Decision-gate body contract).
- `session` — needs an interactive working session.

Pickability: `none` → next-card picks; `decision` → session ends
cleanly, pointing at the parked card; `session` → only an interactive
session advances. Terminal closes refuse while the gate is raised
(`goc decide` first; `reference.md` § Gate symmetry). `goc new`
default: `decision`.

### `waiting_on` / `waiting_until` — impediment overlay

Stored, orthogonal to `status`; the exogenous waits the dependency
graph cannot derive. `waiting_on` ∈ `external` (third party) |
`resource` (person/skill unavailable) | `deferred` (calendar defer);
`waiting_until` is an optional ISO date (bare date implies
`deferred`). A future date — or a reason with no date — hides the
card from `--ready` / next-card / pull-card and self-clears when it
passes; an elapsed date surfaces as `WAITING_OVERDUE`. Set / clear
via `goc wait <title> [--reason <r>] [--until <date>] [--clear]`
(`Skill(advance-card)` Step 6).

Ready-to-pull predicate: `status == open ∧ human_gate == none ∧ not
waiting_impedes(card)`. An open `advances` prereq does NOT gate
pulling — advisory "awaiting" line only (`reference.md` § Three-axis
model).

### `worker`

Optional free-form assignee: flat string (`worker: rodja`) or mapping
(`worker: {who: rodja, where: feature/foo}`); unregistered values.
Auto-populated at claim time by `goc status <title> active`; persists
after close. Filter with `goc --worker <X>` or `GOC_WORKER`.

### `draft`

Boolean overlay marking an unauthored scaffold. `goc new` stamps it;
clears on claim or close, or via `goc publish <title>`. While set:
hidden from queues (visible under `--status all`, `✎` on the board),
protected from supersede/disprove closes, skipped by auto-commit; may
not be terminal. Details: `reference.md` § Draft contract.

### `advances` / `advanced_by` — value-flow axis

- `advances` — slugs whose progress this card contributes to ("X
  advances Y" = closing X delivers a piece of Y's value chain).
- `advanced_by` — the inverse; slugs contributing to this card.

**Invariant:** `A.advances` contains `B` ⇔ `B.advanced_by` contains
`A` — maintained atomically by `goc advance <title> --by <other>` /
`goc unadvance`; half-edges are validator errors; cycles forbidden.
Epics are just cards with `advanced_by: [children]`.

**Value-chain rule (short form):** a true edge means the target is
not closeable while the source is open — the `advanced-by-closed`
attest check enforces exactly this. When it fires: wait, or retract a
false edge with `goc unadvance` — never `--skip` past it
(`reference.md` § Value-chain rule).

**Coordinating cards (short form):** aggregation epic →
`child.advances: [epic]`; governing cluster (closes when *decided*) →
shared tag, NO edge; `epic.advances: [children]` is always wrong
(`BACKWARDS_EPIC_EDGE`; `reference.md` § Coordinating cards).

### `supersedes` / `superseded_by` — replacement axis

`superseded_by` — slugs replacing this card (on the *old* card);
`supersedes` — the inverse (on the *new* card).
`goc status <title> superseded --by <successor>` maintains both
endpoints atomically. Validator-enforced: bidirectional consistency;
non-empty `superseded_by` ⇒ `status: superseded`; every `supersedes`
entry points at a `superseded` card. The typed edge is the pointer;
the *rationale* still appends to the old card's `log.md`
(`reference.md` § Deck as scheduler vs record).

### `tags` — grouping

Canonical-set enforced (below). Soft grouping and governing clusters;
one conventional tag per epic-shaped body of work, retired when the
epic closes. Lineage is forensic prose for `log.md`, never
frontmatter.

**YAML format:** non-empty edge lists (`advances` etc.) render
block-style (one `- item` per line); empty lists inline `[]`; `tags`
stays inline flow style.

## Definition of Done (layer 1)

**Checkbox list (preferred):** `- [ ]` items mutating to `- [x]`;
`goc done` requires every box ticked. Detection: `^- \[[ x]\]` lines;
zero matches → free-form prose mode, which requires `goc done
--force`. Layers 2 (project-wide) and 3 (GoC-wide) are recorded at
closure by `goc attest` (`reference.md` § DoD layers).

### DoD method tags

Declare each item's closure class with a colon-suffixed prefix:

| Tag | Closure rule |
|---|---|
| `TDD:` | a deterministic predicate with a closed-form expected value holds |
| `EMPIRICAL:` | the experiment ran and the verdict is documented — direction does **not** gate closure |
| `MECHANICAL:` | a reviewer confirms the edit landed by reading |
| `PROCESS:` | an agreement, gate flip, or edge update happened |

Prefer `TDD:` whenever a closed-form expected value exists;
mislabelling a provable assertion as `EMPIRICAL:` lets a real failure
hide behind "the experiment ran". `goc validate` warns
(`UNTAGGED_DOD_ITEM`, non-fatal) on untagged boxes in non-terminal
cards.

## Title antipatterns (rejected at filing time)

Titles ARE the kanban label — a non-engineer reading `goc --board`
must understand each card without opening it. `goc new` rejects:

| Pattern | Example | Why bad |
|---|---|---|
| `\br\d+\b` | `r88-csubstrate-replication` | investigation-round reference |
| `\bpath-\d+\b` / `\bphase-\d+\b` | `path-2-recovery` | internal sequence step |
| `\bbug-\d+\b` | `bug-140-fix` | tracker numbering |
| `_md_` / `_py_` | `coupling-md-formula` | file infix — name the concept |
| camelCase | `runSimulation-fails` | function jargon |
| math symbols | `late-hr-≥-0.5` | slug allows `[a-z0-9-]` only |
| underscores | `my_first_card` | slug allows `[a-z0-9-]` only |

On rejection the CLI suggests a rephrasing from the *observable
problem*; `Skill(refine-deck)`'s quality pass checks the same
dimensions across the existing deck.

## Canonical tags

Project-specific tags register in `.game-of-cards/canonical-tags.md`
(merged into the enum by `goc validate`); goc-shipped tags change via
PR (`reference.md` § Adding new tags). A tag is **load-bearing** iff
its predicate fires on the title, H1, or first ~2500 chars of body;
when in doubt, drop it.

| tag | applies iff |
|---|---|
| `bug` | not `epic` and not `story` (default for findings) |
| `epic` | multiple cards block its closure OR carry its epic-grouping tag |
| `story` | part of an epic-grouping (carries the epic-grouping tag) |
| `unverified` | no working `reproduce.py` AND tagged at filing |
| `documentation` | doc-quality failure (`doc`/`stale`/`drift`/`mismatch`/`cite`/`claim`/`readme-` in title, or body cites docstrings / `.md says`) |
| `test` | title starts `test-` or contains `tolerance`/`vacuous`/`regression`, or body cites pytest / `tests/` |
| `api-contract` | cites a public API surface callers depend on |
| `infra` | touches infrastructure (pre-commit, `pyproject.toml`, CI, packaging) |
| `meta-fix` | literal `meta-fix` / `family meta-fix` in title or body |

Project-specific predicates appended below:

!`cat .game-of-cards/canonical-tags.md 2>/dev/null || true`
