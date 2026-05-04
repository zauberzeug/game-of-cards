---
name: finish-card
description: "Close a card with DoD enforcement, log.md closure entry, and project-specific post-close / commit handoff. AUTO-INVOKE when user says \"done\", \"close this\", \"finish X\", \"mark complete\", \"wrap up\", \"ship it\", or completes work that satisfies a card's DoD. The DoD checkboxes ARE the closure contract (Scrum Definition of Done) — `goc done` refuses to close with any unchecked."
---

# Close a card

Scrum's **Definition of Done** as a machine-checkable closure contract.
The DoD is the agreement, set when the card was filed, that the work
is actually complete — not "the test passed once," but every named
criterion satisfied. An LLM agent reading the card at 3 AM in a /loop
iteration must not be able to mark the work done by accident; the
contract is enforced by `goc done`, which counts unchecked boxes
and refuses to flip the status if any remain. The human-typed checkbox
list is the audit trail.

Closure is an eight-step contract — skip a step and the card is dishonest:

1. Verify the work satisfies the DoD criteria.
2. Run the project-specific closure audit (or honestly note that no project rubric applies).
3. Tick the DoD checkboxes in the README.
4. Append closure context to `log.md` (including the audit outcome).
5. Run `goc attest <title>` to record the Closure-verification block in `log.md` (layer-2 + layer-3 DoDs from `.claude/deck-config.yaml`).
6. Run `goc done <title>` (DoD-100% gated).
7. Run any project-specific post-close action (status dashboard, changelog row, etc.) defined in the consuming repo's hook.
8. Commit or hand off according to the consuming repo's hook / normal runtime workflow.

If at any step the work turns out NOT to be a closure (a fix
attempt regressed, a hypothesis was disproved during verification),
divert to `Skill(advance-card)` for `disproved` / re-`open` instead.

User argument: $ARGUMENTS — title.

## Step 1 — confirm the work satisfies the DoD

Read the card:

!`.codex/skills/_goc-bootstrap.sh show <title>`

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

## Step 2 — project-specific closure audit

Closure should align with the consuming repo's project principles, not
just pass pytest + ruff. A fix that turns its tests green but encodes
a default the project's documented principles disagree with, silently
disables a primitive to mask a side-effect, or drifts a documented
contract is debt-accumulating even when "green". The audit forces the
closer to articulate *which* project principle the closure aligns with
— or to honestly note that no principle is touched (mechanical fixes:
cache invalidation, bounds checks, field-symmetric serialization).

!`cat .game-of-cards/hooks/finish-card.md 2>/dev/null || true`

If the consuming repo defined a closure-audit rubric in the hook above,
follow it. Then write the outcome into the Step 4 `log.md` closure
entry as exactly ONE of:

- **`<rubric-name> audit: PASS — invokes <principle> + <primary source>`**
  for fixes that touch a project principle.
- **`<rubric-name> audit: PASS — no principle touched, mechanical fix`**
  for fixes that don't bind to any project principle. Be honest — if the
  fix has *any* principle binding, name it instead.

If the audit FAILS — the fix encodes a default the project rubric
disagrees with, masks a missing concept, or contradicts a documented
principle — STOP the closure. Either redesign the fix to align
(preferred), or divert to `Skill(advance-card) <title> open` and append
a `## audit failed` section to `log.md` documenting what's wrong and
what an aligned resolution would look like.

If no project rubric is defined (the hook above is absent or empty),
the audit reduces to: "no rubric configured; mechanical fix" — record
that verbatim.

**No per-card DoD checkbox required.** This audit is a workflow gate
on every closure, not a per-card promise. Cards inherit the gate from
`finish-card` mechanics; the closure log entry is the audit trail.

## Step 3 — tick the DoD checkboxes

Edit `deck/<title>/README.md` and mark each criterion `- [x]`:

```yaml
definition_of_done: |
  - [x] reproduce.py exits zero (defect no longer fires)
  - [x] documented contract reflects the new default
  - [x] regression test added covering the previous-failing path
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
- **Audit**: PASS — <principle + primary source> | PASS — no principle touched, mechanical fix
- **Project impact**: <project-defined dashboard line, or "n/a">
- **Tests**: <count> passed / <count> failed / <count> xfailed
- **Bundled with**: <title-A>, <title-B> (if any)
```

