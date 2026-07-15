---
name: audit-deck
description: "Hunt for one previously-undocumented defect, doc drift, missing test, or inconsistency; file it via Skill(create-card). AUTO-INVOKE on \"find me a bug\", \"audit X\", \"check for inconsistencies\", or /audit-deck. Inconsistencies are the primary lead."
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

Invoke when the user says "find me a bug", "audit X", "check for inconsistencies", "what could be wrong", "hunt for issues", "scan the codebase", "look for gaps", or invokes /audit-deck. Also covers architectural ugliness, code smells, and inconsistencies (XP spike + Scrum backlog refinement).

## Preflight

If any `!` block below shows `goc: command not found`, `Permission for this action has been denied`, or `no such file or directory: .game-of-cards/deck/`, **stop and invoke `Skill(kickoff)` first**. Kickoff detects which setup step is missing (CLI not installed, Bash allowance not granted, project state not scaffolded) and walks the user through it. Re-invoke this skill only after kickoff completes.

## Context (read but distrust — these are hypotheses, not ground truth)

!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b; else goc; fi 2>&1 || true`

!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b --done; else goc --done; fi 2>&1 || true`

!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b --status disproved; else goc --status disproved; fi 2>&1 || true`

!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b --tag unverified; else goc --tag unverified; fi 2>&1 || true`

!`cat .game-of-cards/hooks/audit-deck.md 2>/dev/null || true`

# Audit

Find one previously-undocumented defect — bug, derivation gap, doc
drift, missing test, wrong concept, architectural ugliness, code
smell, or inconsistency — and file it via `Skill(create-card)`.
Treat nothing as truth; **inconsistencies and contradictions are the
primary lead**, and "I looked and didn't find anything" is a failure
mode, not an acceptable outcome.

User argument: $ARGUMENTS — if non-empty, narrow within the
default scope (the consuming repo defines this in
`.game-of-cards/hooks/audit-deck.md`). Out-of-scope arguments are
flagged and ignored.

**Long-form material lives in `reference.md`** — a sibling file in
this skill's directory. Read the named section only when the
situation actually applies:

| Situation | `reference.md` section |
|---|---|
| Why the audit exists; what counts as a defect | Rationale |
| No probe configured; need probe ideas | Typical probe recipes |
| A candidate touches a design decision / unclear gate | Consulting the project rubric |
| Filing a parser/emitter/serializer defect | Reachability paths |
| A round ends with unfollowed or zero candidates | Park-or-disprove: bounds and escape valve |
| Writing the commit | Canonical commit subject |

## Mindset (compressed)

- **Code is suspect first; documentation second.** When code and
  the project's stated principles disagree, the default presumption
  is the code drifted. Documentation is the target the code is
  meant to approximate; the consuming repo's hook (above) names the
  doc surfaces that count as ground truth.
- **Empirical or it didn't happen.** Every reported defect needs
  evidence — no "I think this might be." For behavioral defects
  (bugs, derivation gaps, missing tests), evidence is a
  `reproduce.py` that prints output proving the defect. For
  structural defects (architectural ugliness, code smells, doc
  drift, inconsistencies), evidence is the citation set: every
  duplicated site, every contradicting passage, every contract
  violation, quoted with file:line. Either form is concrete; "it
  feels off" is not.
- **Disproved dedup before filing.** Grep
  `goc --status disproved` for the candidate's
  identifying string. Re-promote only with new evidence (cited
  code changed since the rebuttal date).
- **Hunt the big thing first.** Contribution ladder: `high` outranks
  `medium` outranks `low`. Doc claims that contradict an
  authoritative source are `contribution: high` + `tags: [documentation]`,
  NOT low.
- **File every confirmed defect regardless of queue depth.** Queue
  length is a transparency signal, not backpressure.
- **Flag, don't fix.** This skill ships a documented defect, not
  a patch.

When a candidate touches a substantive design decision or the right
gate is unclear, consult the project rubric first —
`reference.md` § Consulting the project rubric.

## Phase 1 — Probe (run BEFORE static hunting)

Static analysis converges to "no new defect" within ~5 rounds.
Behavioral defects — NaN/Inf, divergence, silent boundary-state
corruption — require running the actual project. Run the probe AND
doc-quality hunters concurrently.

The consuming repo defines its probe recipe in
`.game-of-cards/hooks/audit-deck.md` (already loaded above); generic
probe shapes in `reference.md` § Typical probe recipes.

Triage:

