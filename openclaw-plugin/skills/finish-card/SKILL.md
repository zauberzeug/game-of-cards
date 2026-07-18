---
name: finish-card
description: Close a card with DoD enforcement and a log.md closure entry — goc done refuses to close with any unchecked box. AUTO-INVOKE on "done", "close this", "finish X", "ship it", or when work satisfies a card's DoD. For every other status change, use advance-card. If the catalog location path is unreadable, fetch the body via the goc tool verb "skill", args ["finish-card"].
---

## When to invoke

Invoke when the user says "done", "close this", "finish X", "mark complete", "wrap up", "ship it", or completes work that satisfies a card's DoD. The DoD checkboxes ARE the closure contract (Scrum Definition of Done).

# Close a card

Scrum's **Definition of Done** as a machine-checkable closure
contract: `goc done` counts unchecked boxes and refuses to flip the
status while any remain. The ticked checkbox list is the audit trail.

Closure is an eight-step contract — skip a step and the card is dishonest:

1. Verify the work satisfies the DoD criteria.
2. Run the project-specific closure audit (or honestly note that no project rubric applies).
3. Tick the DoD checkboxes in the README.
4. Append closure context to `log.md` (including the audit outcome).
5. Run `goc attest <title>` to record the Closure-verification block in `log.md`.
6. Run `goc done <title>` (DoD-100% gated).
7. Run any project-specific post-close action defined in the consuming repo's hook.
8. Commit or hand off per the consuming repo's hook / normal runtime workflow.

If at any step the work turns out NOT to be a closure (a fix attempt
regressed, a hypothesis was disproved during verification), divert to
the `advance-card` skill for `disproved` / re-`open` instead.

**Edge cases live in `reference.md`** — a sibling file in this
skill's directory. Read the named section only when the situation
actually applies:

| Situation | `reference.md` section |
|---|---|
| One fix closes several cards | Bundled closures |
| `advanced-by-closed` FAILs at attest time | Retraction vs waiting |
| An attest check needs `--skip` | Attest details and skip policy |
| New evidence after the card closed | After closure |
| Commit-message shape, commit-failure handling | Commit conventions |
| Index hygiene when agents share a worktree | Parallel-agent commit safety |
| Why these gates exist | Rationale |

Optional argument — title.

## Step 1 — confirm the work satisfies the DoD

Read the card by running `goc show <title>` yourself with the real
title bound. Re-confirm each DoD criterion against the actual work:

- `- [ ] reproduce.py exits zero (defect no longer fires)` — run
  `uv run python deck/<title>/reproduce.py`, confirm exit 0 with the
  no-defect output.
- `- [ ] <metric assertion>` — run the relevant pytest / sweep and
  capture the verification number.
- Doc-quality criteria — re-read the cited paper / axiom and confirm
  the doc now aligns.

If any criterion is NOT actually satisfied, **stop the closure**: a
failed fix attempt → revert, append a `## Disproved fix attempt`
section to `deck/<title>/log.md`, leave status `active` or re-`open`
via the `advance-card` skill; a disproved hypothesis → divert to
the `advance-card` skill (with `<title> disproved`).

## Step 2 — project-specific closure audit

Closure must align with the consuming repo's documented principles,
not just pass tests — a green fix can still encode a default the
project disagrees with. The audit makes the closer name *which*
principle the closure aligns with, or honestly record that none is
touched.

`cat .game-of-cards/hooks/finish-card.md 2>/dev/null || true`

If the hook above defines a closure-audit rubric, follow it, then
write the outcome into the Step 4 `log.md` entry as exactly ONE of:

- **`<rubric-name> audit: PASS — invokes <principle> + <primary source>`**
- **`<rubric-name> audit: PASS — no principle touched, mechanical fix`**
  (be honest — if the fix binds *any* principle, name it instead)

If the audit FAILS — the fix encodes a default the rubric disagrees
with, masks a missing concept, or contradicts a documented principle —
STOP the closure: redesign the fix to align (preferred), or divert to
the `advance-card` skill (with `<title> open`) and append an `## audit failed`
section to `log.md`. If no rubric is defined (hook absent or empty),
record "no rubric configured; mechanical fix" verbatim.

No per-card DoD checkbox is required for the audit — it is a workflow
gate on every closure; the closure log entry is the audit trail.

## Step 3 — tick the DoD checkboxes (update the dashboard)

Edit `deck/<title>/README.md` and mark each criterion `- [x]`. The
README is the **dashboard**: if the body's "Fix" or "Empirical
evidence" sections still reflect the pre-resolution framing, rewrite
them in place to describe the *applied* fix and final measurement.
Do NOT append a "Resolution (DATE)" block below the original framing
— the journal entry in Step 4 captures the transition (see
the `card-schema` skill "What goes where").

