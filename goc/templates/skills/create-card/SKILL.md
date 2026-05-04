---
description: File a new card with frontmatter, DoD scaffold, and (for bugs) reproduce.py stub. AUTO-INVOKE when user says "let's do X", "implement Y", "fix Z", "add support for", "I want to", "we need to", describes a bug, requests a feature, or initiates ANY persistent work item. The card is filed BEFORE implementation — the body is the briefing the next reader (human or AI agent) needs to act cold. Title must be user-facing, descriptive, PO-readable (not engineer's jargon).
argument-hint: <title> [--contribution high|medium|low] [--gate none|decision|session] [--tag <canonical-tag>]
---

# File a new card

XP's **story card as conversation** (Beck, 1999): a card is a
self-contained briefing for the next reader — human or agent —
written so the work can be picked up cold. Hallway context evaporates
between /loop iterations and conversational continuity is the first
casualty when a sub-agent reads the card three weeks later. Each card
must therefore carry its own evidence (verbatim quotes, reproducer
output), its own framing (what's broken, why it matters), and its own
closure contract (the DoD).

Scaffold a `deck/<title>/` dir with valid frontmatter, an empty
`log.md`, and a placeholder DoD that `Skill(finish-card)` will refuse
to satisfy until you write real criteria. The CLI guarantees frontmatter
validity; the body is on you.

User argument: $ARGUMENTS

## Step 1 — confirm the title

Slug pattern: `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (per `Skill(card-schema)`).
Short, hyphenated, descriptive. Examples:
`heterosynaptic-ltd-absent-fchannel`, `phantom-contact-motor-mask`,
`test-zero-w-prediction-tautology-compares-identical-graphs`.

`deck.py new` enforces a **title-antipattern guard** at filing time
(see `Skill(card-schema)` "Title antipatterns"): the regex set rejects
`rN` round-references, `path-N` / `phase-N` step-numbers, `bug-N`
tracker-numbering, `_md_` / `_py_` source-file infixes, camelCase
tokens, and math symbols. The error suggests an alternative phrasing
based on the *observable problem*. Pass `--allow-jargon` only for
migration tools.

**Read the slug aloud before scaffolding.** Beyond the antipattern guard,
also avoid:

- **Word stuttering** — same root word repeated three or more times in
  one slug. Bad: `test-at-target-zero-delta-tautology-zero-times-anything-is-zero`
  (three "zero"s pile up; readers parse it twice). Good:
  `test-intrinsic-plasticity-at-target-passes-trivially` (same idea,
  parseable on first read).
- **Colloquial clauses as the back half** — "X-times-anything-is-Y" or
  "passes-because-Z-is-trivially-true" reads like chat sentence, not a
  slug. The defect-shape clause should be a noun phrase a PO could
  read once. Use `passes-trivially`, `compares-identical-graphs`,
  `shadows-substrate-default` — not `is-trivially-zero-anyway`.
- **Family-shape mismatch** — when the card is the Nth instance of a
  known family, match the title shape of existing siblings. If R3 and
  R10 used `test-<name-fragment>-<defect-shape-clause>`, R11 in the
  same family must too. Inventing a new slug shape per instance makes
  the family illegible.

Verify it doesn't already exist:

!`goc show <title> 2>&1 | head -3`

Existence (frontmatter dump returned) → pick a different title.
Non-existence ("ERROR: ... not found") → safe to proceed.

## Step 2 — dedup against open / done / disproved queues

Same root cause as an existing card = supporting evidence on that
card's body + a `log.md` appendage on the existing entry, NOT a new
filing. Grep for the candidate's identifying string:

!`goc --status all 2>&1 | grep -i <near-name-fragment>`

If a `disproved` rebuttal exists for this hypothesis, re-read it
before filing. Re-promote only if `git log -p -- <cited-file>` shows
the cited code has changed since the disproved entry's date.

## Step 3 — pick the gate

The CLI default is `decision`; that is the *fallback* for findings
whose fix path genuinely needs a human pick between alternatives.
When the work shape makes the right gate clear, set it explicitly:

- `--gate none` — fully mechanical: sed-style rename, stale-reference
  patch, single-line constant correction. `Skill(next-card)` can
  recommend it under `/loop` without a checkpoint.
- `--gate decision` — two or more credible fix paths and a human
  must pick. **You MUST then write the `## Decision required`
  section in the body** (per `Skill(card-schema)`'s Decision-gate
  body contract).
- `--gate session` — research-impacting: framework derivation gap,
  mechanism choice between literature alternatives, sign convention,
  new named primitive, default anchored to a paper / axiom.

When in doubt between `decision` and `session`: if recording the
framing in a `## Decision required` section feels like it would
under-serve the question (the options aren't well-scoped yet, or
picking would itself need new evidence), use `session` instead.

### Try the project rubric before defaulting to `decision`

If the card you're filing has a substantive decision at its core
(mechanism choice, sign convention, default anchored to a project
principle), consult the consuming repo's project-specific rubric
*before* picking `--gate decision`.

!`cat .game-of-cards/hooks/create-card.md 2>/dev/null || true`

If the rubric gives a clear answer with a principle citation AND
primary-source backing, scaffold the card with `--gate none` and
pre-write a `## Decision (rubric-derived)` body section recording:

- The choice (one line)
- The principle invoked (citation form prescribed by the hook above)
- The primary-source citation (paper DOI/PMID, textbook chapter, or
  project-doc section)

The card joins the autonomous queue immediately; `pull-card`
implements without waiting on the human. Reserve `decision` /
`session` gates for questions the rubric cannot answer — resource
allocation, scope splits, taste calls, or missing primary-source
evidence.

This is the lazy Andon pattern: try the rubric, then pull. See
`Skill(decide-card)`'s "When an agent invokes this skill" section
for the full contract.

## Step 4 — scaffold via the CLI

```bash
goc new <title> \
  --contribution <high|medium|low> \
  --gate <none|decision|session> \
  --tag bug \
  --tag <area-tag>     # plasticity / fchannel / documentation / etc.
```

The CLI creates `deck/<title>/README.md` with valid flat frontmatter
and a placeholder `- [ ] (replace with real criteria)` DoD, plus an
empty `deck/<title>/log.md`. Tags must come from the canonical set
(see `Skill(card-schema)`); the CLI rejects unknowns.

## Step 5 — write the body

Edit `deck/<title>/README.md` and replace the placeholder body with:

- **Title (H1)** — one-line description.
- **Summary** — populate the frontmatter `summary:` field (≤ 3
  sentences, what + why) so triage views can scan without opening.
- **Location** — `file:line` for the offending code (bug-class) or
  doc/section (doc-class).
- **What's broken / what's missing** — prose with **quoted code AND
  quoted contradicted doc/comment**. Don't paraphrase — the reader
  needs to see the conflict with their own eyes.
- **Empirical evidence** — paste the `reproduce.py` output verbatim
  (after Step 6).
- **Why it matters** — connect to a real symptom (an unexplained
  drift, a Sprint that "tied" unexpectedly, a metric that
  plateaus). Cross-link other cards as `[<title>](../<title>/)`.
- **Fix** — concrete code change with file:line. **Do NOT apply the
  fix.** When the gate is `decision`, this collapses into the
  `## Decision required` section.
- **Refine the DoD** — replace the placeholder with real criteria.
  Each box is a contract the fix must satisfy:

  ```yaml
  definition_of_done: |
    - [ ] reproduce.py exits zero (defect no longer fires)
    - [ ] <specific assertion or metric the fix must satisfy>
    - [ ] <if doc-quality: doc claim aligns with cited literature>
  ```

## Step 6 — write `reproduce.py` (bug-class only)

For bug / measurement / regression class cards, ship a
`deck/<title>/reproduce.py` that, run on a clean checkout, prints
output an outside reader would accept as proof.

The script must use the **parent-walk pattern** to find the repo
root — NOT `parents[N]` with a fixed N. The parent-walk is
path-depth-agnostic and survives directory moves:

```python
import sys
from pathlib import Path

def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")

sys.path.insert(0, str(_repo_root()))
```

Run it via `uv run python deck/<title>/reproduce.py` (per project's
`uv run` discipline). Capture output verbatim into the body's
"Empirical evidence" section.

For plausible-but-unreproduced hypotheses, add `--tag unverified`
and document the falsifying-test recipe in the body. The promotion
rule: drop the `unverified` tag once a working `reproduce.py` lands.

## Cross-references

- `Skill(card-schema)` — field semantics, enum values, canonical
  tags, decision-gate body contract.
- `Skill(scan-deck)` — dedup queries for the open / done / disproved
  queues.
- `Skill(advance-card)` — if the body reveals the gate should be
  different than what you scaffolded with.
- `Skill(prepare-commit)` — when the body, DoD, and `reproduce.py`
  are written, hand to the commit gauntlet to land the filing.
