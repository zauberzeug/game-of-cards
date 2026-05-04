---
description: Close a card with DoD enforcement, log.md closure entry, STATUS.md refresh, and commit via Skill(prepare-commit). AUTO-INVOKE when user says "done", "close this", "finish X", "mark complete", "wrap up", "ship it", or completes work that satisfies a card's DoD. The DoD checkboxes ARE the closure contract (Scrum Definition of Done) — `deck.py done` refuses to close with any unchecked.
argument-hint: <title>
---

# Close a card

Scrum's **Definition of Done** as a machine-checkable closure contract.
The DoD is the agreement, set when the card was filed, that the work
is actually complete — not "the test passed once," but every named
criterion satisfied. An LLM agent reading the card at 3 AM in a /loop
iteration must not be able to mark the work done by accident; the
contract is enforced by `deck.py done`, which counts unchecked boxes
and refuses to flip the status if any remain. The human-typed checkbox
list is the audit trail.

Closure is an eight-step contract — skip a step and the card is dishonest:

1. Verify the work satisfies the DoD criteria.
2. Run a `/mindset` audit (closure must align with axioms or honestly note "no axiom touched").
3. Tick the DoD checkboxes in the README.
4. Append closure context to `log.md` (including the audit outcome).
5. Run `deck.py attest <title>` to record the Closure-verification block in `log.md` (layer-2 + layer-3 DoDs from `.claude/deck-config.yaml`).
6. Run `deck.py done <title>` (DoD-100% gated).
7. Refresh `demos/pong/STATUS.md` dashboard.
8. Hand to `Skill(prepare-commit)`.

If at any step the work turns out NOT to be a closure (a fix
attempt regressed, a hypothesis was disproved during verification),
divert to `Skill(advance-card)` for `disproved` / re-`open` instead.

User argument: $ARGUMENTS — title.

## Step 1 — confirm the work satisfies the DoD

Read the card:

!`goc show <title>`

Re-confirm each DoD criterion against the actual work:

- For `- [ ] reproduce.py exits zero (defect no longer fires)` —
  run `uv run python deck/<title>/reproduce.py` and confirm exit 0
  with the no-defect output.
- For `- [ ] <metric assertion>` — run the relevant pytest /
  sweep and capture the verification number.
- For doc-quality criteria — re-read the cited paper / axiom and
  confirm the doc now aligns.

If any criterion is NOT actually satisfied, **stop the closure**:
- If the fix attempt failed → revert, append a `## Disproved fix
  attempt` section to `deck/<title>/log.md`, leave status `active`
  or flip back to `open` via `Skill(advance-card)`.
- If verification revealed the hypothesis was wrong → divert to
  `Skill(advance-card) <title> disproved`.

## Step 2 — `/mindset` audit (closure must align with axioms)

Bio-faithfulness is the methodology's target (CLAUDE.md "Bio-divergence
is a bug, not a tradeoff"). A fix that passes pytest + ruff but encodes
a non-bio-faithful default, silently disables a primitive to mask a
side-effect, or drifts a documented contract is debt-accumulating even
when "green". The audit forces the closer to articulate *which*
principle the closure aligns with — or to honestly note that no axiom
is touched (engineering-substrate fixes: cache invalidation, bounds
checks, field-symmetric serialization).

Invoke `Skill(mindset)` to load the vision / axioms / plasticity
context (skip for clearly mechanical fixes — but only if you can
honestly write the "no axiom touched" statement without /mindset
loaded). Then write the outcome into the Step 4 `log.md` closure
entry as exactly ONE of:

- **`/mindset audit: PASS — invokes <axiom> + <primary source>`** for
  fixes that touch axiomatic mechanisms. Example: `"/mindset audit:
  PASS — invokes A5 layer-3b-F heterosynaptic LTD (Eckmann 2024 /
  Royer-Paré 2003); fix shifts the row-L1 invariant from row-L2
  toward bio-faithful row-L1 sum."`
- **`/mindset audit: PASS — no axiom touched, mechanical fix`** for
  engineering-substrate fixes that don't touch any biological
  mechanism. Be honest — if the fix has *any* axiom binding, name
  it instead.