If the fix added a sub-criterion the original DoD didn't anticipate,
add a new ticked box and note in the body why. If a criterion turned
out to be moot, strike it from the DoD with a one-line justification
rather than ticking it falsely.

## Step 4 — append closure context to `log.md` (the journal)

`log.md` is the **append-only journal** — never rewrite existing
entries; the closure entry is one more entry at the bottom:

```markdown
## YYYY-MM-DDTHH:MM:SSZ — Closure

- **What changed**: <file:line> — <one-line essence>
- **Verification**: <one or two key numbers>
- **Audit**: PASS — <principle + primary source> | PASS — no principle touched, mechanical fix
- **Project impact**: <project-defined dashboard line, or "n/a">
- **Tests**: <count> passed / <count> failed / <count> xfailed
- **Bundled with**: <title-A>, <title-B> (if any)
```

The timestamp is ISO 8601 UTC. (`goc attest`'s closure-marker check
date-prefix-matches, so legacy date-only headers keep validating.)

## Step 5 — record the Closure verification (`goc attest`)

```bash
goc attest <title>
```

`attest` runs every project-wide (layer-2) and GoC-wide (layer-3)
check from `.game-of-cards/config.yaml` — automated subprocesses
(pytest, ruff, `goc validate`), derived card-state checks (DoD %,
`advanced_by` closure, closure-entry grep), and interactive
manual / agent confirmations — then appends a "Closure verification"
block to `log.md`. On any failure it exits non-zero and closure
blocks: fix the failing check and re-run. No waivers.

- `--skip <name>` records `[~] SKIPPED` for one genuinely flaky
  check — last resort, never routine (`reference.md` § Attest details
  and skip policy).
- An `advanced-by-closed` FAIL means a card in `advanced_by` is still
  open: either wait for it to close, or retract a false edge with
  `goc unadvance <closing-title> --by <upstream-title>`. Do NOT
  `--skip` past it — see `reference.md` § Retraction vs waiting.

## Step 6 — close via the CLI

```bash
goc done <title>
```

Refuses (exit 2, `ERROR: <title>: <n> unchecked DoD boxes`) while any
box is unchecked. On success sets `status: done` + `closed_at` and
prints `<title>: open → done`.

- `done` does NOT auto-commit — the closure flip ships with the work
  commit in Step 8, not as a state-only commit.
- A free-form prose DoD (zero checkboxes) needs `--force`; prefer
  adding checkboxes.
- One fix resolving several cards → `goc done --bundle <A> <B> …`
  writes one shared attestation and cross-referenced closure entries;
  read `reference.md` § Bundled closures before first use.

## Step 7 — project-specific post-close action

If the hook file loaded in Step 2 also defines a post-close action (a
status-dashboard refresh, a changelog row, a release-notes entry),
run it now; otherwise this step is a no-op. Step 2 and this step
deliberately share the one hook file
(`.game-of-cards/hooks/finish-card.md`) — the consuming repo authors
both rubrics together.

## Step 8 — commit or hand off

Follow the hook's commit flow if it defines one; otherwise use the
runtime's normal commit workflow. The final commit ships the **work**:
the code/doc diff plus the closure transition (DoD ticks, log entries
from Steps 4 + 5, `status: done`). Claim/decide/advance flips usually
committed earlier under `workflow.auto_commit`.

On a shared worktree, guard the index (rationale in `reference.md`
§ Parallel-agent commit safety):

```bash
git diff --cached --name-only   # foreign staged files? another agent is mid-commit — back off
git add <path>...               # explicit paths only — never `git add .` / `git add -A`
git diff --cached --stat
git commit -- <path>...         # pathspec confines the commit to this closure's files
```

Never use `git stash`, `git restore`, `git checkout --`,
`git reset --hard`, or `git clean` as a commit-isolation technique.

Subject shape: `fix(<scope>): <one-line subject> — closes <title>`
(bundled closures append more slugs); body carries the WHY plus
verification numbers. Full conventions and commit-failure handling:
`reference.md` § Commit conventions.

## Cross-references

- `reference.md` (this skill's directory) — every edge case routed in
  the table above.
- the `card-schema` skill — DoD format + free-form-prose escape.
- the `advance-card` skill — divert for `→ disproved` or re-`open`.

## Sibling files on this host

This skill ships `reference.md` alongside its body. If a direct file read fails (sandboxed sessions cannot see the plugin install path), fetch the file through the goc tool: `{verb: "skill", args: ["finish-card", "<file>"]}`.
