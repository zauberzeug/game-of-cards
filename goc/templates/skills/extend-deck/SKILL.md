---
description: Hunt for one previously-undocumented defect, derivation gap, doc drift, missing test or wrong concept. Also architectural ugliness, code smells and inconsistencies. Files via Skill(create-card). AUTO-INVOKE when user says "find me a bug", "audit X", "check for inconsistencies", "what could be wrong", "hunt for issues", "scan the codebase", "look for gaps", or invokes /extend-deck. Treats nothing as truth — inconsistencies are the primary lead (XP spike + Scrum backlog refinement).
argument-hint: optional sub-path within default scope (docs/ + phasor_agents/ + demos/pong/)
---

## Context (read but distrust — these are hypotheses, not ground truth)

!`goc`

!`goc --done`

!`goc --status disproved`

!`goc --tag unverified`

!`cat docs/framework/vision.md`

!`cat docs/framework/axioms.md`

!`cat docs/framework/architecture.md`

!`cat docs/framework/plasticity.md`

!`cat demos/pong/STATUS.md`

# Hunt

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
default scope (`docs/` + `phasor_agents/` + `demos/pong/`).
Out-of-scope arguments (`paper/`, other demos) are flagged and
ignored.

## Mindset (compressed)

- **Code is suspect first; theory second.** When code and stated
  theory disagree, the default presumption is the code drifted.
  The project's mission is to reverse-engineer biology — the
  theory is the target, the code is the approximation.
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
  `goc/engine.py --status disproved` for the candidate's
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
touches framework derivation, mechanism choice, or deeper
bio-plausibility — and especially when the right gate for the new
card is unclear — invoke `Skill(mindset)` for the full vision /
axioms / plasticity context. /mindset often reveals that what looks
like a research-impacting decision is already determined by an
existing axiom + primary source, in which case the card can be filed
with `--gate none` and a `## Decision (mindset-derived)` body section
(see `Skill(create-card)` Step 3). Keeps the human out of the loop
when bio-faithful reasoning is decisive.

## Phase 1 — Probe (run BEFORE static hunting)

Static analysis converges to "no new defect" within ~5 rounds.
Behavioral defects — NaN/Inf, weight divergence, silent
boundary-state corruption — require running the actual demo.

**Pong is the canonical reference.** Run the probe AND doc-quality
hunters concurrently — the probe is I/O-bound; doc hunters have
no probe dependency.

### Phase A — metrics probe (steady-state)

Write `tmp/grow_deck_probe.py` (Python; tmp/ is gitignored, so
regenerate fresh each round). It should:

1. Build the shipping pong topology + agent (no overrides) and
   step it for ~300 s with 2-3 seeds, parallelized via
   `multiprocessing.Pool` (so it runs in ~5 min wall-clock).
2. Log per-seed: probe_after, late_HR, |W_coupling| max,
   |W_competition| max, any NaN/Inf in `graph._state`, any logged
   warnings, any metric outside the STATUS.md "Latest metrics"
   σ-bands.
3. Compare to STATUS.md and flag divergence ≥ 2σ as a candidate.

Run via `uv run python tmp/grow_deck_probe.py 2>&1 > tmp/probe_out.log`.

### Phase B — boundary-exercise probe

Most recurring family defects live at boundaries — `reset()`,
`frozen_learning()`, checkpoint save/load, `Topology.copy()`.
Phase A doesn't hit these surfaces. Phase B exercises them
explicitly:

1. Build a fresh pong graph, train ~200 s.
2. Snapshot every public state field via reflection.
3. **Reset diff:** call `graph.reset()`, snapshot again. Any field
   that differs but isn't in the documented "reset clears" list is
   a silent-state-leak candidate.
4. **frozen_learning diff:** wrap `graph.step()` × 100 in
   `with graph.frozen_learning():` — any plasticity-class field
   that mutates inside the context is a candidate.
5. **Checkpoint diff:** save + load_into a fresh graph — any field
   that doesn't match is a candidate.

### Phase C — introspection-trace probe

Pong ships `demos/pong/trace_approach.py`:

```bash
uv run python demos/pong/trace_approach.py --seed 42 2>&1 > tmp/trace_fresh.log
```

Triage output: any `[FAIL]` chain check is high-impact (chain
link broken). Any `nan` / `inf` / `±0.0000` in a signal that
should be active is high-impact. Sudden discontinuity in motor /
F-channel / VTA without a court event is a candidate.

### Triage all three phases before spawning hunters

- Phase surfaces NaN/Inf, out-of-range metric, state-leak diff,
  `[FAIL]`: that's the primary lead. Skip Phase 2, go to Phase 3
  (file).
- Phase suggestively close to a documented bound: record as
  `tags: [unverified]` with a sweep recipe.
- All three clean: proceed to Phase 2 static hunting.

## Phase 2 — Hunt (parallel agents in a single message)

Spawn at minimum:

- **`analytical-reviewer`** — primary hunter; finds inconsistency
  between doc and code. Always include.
- **`pr-review-toolkit:silent-failure-hunter`** — error handling,
  catches, silent fallbacks.
- **`Explore`** with `thoroughness: very thorough` — for areas
  the analytical-reviewer hasn't visited.

Add when applicable:

- **`visionary`** — high-impact + `tags: [documentation]` hunter
  for principle / cross-doc / intra-doc claims. Reads
  `docs/framework/*.md` against `axioms.md` and `vision.md` for
  principle violations, cross-doc contradictions, intra-doc
  ambiguity. Always include when scope touches `docs/`.
- **`bio-reviewer` / `neuro-reviewer` / `ml-reviewer`** — for
  docs-vs-literature drift. Brief them with the citation surfaces
  (Frémaux/Gerstner, Schultz, Pathak, Laurent, Fries,
  Deco/Jirsa, Frey/Morris, etc.) and instruct them to actually
  `WebFetch` the cited papers and check the doc's claims against
  the source. **Taking the doc's paraphrase at face value defeats
  the hunt.**
- **`hardcore-tester`** — for tests that pass for the wrong
  reason.
- **`substrate-reviewer`** — when the defect might be "this isn't
  really using the phasor substrate as documented."
- **`creative-cs`** — for architectural ugliness: five special
  cases hiding one rule, mechanisms in the wrong module, modules
  that must be detached together. The pattern-collapsing hunter.
- **`pragmatic-engineer`** — for code smells: duplicated logic,
  defensive scaffolding around a hidden bug, abstraction that
  pays no rent, cross-cutting concerns smeared across modules.

Brief each agent with:

1. The catalog floor — point at the deck CLI queries for
   `open` / `done` / `disproved` / `unverified`. Agents should
   `deck.py show <title>` for full READMEs of specific entries.
2. The user's scope.
3. Mindset: prioritize `contribution: high` (structural / algorithmic)
   over `contribution: low` (text-rot).
4. Deliverable: top 3 candidates with **file:line** citation, an
   **contribution classification** (high/medium/low) + relevant **tags**,
   and a **falsifiable prediction** about what
   `deck/<title>/reproduce.py` would print.

Use `model: "opus"` per project CLAUDE.md.

If a hunter returns three `contribution: low` candidates and no `high`,
send it back with explicit pointers to under-audited high-impact
seams (the integrator, plasticity update equations, state-restore
paths, default-parameter table, public API contracts).

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
written, invoke `Skill(prepare-commit)`. Let the gauntlet run; the
deck-validate hook rejects schema violations.

### Canonical commit subject

Every extend-deck commit uses:

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
- The commit hash from `Skill(prepare-commit)`.

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
- `Skill(prepare-commit)` — final gauntlet.
