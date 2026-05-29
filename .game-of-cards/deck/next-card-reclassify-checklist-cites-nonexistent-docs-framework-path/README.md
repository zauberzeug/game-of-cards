---
title: next-card-reclassify-checklist-cites-nonexistent-docs-framework-path
summary: "`next-card`'s 'Reclassify after reading' checklist tells the agent to consider whether a fix would 'Close (or reopen) a gap in `docs/framework/*.md`' — a concrete path that doesn't exist in goc's own dogfood repo and isn't shipped to any consumer. It's residue from when goc was hosted inside a research-framework repo; the audit catalogue for the package-extraction work explicitly notes these framework docs as project-specific. A reader landing on this line in a generic consumer repo has no `docs/framework/` to act on, and the bullet's signal (literature-anchored design doc; bump the gate) is lost."
status: open
stage: null
contribution: medium
created: "2026-05-29T13:17:07Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] PROCESS: human picks fix path A (delete) or B (generalize); decision recorded in body
  - [ ] MECHANICAL: `goc/templates/skills/next-card/SKILL.md:117` edited per the chosen path
  - [ ] MECHANICAL: `python scripts/sync_plugin_assets.py` regenerates `.claude/skills/`, `.codex/skills/`, `claude-plugin/skills/`, `codex-plugin/skills/` mirrors; `--check` exits zero
  - [ ] MECHANICAL: `python scripts/port_skills_to_openclaw.py` re-ports the openclaw skill; `--check` exits zero
  - [ ] PROCESS: `uv run goc validate` clean
---

# next-card-reclassify-checklist-cites-nonexistent-docs-framework-path

## Location

- `goc/templates/skills/next-card/SKILL.md:117` — the "Reclassify after reading" checklist's first bullet:

  ```
  - Close (or reopen) a gap in `docs/framework/*.md`.
  ```

- Auto-synced mirrors carry the same line:
  - `.claude/skills/next-card/SKILL.md:117`
  - `.codex/skills/next-card/SKILL.md:117`
  - `claude-plugin/skills/next-card/SKILL.md:117`
  - `codex-plugin/skills/next-card/SKILL.md:117`
  - `openclaw-plugin/skills/next-card/SKILL.md` (hand-ported via `scripts/port_skills_to_openclaw.py`)

## What's broken

The five surrounding bullets are project-shape-agnostic — they name *kinds* of moves (pick a mechanism between two literature candidates, set a sign convention, introduce a new primitive, flip a paper-anchored default, update a publication-tier claim). They read sensibly in any consuming repo.

This bullet is the odd one out: it names a **concrete path** (`docs/framework/*.md`) that does not exist in:

- the goc dogfood repo (no `docs/` directory at all — `find . -maxdepth 3 -path '*/docs/framework'` returns nothing);
- the install templates (`goc install` writes `AGENTS.md`, `CLAUDE.md`, `.game-of-cards/`, `.claude/skills/`, `.claude/hooks/` — no `docs/framework/`);
- the shipped plugin payloads (claude / codex / openclaw — same set as install).

The path is residue from goc's pre-extraction life inside the phasor research-framework repo. The package-extraction audit catalogue calls this out explicitly:

> `docs/framework/*.md` — phasor's framework docs aren't shipped by goc. Goc-shipped skills *read* them (`!`cat docs/framework/axioms.md``); the `!`cat`` paths move to `hooks/<skill>.md` (Category 1 + Category 7).
> — `.game-of-cards/deck/package-pyproject-and-pypi-release/audit_catalogue.md:275`

That audit migrated the `!`cat docs/framework/...`` priming reads in `extend-deck/SKILL.md` into project-local hooks correctly. The same audit (line 166) flagged `next-card/SKILL.md:3,25,50,51,102` for similar rewording — but line 117 in today's file (post-rename / re-ordering) was either missed or regressed in a later edit. The prescriptive path is still in the goc-shipped template.

## Why it matters

`next-card` is the autonomous-loop picker. Every `/loop pull-card` invocation reads this skill body. The "Reclassify after reading" checklist is the agent's guard against working a `human_gate: none` card whose body reveals it's actually a research-impacting move — the agent re-reads the body, mentally runs this checklist, and (if any item fires) recommends escalation via `advance-card`.

