---
name: create-card
description: File a new card with frontmatter and a DoD scaffold BEFORE implementation — the body is the briefing the next reader needs to act cold. AUTO-INVOKE on "let's do X", "implement Y", "fix Z", a described bug, a requested feature, or ANY new persistent work item.
---

## When to invoke

Invoke when the user says "let's do X", "implement Y", "fix Z", "add support for", "I want to", "we need to", describes a bug, requests a feature, or initiates ANY persistent work item. Title must be user-facing, descriptive, PO-readable (not engineer's jargon). reproduce.py is authored by hand in Step 6 for bug-class cards, not scaffolded by the tool.

# File a new card

A card is a self-contained briefing for the next reader — human or
agent — written so the work can be picked up cold: its own evidence,
its own framing, its own closure contract (the DoD). Scaffold a
`deck/<title>/` dir with valid frontmatter, an empty `log.md`, and a
placeholder DoD that the `finish-card` skill will refuse to satisfy
until you write real criteria. The CLI guarantees frontmatter
validity; the body is on you.

**Edge cases live in `reference.md`** (sibling file in this skill's
directory) — read the named section only when the situation applies:

| Situation | `reference.md` section |
|---|---|
| Slug reads badly aloud | Title quality |
| The card coordinates other cards | Edge direction for coordinating cards |
| A substantive decision at the card's core | Rubric-derived decisions |
| Body needs diagrams / matrices / forms | Rich artifact files |
| Draft-flag lifecycle details | Draft contract |
| Reachability path for parser/emitter defects | Reachability |
| Why cards are written this way | Rationale |

User argument: the user's argument

## Step 1 — confirm the title

Slug pattern: `^[a-z0-9][a-z0-9-]*[a-z0-9]$`. Short, hyphenated, the
*observable problem*, PO-readable — e.g.
`csv-export-button-truncates-rows-over-10000`.

`goc new` enforces a **title-antipattern guard** (see
the `card-schema` skill "Title antipatterns"): it rejects `rN` rounds,
`path-N` / `phase-N` steps, `bug-N` numbering, `_md_` / `_py_`
infixes, camelCase, and math symbols, suggesting a rephrasing from
the observable problem. `--allow-jargon` only for migration tools.
Read the slug aloud — avoid word stutter, colloquial back-half
clauses, and family-shape mismatch (`reference.md` § Title quality).

Verify the title is free by running `goc show <your-title>` yourself:
`ERROR: ... not found` means safe.

## Step 2 — dedup against open / done / disproved queues

Same root cause as an existing card = supporting evidence on that
card's body + a `log.md` appendage on the existing entry, NOT a new
filing. Grep for the candidate's identifying string yourself, e.g.
`goc --status all | grep -i <fragment>`.

If a `disproved` rebuttal exists for this hypothesis, re-read it
before filing. Re-promote only if `git log -p -- <cited-file>` shows
the cited code has changed since the disproved entry's date.

## Step 3 — pick the gate

The CLI default is `decision` — the *fallback* for findings whose fix
path genuinely needs a human pick. When the work shape makes the
right gate clear, set it explicitly:

- `--gate none` — fully mechanical: sed-style rename, stale-reference
  patch, single-line constant correction. Autonomous-loop-safe.
- `--gate decision` — two or more credible fix paths and a human must
  pick. **You MUST then write the `## Decision required` body
  section** (per the `card-schema` skill "Decision-gate contract").
- `--gate session` — research-impacting: framework derivation gap,
  mechanism choice between literature alternatives, sign convention,
  new named primitive, default anchored to a paper / axiom.

When in doubt between `decision` and `session`: if a `## Decision
required` section would under-serve the question (options not yet
well-scoped, or picking needs new evidence), use `session`.

If a substantive decision sits at the card's core, consult the
consuming repo's rubric *before* defaulting to `decision`:

`cat .game-of-cards/hooks/create-card.md 2>/dev/null || true`

If the rubric answers cleanly with a principle citation AND
primary-source backing, scaffold with `--gate none` and pre-write a
`## Decision (rubric-derived)` body section (choice, principle,
citation). Reserve human gates for questions the rubric cannot answer
(`reference.md` § Rubric-derived decisions).

## Step 4 — scaffold via the CLI

```bash
goc new <title> \
  --contribution <high|medium|low> \
  --gate <none|decision|session> \
  --tag bug \
  --tag <area-tag> \
  --advances <target-title> \
  --advanced-by <parent-title> \
  --commit
```

Creates `deck/<title>/README.md` (valid flat frontmatter, placeholder
`- [ ] (replace with real criteria)` DoD) plus an empty `log.md`.
Tags must come from the canonical set — the CLI rejects unknowns;
project-local tags register in `.game-of-cards/canonical-tags.md`
(see the `card-schema` skill "Adding new tags").

- **Known value-flow at filing time** → pass `--advances` /
  `--advanced-by` AND `--commit` so both edge endpoints land in one
  atomic commit (without `--commit`, an explicit-pathspec commit of
  just the new directory ships a half-edge). The `goc new` +
  `goc advance` two-step is the fallback for edges discovered later.
- **Coordinating card?** Aggregation epic (closes when its children
  close) → `child.advances: [epic]`. Governing cluster (closes when
  *decided*) → shared tag, NO edge. Never `epic.advances: [children]`
  (`BACKWARDS_EPIC_EDGE`). Full reasoning: `reference.md` § Edge
  direction for coordinating cards.
- **The scaffold is born `draft: true`** — hidden from queues until
  authored (Steps 5–7). Claiming or closing clears the flag;
  `goc publish <title>` releases an authored-but-unclaimed card
  (`reference.md` § Draft contract).

## Step 5 — write the body (the dashboard)

The README body is the card's **dashboard**: a snapshot of latest
knowledge, rewritten in place as understanding evolves. Do NOT append
"Latest finding (DATE)" blocks — history belongs in `log.md` (see
the `card-schema` skill "What goes where"). Replace the placeholder with:

- **Title (H1)** — one-line description.
- **Summary** — frontmatter `summary:` (≤ 3 sentences, what + why)
  so triage views can scan without opening.
- **Location** — `file:line` (bug-class) or doc/section (doc-class).
- **What's broken** — prose with **quoted code AND quoted
  contradicted doc/comment**; the reader must see the conflict.
- **Empirical evidence** — `reproduce.py` output verbatim (Step 6).
- **Why it matters** — connect to a real symptom; cross-link cards as
  `[<title>](../<title>/)`. For parser / emitter / storage-layer
  defects, name the reachability path that produces the offending
  input (`reference.md` § Reachability).
- **Fix** — concrete change with file:line. **Do NOT apply the fix.**
  For `decision` gates this collapses into `## Decision required`.
  Consider a sibling artifact file for gated cards (Step 7).
- **Refine the DoD** — each box a contract, prefixed with its method
  class (see the `card-schema` skill "DoD method tags"); prefer `TDD:`
  whenever a closed-form expected value exists:

  ```yaml
  definition_of_done: |
    - [ ] TDD: reproduce.py exits zero (defect no longer fires)
    - [ ] TDD: <specific assertion or metric the fix must satisfy>
    - [ ] EMPIRICAL: <experiment run, verdict recorded in log.md either way>
    - [ ] MECHANICAL: <doc/config edit landed and reads correctly>
    - [ ] PROCESS: <agreement recorded, parent advanced_by updated>
  ```

Each later round of work rewrites the dashboard *and* appends a
`log.md` journal entry (what changed, why).

## Step 6 — write `reproduce.py` (bug-class only)

For bug / measurement / regression cards, ship a
`deck/<title>/reproduce.py` that, on a clean checkout, prints output
an outside reader would accept as proof. Find the repo root with the
**parent-walk pattern** — never `parents[N]` with a fixed N:

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

Run via `uv run python deck/<title>/reproduce.py`; paste the output
verbatim into "Empirical evidence".

For plausible-but-unreproduced hypotheses, add `--tag unverified` and
document the falsifying-test recipe in the body; drop the tag once a
working `reproduce.py` lands.

## Step 7 — rich artifact files (optional, any card class)

When markdown can't express the content — colored option grids,
state diagrams, interactive decision forms, screenshots — ship the
artifact as a sibling file in the card directory and link it from the
README (`[See the matrix](comparison-matrix.html)`). Sibling files
are opaque to the engine. Bundle shape, use/skip criteria:
`reference.md` § Rich artifact files.

## Cross-references

- `reference.md` (this skill's directory) — edge cases routed above.
- the `card-schema` skill — field semantics, enums, canonical tags.
- the `scan-deck` skill — dedup queries; the `advance-card` skill — if the
  body reveals a different gate than scaffolded.
- Commit the filing per the consuming repo's normal checks and any
  GoC hook it defines.