If the audit FAILS — the fix encodes a non-bio-faithful default,
masks a missing concept, or contradicts a documented axiom — STOP
the closure. Either redesign the fix to be bio-faithful (preferred),
or divert to `Skill(advance-card) <title> open` and append a
`## /mindset audit failed` section to `log.md` documenting what's
wrong and what a bio-faithful resolution would look like.

**No per-card DoD checkbox required.** This audit is a workflow gate
on every closure, not a per-card promise. Cards inherit the gate from
`finish-card` mechanics; the closure log entry is the audit trail.

## Step 3 — tick the DoD checkboxes

Edit `deck/<title>/README.md` and mark each criterion `- [x]`:

```yaml
definition_of_done: |
  - [x] reproduce.py exits zero (defect no longer fires)
  - [x] axioms.md A5 Layer 3b-F lists row-L1 invariant
  - [x] 10-seed pong sweep within 2σ of prescribed motor row-L1
```

If the fix added a sub-criterion the original DoD didn't anticipate,
add a new ticked box and note in the body why. If a criterion
turned out to be moot (e.g., not reachable in shipping at any
default), strike it from the DoD with a one-line justification
rather than ticking it falsely.

## Step 4 — append closure context to `log.md`

`deck/<title>/log.md` is the append-only round/phase narrative;
never rewrite existing entries. Format the closure entry:

```markdown
## YYYY-MM-DD — Closure

- **What changed**: <file:line> — <one-line essence>
- **Verification**: <one or two key numbers>
- **/mindset audit**: PASS — <axiom + primary source> | PASS — no axiom touched, mechanical fix
- **Pong impact**: dormant / +Xpp probe / -Ypp regression / etc.
- **Tests**: <count> passed / <count> failed (Bug 119 baseline) / <count> xfailed
- **Bundled with**: <title-A>, <title-B> (if any)
```

## Step 5 — record the Closure verification (`deck.py attest`)