For consuming repos with no `docs/framework/` directory (the default everywhere — goc itself, the package's own dogfood, any non-phasor adopter), the first bullet either:

- gets pattern-matched as "edits any docs directory" and over-fires (every doc-touch card escalates), or
- gets ignored as inapplicable and silently downgrades the checklist's perceived authority (if one bullet is stale, the agent learns to discount the whole list).

Either failure mode reduces the autonomy gate's value. The other five bullets carry the same signal in a path-agnostic form ("Pick one of two literature-backed mechanism candidates", "Flip a default whose rationale is documented against a paper or axiom") — the docs-path bullet is the only one that ties the checklist to a specific consumer's directory shape.

Reachability: every `Skill(next-card)` invocation loads this body. `/loop pull-card`, `goc --ready`-driven sessions, and human `/next-card` calls all read the line. There is no gated path; the prescriptive string is shipped to every install.

## Decision required

**Two plausible fix paths:**

### A. Delete the line outright

Remove bullet 117 entirely. The remaining five bullets already cover the spirit (literature-anchored design docs, paper-anchored defaults, publication-tier claims). The checklist stays research-flavored but stops naming a specific path.

- **Pro:** smallest diff, no residual project-shape assumption, no consumer confusion.
- **Pro:** clean precedent for future audits of generic-vs-project-specific guidance.
- **Con:** loses the explicit "doc-file gap" framing — readers who don't read the other bullets as "this is doc-file work too" might miss the trigger when the fix shape is purely a doc rewrite.

### B. Generalize the line

Rewrite as a path-shape-agnostic bullet, e.g.:

```
- Close (or reopen) a gap in a literature-anchored design or framework
  doc (whatever path your repo uses for primary-source references).
```

- **Pro:** keeps the explicit doc-class trigger; matches the path-agnostic style of the other five bullets.
- **Pro:** signals to consuming repos that goc *does* recognize "literature-anchored design docs" as a deck-runtime concept, even without prescribing where they live.
- **Con:** longer prose; arguably redundant once the surrounding bullets already cite "papers" and "axioms".

### Recommendation

Path **B** keeps the signal while removing the project-shape assumption. The bullet is uniquely valuable for repos whose research framework lives in design docs rather than code (a documentation-class fix that closes a derivation gap won't trip the "mechanism / sign / primitive / default" bullets, but *is* research-impacting). Make the doc-class trigger explicit and path-agnostic.

If picked: the fix lands as a one-line edit in `goc/templates/skills/next-card/SKILL.md`, with `sync_plugin_assets.py` regenerating the four mirror copies and `port_skills_to_openclaw.py` re-porting the openclaw skill.

## Fix sketch (pending the decision above)

Conditional on path B:

```diff
- - Close (or reopen) a gap in `docs/framework/*.md`.
+ - Close (or reopen) a gap in a literature-anchored design or framework
+   doc (whatever path your repo uses for primary-source references).
```

Conditional on path A: delete line 117 (and the trailing blank-line discipline of the surrounding bullets).

Either path: regenerate auto-synced mirrors via `python scripts/sync_plugin_assets.py` and re-port the openclaw skill via `python scripts/port_skills_to_openclaw.py`. Run `python scripts/sync_plugin_assets.py --check` and `python scripts/port_skills_to_openclaw.py --check` to confirm drift is zero.

definition_of_done (replace after decision):

  - [ ] PROCESS: human picks fix path A (delete) or B (generalize); decision recorded above
  - [ ] MECHANICAL: `goc/templates/skills/next-card/SKILL.md:117` edited per the chosen path
  - [ ] MECHANICAL: `python scripts/sync_plugin_assets.py` regenerates `.claude/skills/`, `.codex/skills/`, `claude-plugin/skills/`, `codex-plugin/skills/` mirrors; `--check` exits zero
  - [ ] MECHANICAL: `python scripts/port_skills_to_openclaw.py` re-ports the openclaw skill; `--check` exits zero
  - [ ] PROCESS: `uv run goc validate` clean