- Probe surfaces NaN/Inf, out-of-range metric, state-leak diff, or
  a project-specific `[FAIL]` marker: that's the primary lead.
  Skip Phase 2, go to Phase 3 (file).
- Probe suggestively close to a documented bound: record as
  `tags: [unverified]` with a sweep recipe.
- Probe clean (or no probe configured): proceed to Phase 2 static
  hunting.

## Phase 2 — Hunt (parallel agents in a single message)

The consuming repo defines its hunter roster in
`.game-of-cards/hooks/audit-deck.md` (already loaded above) — which
specialized agents to spawn for which scopes, and which surfaces
each is briefed against.

If no hunter roster is configured, default to spawning ONE
`general-purpose` agent with the user's scope and the briefing
items below — every Claude Code installation has this agent
available.

Brief each agent with:

1. The catalog floor — point at the goc CLI queries for
   `open` / `done` / `disproved` / `unverified`. Agents should
   `goc show <title>` for full READMEs of specific entries.
2. The user's scope.
3. Mindset: prioritize `contribution: high` (structural /
   algorithmic) over `contribution: low` (text-rot).
4. Deliverable: top 3 candidates with **file:line** citation, a
   **contribution classification** (high/medium/low) + relevant
   **tags**, and a **falsifiable prediction** about what
   `deck/<title>/reproduce.py` would print.

For model-tier guidance (e.g. mandating `model: "opus"`), see
`.game-of-cards/tooling-conventions.md`.

If a hunter returns three `contribution: low` candidates and no
`high`, send it back with explicit pointers to under-audited
high-impact seams (the integrator, the core update logic, state-
restore paths, default-parameter table, public API contracts).

## Phase 3 — File (one card per confirmed defect)

For each confirmed candidate:

1. **Read the cited code yourself.** Agents hallucinate file:line.
2. **Disproved-dedup grep.** Before drafting `reproduce.py`, grep
   the candidate's identifying string against existing disproved
   bodies. If a rebuttal exists, re-read it.
3. **Name the reachability path in `## Why it matters`.** For
   parser / emitter / serializer / storage-layer defects, name the
   path that produces the offending input — full convention in
   `reference.md` § Reachability paths.
4. **Hand to `Skill(create-card)`** for the actual filing
   (title, scaffold, body, DoD, `reproduce.py`).
5. **Sibling sweep after confirmation.** Grep for the same
   root-cause shape in adjacent modules. File every confirmed
   sibling as a separate card. If the sweep would produce a 4th
   instance of an already-catalogued family, file the
   architectural meta-fix instead.

### Park-or-disprove unfollowed candidates (mandatory)

Each hunter typically returns 3 candidates; you can verify and
file 1–2 in a single round. The remaining candidates MUST go
somewhere durable before commit:

1. **Filed** as a new card via `Skill(create-card)`.
2. **Disproved** via `Skill(advance-card) <title> disproved` — when
   you read the cited code and the claim is wrong on its face.
3. **Unverified** via `Skill(create-card) ... --tag unverified` —
   when the candidate has substance but no `reproduce.py` budget
   this round. Body must include: hypothesis with file:line
   (verbatim quote), why deferred, falsification recipe, agent
   that surfaced it.

This rule applies even when the round produces a confirmed defect;
bounds, the hallucination escape valve, and the empty-round restart
rule are in `reference.md` § Park-or-disprove.

## Phase 4 — Commit

When all `deck/<title>/` dirs (filed + disproved + unverified) are
written, commit them according to the consuming repo's normal commit
workflow and any GoC hook it defines. The deck-validate hook rejects
schema violations. Subject shape: `new card: <one-line description>`
— full rules in `reference.md` § Canonical commit subject.

## Output

Brief summary in chat (≤200 words):

- The new card title(s) (`<title> — <subject>`).
- Where it was found (file:line).
- One verification number from `deck/<title>/reproduce.py`.
- The contradicted doc/comment (quoted, one line).
- Disproved candidates added this run, if any (one-liner each).
- Unverified candidates parked this run, if any.
- The commit hash, if this run created a commit.

Full writeup, code quotes, empirical output, and proposed fix all
live in `deck/<title>/README.md`. Do not duplicate them in chat.

## Cross-references

- `Skill(create-card)` — actual filing (title, scaffold, body, DoD).
- `Skill(advance-card)` — for `disproved` flips during
  verification.
- `Skill(scan-deck)` — dedup queries against existing queues
  (open / done / disproved / unverified).
- `Skill(card-schema)` — DoD format, decision-gate body contract,
  canonical tag predicates.
- Project commit workflow — final checks, staging, and commit.