Implicit DoD layers — the project-wide rules in CLAUDE.md ("tests
pass, ruff green, /mindset audit pass, doc-consistency-checker") and
the GoC-wide rules ("schema valid, advanced_by closed, log.md has
closure entry, DoD 100%") — are the *meta*-contract that applies to
every closure regardless of what the card does. Today they're invisible:
a 6-month-old reader sees the layer-1 ticked boxes but no record of
whether layer-2 or layer-3 was actually verified.

`deck.py attest` reads `.claude/deck-config.yaml`, runs each layer-2 +
layer-3 check (or prompts the closer for manual ones), and appends a
"Closure verification (DATE)" block to `log.md`. The block is the
audit trail.

```bash
goc attest <title>
```

The command:
- **Automated checks** run as subprocesses (`pytest`, `ruff check`,
  `ruff format --check`, `deck.py validate`). Non-zero exit fails.
- **Derived checks** compute from card state (DoD %, advanced_by
  closure, log.md grep for the Step 4 closure section).
- **Manual checks** (`/mindset audit`, `no-debug-code`) prompt the
  closer interactively for pass/fail + a one-line rationale. The
  rationale is recorded verbatim in the log block.
- **Agent checks** (`doc-consistency-checker`) prompt the closer to
  confirm the subagent was run separately and what it reported.
  Accept `n/a` for pure code/no-doc closures.
- On any failure: exits non-zero. Closure blocks. Fix the failing
  check, re-run `attest`. Per the 2026-05-03 decision, no waivers.

To skip a single check (rare, e.g. when an automated check is
genuinely flaky): `--skip <name>`. The skip is recorded as
`[~] SKIPPED — <description>` in the block. Do not skip casually.

## Step 6 — close via the CLI

```bash
goc done <title>
```

The command:
- Counts `[ ]` boxes — if any are unchecked, exits 2 with
  `ERROR: <title>: <n> unchecked DoD boxes`. Tick them and re-run.
- Sets `status: done` and `closed_at: <today>` via line-anchored
  regex (no YAML round-trip; comments and key order preserved).
- Prints `<title>: open → done` on success.

`done` does NOT auto-commit (unlike `status` / `decide` / `advance`),
because the closure transition is bundled with the work commit via
Step 8 (prepare-commit). The `done` flip stages alongside the work
diff.

For free-form prose DoDs (zero `[ ]` AND zero `[x]` boxes
detected), `done` requires `--force` to bypass enforcement — but
prefer adding checkboxes over forcing.

**Bundled closures** (one fix resolves multiple cards): run
`deck.py attest <title>` then `deck.py done <title>` for each.
Each gets its own `closed_at` and its own attestation block.
Cite the sibling slugs in each body's log entry.

## Step 7 — update `demos/pong/STATUS.md`

Always add a Recent activity row for the closure (even if metrics
/ config didn't shift — mark "pong-dormant" in the Subject text).
The row is the dashboard's audit trail; omitting it makes the
closure invisible from the entry-point doc and trips
doc-consistency-checker.

!`head -100 demos/pong/STATUS.md`

Format:

```markdown
| YYYY-MM-DD | closed | <title> — <one-line subject>; <pong impact> | [→](../../deck/<title>/) |
```

If shipping config changed, also edit the matching Shipping config
table row. If shipping metrics changed (you ran a sweep), replace
the "Latest metrics" table with the new sweep's numbers and add a
one-line footnote referencing the title.

### Enforce STATUS.md dashboard form

After updating STATUS.md (Step 7), verify:

1. **Section order:** Shipping config → Latest metrics → Recent
   activity → Active open items → Key design principles →
   Pointers. Past-sprint analyses do NOT belong here — move them
   to HISTORY.md.
2. **Shipping config is a single table.** No prose between rows.
3. **Latest metrics is a single table.** At most ONE footnote of
   ≤ 3 sentences.
4. **Recent activity** is a 3–5 row table, newest first. Rotate
   out the oldest row when adding a new one.
5. **Active open items** — bulleted list, every item ≤ 200 chars.
6. **Key design principles** — bulleted list, each ≤ 200 chars.
7. **No section is dedicated to a single past sprint's analysis.**

If any check fails, fix it before commit. The dashboard property
is load-bearing — STATUS.md is read at-a-glance; the moment it
grows past one screen of compact tables it loses that role.

## Step 8 — commit via `Skill(prepare-commit)`

Invoke `Skill(prepare-commit)`. It runs the full gauntlet
(`git status` / `diff`, pytest, pre-commit hooks including
`deck-validate`, ruff/mypy/pylint, doc-consistency-checker), writes
the commit message, stages, and commits.

Note: claim/decide/advance state changes already auto-committed
earlier in the card's lifecycle (per `Skill(advance-card)` Step 5).
`prepare-commit` here ships the **work** commit only — the actual
code/doc changes plus the closure transition (DoD ticks, log.md
entries from Steps 4 + 5, `status: done`, `closed_at`).

Override the message:

- **Subject:** `fix(<scope>): <one-line subject> — closes <title>`.
  Examples:
  - `fix(plasticity/synaptic_scaling): wire heterosynaptic LTD on W_coupling — closes heterosynaptic-ltd-absent-fchannel`
  - `fix(pong/agent): remove phantom contact→motor plasticity mask — closes phantom-contact-motor-mask`
- For bundled closures, append additional slugs:
  `fix(<scope>): <subject> — closes <title-A>, <title-B>, <title-C>`.
- **Body:** explain WHY (which user-visible problem this resolves;
  what measurement bias it removed). Include verification numbers
  and the closure log. Reference the `deck/<title>/` archive.
- **Trailer:** `Co-Authored-By: Claude Opus 4.7 (1M context)
  <noreply@anthropic.com>`.

If prepare-commit FAILS *because of the work-todo run itself*
(newly broken test, lint error you introduced, deck-validate
rejection), fix and re-invoke. If it FAILS on a pre-existing issue,
surface in chat and stop — that's a separate concern.

## Cross-references

- `Skill(prepare-commit)` — the commit gauntlet.
- `Skill(card-schema)` — DoD format + free-form-prose escape.
- `Skill(advance-card)` — divert here if verification reveals the
  hypothesis was wrong (`→ disproved`) or the fix needs more work
  (`→ active` retained or `→ open` re-queued).
