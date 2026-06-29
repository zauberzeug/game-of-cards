---
name: create-card
description: "File a new card with frontmatter and a DoD scaffold (reproduce.py is authored by hand in Step 6 for bug-class cards, not scaffolded by the tool). AUTO-INVOKE when user says \"let's do X\", \"implement Y\", \"fix Z\", \"add support for\", \"I want to\", \"we need to\", describes a bug, requests a feature, or initiates ANY persistent work item. The card is filed BEFORE implementation — the body is the briefing the next reader (human or AI agent) needs to act cold. Title must be user-facing, descriptive, PO-readable (not engineer's jargon)."
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


## Preflight

If any `!` block below shows `goc: command not found`, `Permission for this action has been denied`, or `no such file or directory: .game-of-cards/deck/`, **stop and invoke `Skill(kickoff)` first**. Kickoff detects which setup step is missing (CLI not installed, Bash allowance not granted, project state not scaffolded) and walks the user through it. Re-invoke this skill only after kickoff completes.

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
`csv-export-button-truncates-rows-over-10000`, `auth-cookie-expires-too-soon`,
`test-zero-w-prediction-tautology-compares-identical-graphs`.

`goc new` enforces a **title-antipattern guard** at filing time
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

Verify it doesn't already exist by running `goc show <your-title>`
yourself with the candidate title bound. Existence (frontmatter dump
returned) → pick a different title. Non-existence (`ERROR: ... not
found`) → safe to proceed.

## Step 2 — dedup against open / done / disproved queues

Same root cause as an existing card = supporting evidence on that
card's body + a `log.md` appendage on the existing entry, NOT a new
filing. Grep for the candidate's identifying string yourself, e.g.
`goc --status all | grep -i <fragment>` with `<fragment>` replaced
by a distinctive substring of the candidate title.

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
  --tag <area-tag> \
  --advances <target-title> \
  --advanced-by <parent-title> \
  --commit
```

The CLI creates `deck/<title>/README.md` with valid flat frontmatter
and a placeholder `- [ ] (replace with real criteria)` DoD, plus an
empty `deck/<title>/log.md`. Tags must come from the canonical set
(see `Skill(card-schema)`); the CLI rejects unknowns.

**Need a new grouping tag?** Project-local tags (domain vocabulary,
sub-project names, cluster groupings — e.g. when filing a card whose
governing peer wants a shared epic tag) are added in
`.game-of-cards/canonical-tags.md` under a fenced `canonical_tags:`
YAML block; `goc validate` merges it into the enum on every run. A
tag that should ship with goc itself goes through a PR. See
`Skill(card-schema)` "Adding new tags" for the predicates that decide
when a new tag is warranted vs. an existing one fits.

When the value-flow relationship is known at filing time, pass
repeatable `--advances` / `--advanced-by` flags so `goc new` writes
both sides of the edge in one command, and pass `--commit` so the
new card directory and the wired endpoints land in a single atomic
commit. Without `--commit`, the edge mutation on the existing
endpoint lingers in the worktree as ambient ` M`; an agent that
then commits only the new card directory (per AGENTS.md's
explicit-pathspec rule) ships a half-edge. Use the older `goc new`
then `goc advance` two-step only as a fallback for adding edges to
an existing card or when the relationship is discovered after
creation.

**Edge direction for coordinating cards (the three-way fork).** When
the card you're filing coordinates other work, decide which of three
shapes you're authoring before reaching for `--advances`. See
`Skill(card-schema)` "Coordinating cards — aggregation epic vs
governing cluster" for the full rules; the short form:

- **Aggregation epic** (its value chain *is* its children; closes
  when they close) → `child.advances: [epic]`. The child contributes
  upward; the epic aggregates downward via `advanced_by`. Concretely
  on a child filing: `goc new <child> --advances <epic> --commit`.
- **Governing cluster** (a decision or standard-setting card that
  closes when *decided*, independent of the cluster's work) → a
  **shared tag**, no `advances` edge in either direction. Add the
  tag via `--tag <epic-grouping-tag>` on both the governing card and
  its instances.
- **Never** `epic.advances: [children]` (backwards). It defeats the
  value law and trips a spurious `advanced-by-closed` FAIL on every
  child at attest time. `goc validate` emits a
  `BACKWARDS_EPIC_EDGE` advisory hint when this signature appears.

The tell: if the coordinating card itself has `--gate decision` or
otherwise closes on its own deliverable rather than on its cluster's
completion, it's a governing cluster → use a tag, not an edge.

**The scaffold is born a draft.** `goc new` stamps `draft: true`, so the
fresh card is hidden from the queue (`goc`, `goc next`) and protected from
dedup/supersede automation until it is authored — Steps 5–7 below. The flag
clears automatically when you claim the card (`goc status <title> active`,
the usual next step) or close it; release an authored-but-unclaimed card to
the queue explicitly with `goc publish <title>`. This closes the window where
a half-written scaffold could be superseded as a "duplicate" on its title
alone. See `Skill(card-schema)` "Draft" for the full contract.

## Step 5 — write the body (the dashboard)

The README body is the card's **dashboard**: a snapshot of latest
knowledge and current state. As understanding evolves between rounds
of work, **rewrite these sections in place** — replace the old
problem framing, update the fix proposal, refine the DoD. Do NOT
append a "Latest finding (DATE)" block at the bottom; that turns the
README into a stale ledger a future reader has to date-sort by eye.
History, decisions, and per-round details belong in `log.md` (the
journal). See `Skill(card-schema)`'s "What goes where" subsection.

Edit `deck/<title>/README.md` and replace the placeholder body with
the dashboard sections — problem framing, current understanding, fix
proposal, DoD:

- **Title (H1)** — one-line description.
- **Summary** — populate the frontmatter `summary:` field (≤ 3
  sentences, what + why) so triage views can scan without opening.
- **Location** — `file:line` for the offending code (bug-class) or
  doc/section (doc-class).
- **What's broken / what's missing** (problem framing) — prose with
  **quoted code AND quoted contradicted doc/comment**. Don't
  paraphrase — the reader needs to see the conflict with their own
  eyes. Rewrite as the framing sharpens.
- **Empirical evidence** (current understanding) — paste the
  `reproduce.py` output verbatim (after Step 6). Replace with the
  latest run when the evidence changes.
- **Why it matters** — connect to a real symptom (an unexplained
  drift, a Sprint that "tied" unexpectedly, a metric that
  plateaus). Cross-link other cards as `[<title>](../<title>/)`.
  **For parser / emitter / serializer / storage-layer defects, name
  the reachability path that produces the offending input** — e.g.
  "the frontmatter emitter at `engine.py:NNN` writes this string when
  a card has `closed_at: null`," or "a one-shot-authored card supplied
  this header verbatim," or the concrete consumer flow (`goc done →
  finish-card sync → ...`). Reachability is what separates a real
  defect from a theoretical one; without it, a reader six months
  later cannot tell whether the affected shape is actually produced
  in shipping or only hypothetically possible.
- **Fix** (fix proposal) — concrete code change with file:line. **Do
  NOT apply the fix.** When the gate is `decision`, this collapses
  into the `## Decision required` section. Rewrite the proposal as
  the chosen approach changes; record the pivot reasoning in
  `log.md`.
