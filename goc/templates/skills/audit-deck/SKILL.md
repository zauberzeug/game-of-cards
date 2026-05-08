---
name: audit-deck
description: Hunt for one previously-undocumented defect, derivation gap, doc drift, missing test or wrong concept. Also architectural ugliness, code smells and inconsistencies. Files via Skill(create-card). AUTO-INVOKE when user says "find me a bug", "audit X", "check for inconsistencies", "what could be wrong", "hunt for issues", "scan the codebase", "look for gaps", or invokes /audit-deck. Treats nothing as truth — inconsistencies are the primary lead (XP spike + Scrum backlog refinement).
argument-hint: optional area filter within the project (consuming repo defines its default scope in `.game-of-cards/hooks/audit-deck.md`)
---

## Preflight

If any `!` block below shows `goc: command not found`, `Permission for this action has been denied`, or `no such file or directory: .game-of-cards/deck/`, **stop and invoke `Skill(kickoff)` first**. Kickoff detects which setup step is missing (CLI not installed, Bash allowance not granted, project state not scaffolded) and walks the user through it. Re-invoke this skill only after kickoff completes.

## Context (read but distrust — these are hypotheses, not ground truth)

!`goc`

!`goc --done`

!`goc --status disproved`

!`goc --tag unverified`

!`cat .game-of-cards/hooks/audit-deck.md 2>/dev/null || true`

# Audit

XP's **spike** (Beck, 1999) plus Scrum's **backlog refinement**: the
deck only contains what we've already noticed. Every iteration must
close the gap between what's known and what's documented — otherwise
the read-pattern guarantee silently rots as code drifts away from the
filed cards. Treat nothing as truth — neither code, comments, docs,
nor the deck itself; **inconsistencies and contradictions are the
primary lead**.

Find one previously-undocumented defect — bug, derivation gap, doc
drift, missing test, wrong concept, architectural ugliness, code
smell, or inconsistency — and file it via `Skill(create-card)`.
"Ugly architecture" (mechanism in the wrong module, modules that
must be detached together, double-counted concerns, five special
cases hiding one rule) signals a missing abstraction and counts as
a defect. "I looked and didn't find anything" is a failure mode,
not an acceptable outcome.

User argument: $ARGUMENTS — if non-empty, narrow within the
default scope (the consuming repo defines this in
`.game-of-cards/hooks/audit-deck.md`). Out-of-scope arguments are
flagged and ignored.

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
- **Hunt the big thing first.** Impact ladder: `high` outranks
  `medium` outranks `low`. Doc claims that contradict an
  authoritative source are `contribution: high` + `tags: [documentation]`,
  NOT low.
- **File every confirmed defect regardless of queue depth.** Queue
  length is a transparency signal, not backpressure.
- **Flag, don't fix.** This skill ships a documented defect, not
  a patch.

The bullets above are for _rapid hunt triage_. When a candidate
touches a substantive design decision (mechanism choice, sign
convention, default anchored to a project principle) — and
especially when the right gate for the new card is unclear —
consult the consuming repo's project-specific rubric (wired in via
`.game-of-cards/hooks/audit-deck.md`, loaded above). The rubric
often reveals that what looks like a fresh decision is already
determined by an existing principle + primary source, in which case
the card can be filed with `--gate none` and a `## Decision
(rubric-derived)` body section (see `Skill(create-card)` Step 3).
Keeps the human out of the loop when project-specific reasoning is
decisive.

## Phase 1 — Probe (run BEFORE static hunting)

Static analysis converges to "no new defect" within ~5 rounds.
Behavioral defects — NaN/Inf, divergence, silent boundary-state
corruption — require running the actual project. Run the probe AND
doc-quality hunters concurrently; the probe is I/O-bound and the
doc hunters have no probe dependency.

The consuming repo defines its probe recipe in
`.game-of-cards/hooks/audit-deck.md` (already loaded above).
Typical probes:

- **Metrics probe (steady-state):** run the canonical demo / test
  suite for a few seeds in parallel; compare to a baseline metrics
  table; flag divergence ≥ 2σ as a candidate.
- **Boundary-exercise probe:** snapshot state, hit reset / freeze /
  checkpoint surfaces, diff. Silent state-leaks live here.
- **Introspection-trace probe:** run any project-specific trace
  tool, triage `[FAIL]` / `nan` / `inf` / discontinuity hits.

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
3. **Hand to `Skill(create-card)`** for the actual filing
   (title, scaffold, body, DoD, `reproduce.py`).
4. **Sibling sweep after confirmation.** Grep for the same
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

The only escape valve: agent claim that's clearly hallucinated
(file path doesn't exist, symbol doesn't appear via `grep`) AND
has no underlying substance can be silently dropped.

This rule applies even when the round produces a confirmed
defect. The "zero confirmed → ≥1 unverified" rule is the
_minimum_; this is the _maximum-amnesia bound_.

If zero confirmed defects after a round, restart Phase 2 with
different agents and seams. After the restart: if still zero, the
round must produce ≥1 unverified entry before reporting empty.

## Phase 4 — Commit

When all `deck/<title>/` dirs (filed + disproved + unverified) are
written, commit them according to the consuming repo's normal commit
workflow and any GoC hook it defines. The deck-validate hook rejects
schema violations.

### Canonical commit subject

Every audit-deck commit uses:

```
new card: <one-line description of the finding(s)>
```

Detail (contribution, tags, agent attribution) goes in the commit body,
not the subject. The subject must NOT contain iteration counters,
round labels, absolute dates, or trigger-mode tags. The git log
itself records timestamps; the subject doesn't need to.

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
