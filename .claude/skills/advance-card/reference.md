# advance-card reference — edge cases and rationale

Companion to `SKILL.md`. Each section below is routed from the core
skill; read the one that matches the situation at hand.

## Rationale

Kanban's **explicit policies** (Anderson): every status transition is
a documented agreement, not a silent flag flip. The lane a card sits
in says what's true about it; the move between lanes carries a
reason — recorded in the body for terminal transitions, in the commit
message for mid-flight ones. A swarm of /loop iterations cannot
audit-trail conversational context, so the rule is: the policy lives
on disk.

Why claim-is-its-own-commit: when two branches both work the deck,
the soft lock (`status: active`) should be git-observable so a
sibling branch pulling sees "this card is claimed" before it races on
the same YAML. The work commit, landing later after
`Skill(finish-card)`, contains the actual code/doc changes — NOT the
status flip.

## Deprecated blocked status

Earlier releases included a `blocked` status that conflated three
orthogonal axes. The three-axis model (see `Skill(card-schema)`
"Three-axis stuck model") splits the old meaning into:

- **derived dependency-readiness** — an `advanced_by` prereq still
  open is computed at read time and self-clears when the prereq
  closes; no stored state.
- **stored impediment overlay** — `waiting_on` (+ optional
  `waiting_until`) for exogenous waits; set via `goc wait`.

The enum value still parses for backwards compatibility but is being
removed in a follow-up release. When touching a legacy `blocked`
card, migrate it: drop to `open` for dependency-derived cases, set
`waiting_on` for exogenous-wait cases.

For an agent-observable wait (upstream release, PR merge, dependency
publication) the card stays `status: open` with
`waiting_on: external` and an optional `waiting_until` date — a
future autonomous run re-checks the condition and
`goc wait <title> --clear`s the overlay when the wait resolves. For a
human-judgement wait, raise `human_gate` to `decision` / `session`
and write the framing into the body; no status flip required.

## Terminal transitions

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

Append an entry to the old card's `log.md` recording the replacement
*rationale*: one line on why (different approach, scope split,
reframing). The typed field is the machine-navigable pointer; the
journal entry is the prose-only *why* a graph edge cannot capture —
both, for different jobs.

Leave the old README body as the historical dashboard; do NOT rewrite
it to point at the successor (the typed link does that mechanically).
Add a one-line `> Later: [<new-title>](../<new-title>/)` pointer atop
the body only if a cold reader would otherwise be misled — see
`Skill(card-schema)` "Replacement axis".

Plain `goc status <title> superseded` (without `--by`) is still
accepted for backwards compatibility, but leaves the supersession
prose-only and forces forensic readers to grep `log.md`. Prefer the
`--by` form for every new supersession.

## Edge vs tag

The full decision procedure behind the core skill's short form:

1. **Same value chain — does the source's closure deliver a piece of
   the target's value?** → `advances` edge. The dependent inherits
   the source's priority and cannot close until the source closes
   (see `Skill(card-schema)` "Value-flow axis").
2. **Same theme, no closure-time dependency — would a future filter
   ("show me all the X cards") want them grouped?** → shared **tag**.
   No edge in either direction.
3. **One card coordinates many others** → the three-way fork:

- **Aggregation epic** — its value chain *is* its children; closes
  when they close. Encoding: `child.advances: [epic]`. Verb on the
  child: `goc advance <child> --by <epic>`.
- **Governing cluster** — a decision or standard-setting card that
  closes when *decided*, independent of the cluster's work. Encoding:
  a **shared tag**, no `advances` edge in either direction. Add the
  tag at `goc new --tag <name>` time on both the governing card and
  each instance; for an existing card, edit `tags:` in the
  frontmatter directly (there is deliberately no `goc add-tag` verb).
  To register a new project-specific tag, see `Skill(card-schema)`
  "Adding new tags".
- **Backwards aggregation** — `epic.advances: [children]`. **Never.**
  Defeats the value law (children stop inheriting the epic's value,
  so the priority sort cannot see the chain) and trips a spurious
  `advanced-by-closed` FAIL on every child at attest time.
  `goc validate` flags this signature as `BACKWARDS_EPIC_EDGE`.

The tell: if the coordinating card closes on its own deliverable
(typically `human_gate: decision`) rather than on its cluster's
completion, it is a governing cluster → tag, not edge. Full
value-law derivation: `Skill(card-schema)` "Coordinating cards".

`goc advance` / `unadvance` maintain the bidirectional invariant
(`A.advances` ⇔ `B.advanced_by`) atomically — the validator refuses
half-edges; cycles are forbidden.

## Retraction

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

## Worker field

`worker` is an optional free-form identifier naming who should or
does work on a card; it matters when multiple humans or agents share
a deck and you want a runner-scoped queue view.

**Format:**

- Flat string for a single identifier: `worker: rodja`. Sugar for
  `{who: rodja}`.
- Mapping with branch context:
  `worker: {who: rodja, where: feature/foo}`.

The value is unregistered — pick a person slug, machine name, or
capability tag (`gpu-required`, `human`, `rendering-expert`). The
field persists after close as a historical record.

**Filter the queue by worker:**

- `goc --worker <X>` — limit listings to cards owned by `X`.
- Set the `GOC_WORKER` env var so a runner sees only its own queue
  without typing the flag every time.