## Step 5 — record the Closure verification (`goc attest`)

Implicit DoD layers — project-wide rules (e.g. "tests pass, ruff
green, audit pass, doc-consistency-checker") and
the GoC-wide rules ("schema valid, advanced_by closed, log.md has
closure entry, DoD 100%") — are the *meta*-contract that applies to
every closure regardless of what the card does. Today they're invisible:
a 6-month-old reader sees the layer-1 ticked boxes but no record of
whether layer-2 or layer-3 was actually verified.

`goc attest` reads `.claude/deck-config.yaml`, runs each layer-2 +
layer-3 check (or prompts the closer for manual ones), and appends a
"Closure verification (DATE)" block to `log.md`. The block is the
audit trail.

```bash
goc attest <title>
```

The command:
- **Automated checks** run as subprocesses (`pytest`, `ruff check`,
  `ruff format --check`, `goc validate`). Non-zero exit fails.
- **Derived checks** compute from card state (DoD %, advanced_by
  closure, log.md grep for the Step 4 closure section).
- **Manual checks** (`audit`, `no-debug-code`) prompt the
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
because the closure transition belongs in the same work commit as the
code/doc diff. The `done` flip remains in the working tree until Step 8
stages and commits it, or until the runtime hands it to the user's
normal commit flow.

For free-form prose DoDs (zero `[ ]` AND zero `[x]` boxes
detected), `done` requires `--force` to bypass enforcement — but
prefer adding checkboxes over forcing.

**Bundled closures** (one fix resolves multiple cards): run
`goc attest <title>` then `goc done <title>` for each.
Each gets its own `closed_at` and its own attestation block.
Cite the sibling slugs in each body's log entry.

## Step 7 — project-specific post-close action

If the consuming repo defined a post-close action in
`.game-of-cards/hooks/finish-card.md` (a status dashboard refresh, a
changelog row, a release-notes entry, etc.), the hook below carries
the recipe. Otherwise this step is a no-op.

!`cat .game-of-cards/hooks/finish-card.md 2>/dev/null || true`

Note: the hook file is *also* loaded in Step 2 above; both steps share
the same hook file because both are project-rubric questions and the
consuming repo authors them together.

## Step 8 — commit or hand off

GoC does not ship a commit-helper skill. If the consuming repo wants a
custom commit flow, it belongs in `.game-of-cards/hooks/finish-card.md`
and should be followed here. Otherwise use the runtime's normal commit
workflow: inspect `git status` / `diff`, run the repo's relevant checks,
stage specific files, and commit the work plus the closure transition.

Note: claim/decide/advance state changes already auto-committed
earlier in the card's lifecycle (per `Skill(advance-card)` Step 5).
The final commit here ships the **work** only — the actual code/doc
changes plus the closure transition (DoD ticks, log.md entries from
Steps 4 + 5, `status: done`, `closed_at`).

Override the message:

- **Subject:** `fix(<scope>): <one-line subject> — closes <title>`.
  Examples:
  - `fix(api/csv-export): stream rows without 10000-row cap — closes csv-export-button-truncates-rows-over-10000`
  - `fix(auth/cookie): bump cookie max-age to 24h — closes auth-cookie-expires-too-soon`
- For bundled closures, append additional slugs:
  `fix(<scope>): <subject> — closes <title-A>, <title-B>, <title-C>`.
- **Body:** explain WHY (which user-visible problem this resolves;
  what measurement bias it removed). Include verification numbers
  and the closure log. Reference the `deck/<title>/` archive.
- **Trailer:** follow the consuming repo's authorship convention, if
  one exists.

If the commit workflow fails *because of this work* (newly broken test,
lint error you introduced, deck-validate rejection), fix and re-run it.
If it fails on a pre-existing issue, surface that in chat and stop —
that's a separate concern.

## Cross-references

- `Skill(card-schema)` — DoD format + free-form-prose escape.
- `Skill(advance-card)` — divert here if verification reveals the
  hypothesis was wrong (`→ disproved`) or the fix needs more work
  (`→ active` retained or `→ open` re-queued).