- For `--gate decision` / `--gate session` cards, consider a sibling
  `*.html` matrix, `*.svg` diagram, or interactive form (see Step 7).
- **Refine the DoD** — replace the placeholder with real criteria.
  Each box is a contract the fix must satisfy. Prefix each item with
  its method class (`TDD:` / `EMPIRICAL:` / `MECHANICAL:` / `PROCESS:`)
  so the closure semantic is legible — see `Skill(card-schema)`
  "DoD method tags". Prefer `TDD:` whenever a closed-form expected
  value exists:

  ```yaml
  definition_of_done: |
    - [ ] TDD: reproduce.py exits zero (defect no longer fires)
    - [ ] TDD: <specific assertion or metric the fix must satisfy>
    - [ ] EMPIRICAL: <if a sweep/A-B: experiment run, verdict recorded in log.md either way>
    - [ ] MECHANICAL: <if a doc/config edit: the edit landed and reads correctly>
    - [ ] PROCESS: <if a decision/cross-ref: agreement recorded, parent advanced_by updated>
  ```

Each round of work on the card updates the README dashboard *and*
appends a journal entry to `log.md` recording what changed and why.

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

## Step 7 — ship rich artifact files (optional, any card class)

When the body benefits from content markdown can't express — colored
option grids, state-machine diagrams, side-by-side visual
comparisons, interactive answer forms for `human_gate: decision`
cards — ship the artifact as a sibling file in the card directory
and reference it from the body. Same bundle shape as `reproduce.py`
for bug cards; the engine treats sibling files as opaque and never
parses them.

```
deck/<title>/
  README.md                       # narrative + links to artifacts below
  log.md
  reproduce.py                    # OPTIONAL — bug-class executable proof
  comparison-matrix.html          # OPTIONAL — colored option grid
  state-diagram.svg               # OPTIONAL — vector diagram
  decision-form.html              # OPTIONAL — interactive answer form for a decision gate
  before-after-screenshot.png     # OPTIONAL — visual regression evidence
```

The README links artifacts as `[See the comparison
matrix](comparison-matrix.html)`. GitHub renders the README inline;
clicking a `.html` link shows source on github.com but opens as a
working page when viewed locally — identical UX github.com gives
any binary asset.

Use this pattern when:

- A decision card carries a colored options matrix that degrades to
  a wall of text in markdown.
- A `human_gate: decision` card ships an interactive form the human
  fills in (open the `.html` in a browser, fill it, paste the
  result back into the README's decision section).
- The card carries a state diagram, an `advances`-graph snapshot,
  or any visual that needs spatial layout markdown can't give.

Skip this pattern when prose alone communicates the content. The
default card stays single-file (`README.md` + `log.md`); rich
artifacts are an opt-in escape hatch, not a requirement. There is
no `body_format:` schema field and no engine dispatch — every
artifact is just another file in the card directory.

## Cross-references

- `Skill(card-schema)` — field semantics, enum values, canonical
  tags, decision-gate body contract.
- `Skill(scan-deck)` — dedup queries for the open / done / disproved
  queues.
- `Skill(advance-card)` — if the body reveals the gate should be
  different than what you scaffolded with.
- Project commit workflow — when the body, DoD, and `reproduce.py`
  are written, commit the filing according to the consuming repo's
  normal checks and any GoC hook it defines.
