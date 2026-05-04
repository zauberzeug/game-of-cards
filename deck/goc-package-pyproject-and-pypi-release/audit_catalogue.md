# Audit catalogue — phasor specifics in goc-shipped templates

**Status:** Pre-extraction inventory.
**Scope:** The 11 goc-shipped skill directories + `deck.py` engine + `.claude/hooks/deck_*.py` + the GoC-relevant sections of `CLAUDE.md`. Total: 16 files.
**Method:** 9-category grep audit per the parent card's "Audit catalogue" section (`README.md` §87–104).
**Outcome:** Disposition recorded per finding. This catalogue is **phasor-internal** — it stays in this card's directory and feeds sub-card 6 (`goc-migrate-phasor-agents-off-vendored-deckpy`) as the briefing for authoring phasor-agents' own `.game-of-cards/` content. It is **not** shipped to the new `zauberzeug/game-of-cards` repo, which describes the methodology generically and has no use for phasor-specific migration mappings.

---

## Headline numbers

| # | Category | Findings | Disposition class |
|---|---|---|---|
| 1 | Domain principles (bio-faithful, axioms) | 16 | extract → `principles.md` + `hooks/<skill>.md` |
| 2 | Domain vocabulary (TGC, F-channel, striosome, …) | ~30 | extract → `canonical-tags.md` + `domain-vocabulary.md` |
| 3 | Project-local skills (`/mindset`, `/observe`, …) | 41 (all `/mindset`) | stays project-local; wired in via `hooks/<skill>.md` |
| 4 | Sub-agent roster (8 personas) | 11 | stays project-local; surfaced via `hooks/extend-deck.md` |
| 5 | Tooling conventions (`uv run`, `model: opus`, …) | ~50 | mostly mechanical (`goc <verb>` rewrite); `tooling-conventions.md` for residue |
| 6 | Documentation conventions (STATUS.md / SPEC.md / pong dashboard) | ~20 | extract → `documentation-conventions.md` + `hooks/finish-card.md` |
| 7 | File-path conventions (`paper/`, `demos/`, `verify/`, …) | ~25 | extract → `file-path-map.md` |
| 8 | Project-specific pre-commit hooks | 2 | stays in consuming repo's `.pre-commit-config.yaml` |
| 9 | In-skill domain examples (pong-, line-follower, R8x rounds) | ~15 | extract → `domain-examples.md` (rewritten as generic) |

**Surprise:** `deck.py` engine itself is ~99% project-agnostic — only 5 lines have phasor flavor (pedagogical examples in title-naming docstring + one error message). The packaging extraction is dominated by **skill bodies**, not engine code.

---

## Category 1 — Domain principles

The "bio-faithful / bio-divergence is a bug" framing is the project's structural axiom layer. It surfaces in skill bodies as decision criteria.

| File:line | Phrase | Disposition |
|---|---|---|
| `create-card/SKILL.md:101` | "If the card you're filing has a bio-faithful decision at its core" | Replace inline; gate logic moves to `hooks/create-card.md` |
| `create-card/SKILL.md:107` | "If /mindset gives a clear bio-faithful answer with axiom citation" | `hooks/create-card.md` |
| `decide-card/SKILL.md:18,37,116,125` | "bio-faithful principles already determine the answer" / "non-bio-faithful question" | `hooks/decide-card.md` (gate-recording requires citation clause) |
| `finish-card/SKILL.md:59` | "Bio-faithfulness is the methodology's target (CLAUDE.md "Bio-divergence is a bug, not a tradeoff")" | Re-author Step 2 generically; phasor-specific framing → `hooks/finish-card.md` |
| `finish-card/SKILL.md:61,78,84,86,89` | "non-bio-faithful default" / "row-L1 invariant from row-L2 toward bio-faithful row-L1" | Same — generic Step 2 + phasor-specific hook |
| `extend-deck/SKILL.md:80,87` | "bio-plausibility — and especially when the right gate" / "when bio-faithful reasoning is decisive" | `hooks/extend-deck.md` |
| `pull-card/SKILL.md:59,66` | "non-bio-faithful question, OR /mindset is ambiguous" / "when bio-faithful reasoning is decisive" | `hooks/pull-card.md` |
| `CLAUDE.md:57` (project-level) | "Bio-divergence is a bug, not a tradeoff — when code diverges from biology, the code is wrong" | **Stays in phasor-agents' CLAUDE.md** (NOT a goc concern) — generic CLAUDE.md template ships only goc-specific sections |

**Generic skill rewrite pattern:** Step 2 of `finish-card` becomes "Run a closure-criteria audit per the consuming repo's `.game-of-cards/hooks/finish-card.md`. Project-specific axioms live there." Phasor's `bio-faithful` test is one possible audit; another project might encode a security-review or compliance-review gate.

---

## Category 2 — Domain vocabulary

Phasor terms permeate `card-schema/SKILL.md`'s tag-predicate table (the most extraction-heavy single file).

| File:line | Tokens | Disposition |
|---|---|---|
| `card-schema/schema.yaml:24-28,43-46` | `plasticity`, `fchannel`, `alpha-channel`, `prediction`, `axiom`, `framework`, `research`, `pong`, `nrem` | **9 phasor-only tags** removed from goc-shipped `schema.yaml`; consuming repo adds them via `.game-of-cards/canonical-tags.md` (parsed by `goc validate`) |
| `card-schema/SKILL.md:159` | "(which axiom / literature / convention is in tension; what)" | Reword generically (drop `axiom`, keep `literature` + `convention`) |
| `card-schema/SKILL.md:292-302,305` | `heterosynaptic-ltd-absent-fchannel` example card body — "F-channel `W_coupling` lacks the in-step row-budget redistribution primitive that biology implements as heterosynaptic LTD … pong-demonstrated via Bug 138 R87-R90" | Extract entire example → `domain-examples.md`. Generic skill body uses a placeholder example or `!`cat .game-of-cards/domain-examples.md`` injection |
| `card-schema/SKILL.md:361-368` | Tag-predicate table: `plasticity` cites `TGC, CompetitionPlasticity, …`; `fchannel` cites `F-channel, W_coupling`; `alpha-channel` cites `α-channel, W_competition, RFI`; `prediction` cites `kappa/κ, self-anneal, striosomal`; `axiom`; `framework` cites `computational-principles, stability-hierarchy, operating-amplitude` | **Entire table is phasor-domain.** Goc ships only the generic tag predicates (`bug`, `documentation`, `test`, `api-contract`, `meta-fix`, `infra`, `unverified`, `epic`, `story`); consuming repo authors `canonical-tags.md` with their own table |
| `card-schema/SKILL.md:366` | Literature-drift author list: `Schultz, Frémaux, Gerstner, Pathak, Laurent, Fries, Deco, Jirsa, Kim & Large, Eckmann, Royer, Paré, Hudspeth, Friedman, Frey, Morris, Stuart-Landau, Hopf, Daw, Sutton, van Rossum, Turrigiano, Oja, Smolen, Mink, Aron, Schmidt, Jin, Costa, Krishna, Stromsdorfer, Gast, Sakaguchi, Kuramoto, Breakspear, Fremaux` | Phasor-domain literature anchors. → `canonical-tags.md` with predicate templated as "body cites a published author surface (consult project-specific list)" |
| `card-schema/SKILL.md:379` | `pong` predicate: "title contains `pong` or body cites `demos/pong/`, `pong/agent.py`, …" | Phasor-only. → `canonical-tags.md` |
| `decide-card/SKILL.md:114` | "(e.g., Kuramoto §2.2; Strogatz §8.2)" | Generic-textbook citation example; replace with neutral "e.g., Knuth Vol 3 §6.4" or remove |
| `extend-deck/SKILL.md:175` | Author list "Frémaux/Gerstner, Schultz, Pathak, Laurent, Fries, Deco/Jirsa, Frey/Morris" | → `hooks/extend-deck.md` (the hunter-briefing instructions) |
| `extend-deck/SKILL.md:144` | "F-channel" mentioned in NaN/Inf triage | Reword: "the F-channel signal" → "any signal flagged in `hooks/extend-deck.md`" |
| `extend-deck/SKILL.md:183` | "this isn't really using the phasor substrate as documented" | → `hooks/extend-deck.md` (sub-agent briefing) |
| `next-card/SKILL.md:50` | "library (`phasor_agents/`) vs demo (`demos/`)" | Reword generically; project layout maps live in `file-path-map.md` |

---

## Category 3 — Project-local skills

`/mindset` is the only project-local skill currently called by goc-shipped templates. It is invoked at five distinct workflow points; each becomes a hook-file injection.

| Skill | Workflow point | Phasor wiring (becomes `hooks/<skill>.md`) | Lines |
|---|---|---|---|
| `create-card` | Pre-decision-gate-raise | "If the card has a bio-faithful decision at its core, invoke `Skill(mindset)`. If /mindset gives a clear axiom citation with `<axiom>: <one-line>` form, lower gate from `decision` to `none`." | 99-124 |
| `decide-card` | Pre-record agent-authored decision | "If recording an agent-authored decision, the `--because` MUST start with a `/mindset: <principle>` clause." | 17-37, 102-125 |
| `finish-card` | Step 2 closure audit | "Run `/mindset` audit before closing. Record outcome as one log.md line: `/mindset audit: PASS — invokes <axiom> + <primary source>` OR `PASS — no axiom touched, mechanical fix`. FAIL diverts to `Skill(advance-card) <title> open`." | 20, 57-89, 122, 152 |
| `extend-deck` | Phase-3 gate-clarification | "When the right gate is unclear, invoke `Skill(mindset)` for the full vision/axioms/plasticity context." | 80-87 |
| `pull-card` | Lazy-Andon trial | "Before raising `human_gate`, invoke `Skill(mindset)`. If it answers confidently, record decision as `/mindset: <principle> — <one-line>` and proceed. Only raise the gate if /mindset cannot resolve the question." | 39-68 |
| `card-schema` | DoD-layer-2 enumeration | Single mention: "Layer 2 covers tests-pass / ruff / `/mindset` audit" | 198 |

**Generic skill body pattern** (proposed):

```markdown
## Pre-decision: project-specific consultation

!`cat .game-of-cards/hooks/<self>.md 2>/dev/null || true`
```

If the consuming repo has no hook file, the skill proceeds with the generic flow (raise gate to `decision`). If present, the markdown is inlined and instructs the agent which project-local skill to consult and what citation form to use.

**Other phasor-local skills not currently called by goc-shipped templates** (so no extraction needed): `/observe`, `/update-experiment`, `/research-review`. They stay in phasor-agents' `.claude/skills/` untouched.

---

## Category 4 — Sub-agent roster

`extend-deck/SKILL.md` Phase-2 Hunt (lines 159-189) is the only goc-shipped skill that names sub-agents directly. Eight phasor-specific personas appear:

| Persona | Role description in skill body |
|---|---|
| `analytical-reviewer` | "primary hunter; finds inconsistency between doc and code. Always include." |
| `pr-review-toolkit:silent-failure-hunter` | "error handling, catches, silent fallbacks" |
| `Explore` (with `thoroughness: very thorough`) | "for areas the analytical-reviewer hasn't visited" |
| `visionary` | "high-impact + `tags: [documentation]` hunter for principle / cross-doc / intra-doc claims" |
| `bio-reviewer` / `neuro-reviewer` / `ml-reviewer` | "for docs-vs-literature drift" |
| `hardcore-tester` | "for tests that pass for the wrong reason" |
| `substrate-reviewer` | "when the defect might be 'this isn't really using the phasor substrate as documented'" |
| `creative-cs` | "for architectural ugliness: five special cases hiding one rule" |
| `pragmatic-engineer` | "for code smells: duplicated logic, defensive scaffolding around a hidden bug" |

**Disposition:** Entire Phase-2 sub-agent roster moves to `hooks/extend-deck.md`. The agents themselves (`.claude/agents/<name>.md`) **stay in phasor-agents' `.claude/agents/`** — not goc-shipped. Generic `extend-deck` body has placeholder text:

```markdown
## Phase 2 — Hunt (parallel agents in a single message)

!`cat .game-of-cards/hooks/extend-deck.md 2>/dev/null || true`

If the consuming repo has not authored a hunter roster, default to spawning
one `general-purpose` agent with the user's scope as briefing.
```

Generic-default rationale: any consuming repo on Claude Code has `general-purpose` available; specialized hunters are project-specific.

---

## Category 5 — Tooling conventions

The biggest finding-count category, but most is **mechanical**: every `uv run python .claude/skills/deck/deck.py <verb>` becomes `goc <verb>` (or `_goc-bootstrap.sh <verb>` per sub-card 5) when the engine is packaged. This is the packaging refactor's responsibility, not a phasor-extraction.

| Pattern | Count | Disposition |
|---|---|---|
| `uv run python .claude/skills/deck/deck.py <verb>` | 35+ | **Mechanical rewrite to `goc <verb>`.** Done as part of the packaging refactor (this card), not a per-template extraction |
| `Use model: "opus" per project CLAUDE.md` | 1 (`extend-deck/SKILL.md:204`) | → `tooling-conventions.md`. Generic skill body says: "consult `.game-of-cards/tooling-conventions.md` for model-tier guidance" |
| `uv run python tmp/grow_deck_probe.py` | 1 (`extend-deck/SKILL.md:113`) | Phasor-tooling-flavored. Reword: "Write a probe under `<your-project's-tmp-dir>/`" + reference `file-path-map.md` |
| `uv run python demos/pong/trace_approach.py --seed 42 …` | 1 (`extend-deck/SKILL.md:138`) | Phasor-only live-probe section. Move entire section to `hooks/extend-deck.md` (Phase-1 live-probe instructions) |
| `pytest` references in `card-schema` predicate, `finish-card` Steps 2/5/8 | 5 | Generic — pytest is a common Python testing tool |

**Result:** Category-5 extraction is small. Most are renames the packaging refactor handles in bulk.

---

## Category 6 — Documentation conventions

`STATUS.md` / `SPEC.md` / pong dashboard refresh is the most concentrated extraction surface in `finish-card`.

| File:line | Item | Disposition |
|---|---|---|
| `finish-card/SKILL.md:25,192-232` | Step 7: "Refresh `demos/pong/STATUS.md` dashboard" — entire 50-line section including dashboard form enforcement (Shipping config / Latest metrics / Recent activity / Active open items / Key design principles / Pointers; "no past-sprint analyses; move to HISTORY.md"; row format `\| YYYY-MM-DD \| closed \| <title> — …`) | **Entire Step 7 → `hooks/finish-card.md`**. Generic Step 7 is one line: "If the consuming repo defines a `hooks/finish-card.md` post-close action (status dashboard, changelog row, etc.), follow it. Otherwise skip." |
| `deck/SKILL.md:175` | "run `deck.py done <title>`, refresh STATUS.md dashboard, hand to" | Reword generically (drop the STATUS.md half, keep `goc done`) |
| `extend-deck/SKILL.md:24,109,111` | `!`cat demos/pong/STATUS.md`` priming read; "metric outside the STATUS.md 'Latest metrics' table"; "Compare to STATUS.md and flag divergence ≥ 2σ" | → `hooks/extend-deck.md` Phase-1 priming section |
| `card-schema/SKILL.md:379` | `pong` predicate cites `pong/STATUS.md` | Already covered in Category 2 (canonical-tags.md) |
| `next-card/SKILL.md:108` | "Update an empirical / publication-tier claim" | Generic-enough — keep, or reword as "domain-substantive claim" |
| `pull-card/SKILL.md:42` | "publication-tier reframing" in gate-raise list | Generic-enough; keep |
| `CLAUDE.md:137` (project-level) | "When editing STATUS.md, SPEC.md … coupling floor, W_coupling+W_pred not W_coupling-only … reward-processing.md" | **Stays in phasor-agents' CLAUDE.md.** Generic CLAUDE.md template references `.game-of-cards/documentation-conventions.md` for project-specific doc rules |

---

## Category 7 — File-path conventions

The clearest case where phasor's project layout (`paper/`, `demos/<demo>/`, `verify/`, `tmp/` gitignored, `phasor_agents/` subtree-pushed) leaks into goc templates.

| File:line | Phasor path | Disposition |
|---|---|---|
| `extend-deck/SKILL.md:3,46,47` | argument-hint "(docs/ + phasor_agents/ + demos/pong/)"; default scope; out-of-scope list "`paper/`, other demos" | Replace argument-hint with generic prose; default scope reads from `.game-of-cards/file-path-map.md` |
| `extend-deck/SKILL.md:16-24` | Priming reads: `cat docs/framework/{vision,axioms,architecture,plasticity}.md` + `cat demos/pong/STATUS.md` | **Entire priming-read block → `hooks/extend-deck.md`** (Phase-0 priming) |
| `extend-deck/SKILL.md:101,113,135-138,170,202` | `tmp/grow_deck_probe.py`, `demos/pong/trace_approach.py`, `docs/framework/*.md`, `axioms.md`, `vision.md`, `deck/<title>/reproduce.py` | First 3 → `hooks/extend-deck.md` (live-probe + priming); `deck/<title>/reproduce.py` is **goc-generic** (stays in template) |
| `next-card/SKILL.md:3,25,50,51,102` | `demos/pong`, `phasor_agents/`, `demos/`, `docs/framework/*.md` | Reword: argument-hint is "optional area filter"; "library vs demo" → `file-path-map.md` |
| `finish-card/SKILL.md:25,192,200` | `demos/pong/STATUS.md` | Already covered in Category 6 |
| `create-card/SKILL.md:176,198` | `deck/<title>/reproduce.py` | **Goc-generic** — `deck/` is the methodology's canonical card location |
| `CLAUDE.md:13-20,131-132` (project-level) | "Where scripts live: `tmp/` … `deck/<card>/` … `verify/` … `tests/`" | **Stays in phasor-agents' CLAUDE.md.** Generic CLAUDE.md template references `.game-of-cards/file-path-map.md` |

**`deck/<title>/`** — note this path *is* part of goc itself (the canonical card-data location). Not a phasor-extraction.

---

## Category 8 — Project-specific pre-commit hooks

Light surface; no goc-shipped skill body installs phasor-specific hooks.

| File:line | Item | Disposition |
|---|---|---|
| `CLAUDE.md:133` | "cascading test failures … reservoir benchmarks, plasticity tests, etc." | Stays in phasor-agents' CLAUDE.md (project tooling note) |
| `card-schema/SKILL.md:366` | Literature-drift author predicate | Already covered in Category 2 (canonical-tags.md) |

`goc install` ships only the `goc validate` pre-commit entry. Project-specific pre-commit hooks (Kim & Large year sweep, citation registry, etc.) are the consuming team's territory and not visible to the goc engine.

---

## Category 9 — In-skill domain examples

Most pedagogical examples in the skill bodies and `deck.py` docstrings are phasor-flavored.

| File:line | Example | Disposition |
|---|---|---|
| `deck.py:858` (title-naming docstring) | "Bad: `pong-late-hr-stuck-below-50-after-bug-140-path-2`" | Replace with generic: e.g., "Bad: `api-csv-export-button-stuck-below-50ms-after-bug-103-path-2`" |
| `deck.py:861` | "Good: `pong-cannot-recover-prior-task-performance`" | Replace with generic: "Good: `api-degrades-after-load-spike`" |
| `deck.py:867-869,877` | "R89 framework HEAD; R88 N=20"; "R90's late_HR ≥ 0.50 mean with σ ≤ 0.20" | Replace with generic |
| `deck.py:1467` | Error message: "`r88-csubstrate-replication` → `pong-cannot-recover-prior-task-performance`" | Replace with generic example slug pair |
| `card-schema/SKILL.md:293-333,343` | `heterosynaptic-ltd-absent-fchannel` example card body; "(`line-follower`, `target-tracking`, `olfactory-classification`)" parenthetical | → `domain-examples.md`. Generic body uses placeholder + `!`cat`` injection |
| `scan-deck/SKILL.md:42,87,154` | "pong-active vs pong-DORMANT"; "Sprint 2.44 coherence²-collapse theorem; pong + …"; "(pong-active vs pong-DORMANT, recent regression vs old)" | Reword generically: "active vs dormant" — the contribution-tier-undercutter framing is generic; the pong instantiation is the phasor flavor |
| `finish-card/SKILL.md:78` | "row-L1 invariant from row-L2 toward bio-faithful row-L1 sum" | Replace example with generic refactor outcome ("normalized representation") |
| `finish-card/SKILL.md:103` | "10-seed pong sweep within 2σ of prescribed motor row-L1" example DoD line | Replace with generic |
| `finish-card/SKILL.md:123,195` | "Pong impact: dormant / +Xpp probe / -Ypp regression"; "mark 'pong-dormant'" | The "dormant" framing is generic-useful; "pong" is the phasor instantiation. → `hooks/finish-card.md` (closure-row format) |
| `extend-deck/SKILL.md:135-138` | Live-probe section: "Pong ships `demos/pong/trace_approach.py`" + the trace probe instructions | Already covered in Category 7 → `hooks/extend-deck.md` |

**Engine impact (deck.py):** ~5 lines need rewording. Trivial. The engine is otherwise generic.

---

## Resulting `.game-of-cards/` file roster (consuming repo)

Based on the audit, phasor-agents' own `.game-of-cards/` (authored in sub-card 6 dogfood migration) needs:

**Content stubs** (root):
- `canonical-tags.md` — 9 phasor tags + tag-predicate table + literature-drift author list
- `domain-vocabulary.md` — phasor / TGC / F-channel / striosome / Hopf / Kuramoto / Lyapunov glossary
- `domain-examples.md` — `heterosynaptic-ltd-absent-fchannel`, `pong-cannot-recover-prior-task-performance`, sample axiom-citation forms (`/mindset: A6 striosome/matrix separation`)
- `tooling-conventions.md` — `model: "opus"` mandate; (the generic "uv run" → "goc" mechanical part is handled by packaging, not this file)
- `documentation-conventions.md` — STATUS.md vs SPEC.md split; formula consistency rule; "frame universally not per-demo"
- `file-path-map.md` — `paper/`, `demos/<demo>/`, `verify/`, `tmp/` (gitignored — "evidence may be deleted"), `phasor_agents/` (per phasor-agents' README, intended for future export)

**Content stubs NOT needed** (no extraction surface):
- `mission.md` — would be useful for human readers but no goc-shipped skill currently `!cat`s it. Optional.
- `principles.md` — phasor's bio-faithful axioms live in CLAUDE.md and `docs/framework/axioms.md`; goc-shipped skills reference them via the `/mindset` hook (Category 3), not via direct injection. So `principles.md` is **not load-bearing** in the audit; it can be deferred or merged into `domain-vocabulary.md`.
- `subagent-roster.md` — same logic; the roster lives in `hooks/extend-deck.md` (active invocation), not in a separate content stub.
- `commit-style.md` — `prepare-commit` skill is invoked from `finish-card` Step 8 but is project-local in phasor-agents. Goc-shipped `finish-card` doesn't need it.

**Workflow-hook stubs** (`hooks/`):
- `hooks/create-card.md` — when to lower gate via `/mindset`; agent-authored-decision citation requirements
- `hooks/decide-card.md` — `--because` MUST start with `/mindset: <principle>` clause for agent-authored decisions
- `hooks/finish-card.md` — Step 2 `/mindset` audit recipe + log.md format; Step 7 `demos/pong/STATUS.md` refresh + dashboard form rules
- `hooks/pull-card.md` — lazy-Andon: try `/mindset` before raising gate; citation form
- `hooks/extend-deck.md` — Phase-0 priming (cat docs/framework/* + STATUS.md), Phase-1 live-probe (`demos/pong/trace_approach.py`), Phase-2 hunter roster (8 personas)

**Total:** 6 content stubs (4 load-bearing, 2 deferred) + 5 hook files. Smaller than the card body anticipated (10 + 4) — the audit collapsed several into hook files because the skill bodies actively use the content rather than just injecting it.

---

## Engine refactor notes (separate from phasor-extraction)

These are part of the packaging refactor itself, not category-9 extractions:

1. **`uv run python .claude/skills/deck/deck.py <verb>` → `goc <verb>`** — 35+ occurrences across all 11 SKILL.md files. Mechanical sed-able rename once the package is registered.
2. **`deck.py` import path** — moves from `.claude/skills/deck/deck.py` to `goc/cli.py` (CLI plumbing) + `goc/engine.py` (value math, frontmatter, validator). Splits per the parent card's "How" Step 1.
3. **`importlib.resources.files("goc.templates")` access pattern** — replaces today's working-tree-relative reads (`use-game-of-cards/SKILL.md` mode A reads from this repo; `goc install` reads from package data).
4. **`schema.yaml` location** — moves from `.claude/skills/card-schema/schema.yaml` to `goc/templates/skills/card-schema/schema.yaml` (or a sibling `goc/schema.yaml` referenced by both the engine and the card-schema skill). Decision deferred to packaging step.
5. **`.claude/hooks/deck_*.py`** — `deck_session_start.py` and `deck_prompt_router.py` are Claude-runtime hook scripts. They'll ship as templates under `goc/templates/hooks/` and be installed by `goc install` (sub-card 2). Audit them for phasor refs separately when sub-card 2 starts; first grep showed only one hit (`deck_prompt_router.py:46` matches `r"\brun\s+(pytest|the\s+tests)\b"` — generic test-run intent detection, not phasor-flavored).

---

## Sequencing recommendation for the rest of the card

Given the audit, the implementation work splits into mostly-independent tracks:

1. **Repo creation** (DoD item 1) — create `zauberzeug/game-of-cards` fresh on GitHub (no git-history preservation). Files copied verbatim per the disposition table. Independent of all other tracks.
2. **`pyproject.toml` + `goc/` layout** (DoD items 2-3) — engine moves, console-script entry point. Touches `deck.py` only mechanically. Can start now.
3. **Phasor-extraction pass on skill templates** (DoD items 4-6, 8-10) — this audit's findings, applied. Touches all 11 SKILL.md files + `card-schema/schema.yaml`. The biggest single chunk; can split into:
   - 3a. Generic-rewrite pass (drop phasor refs, replace examples, add `!`cat`` injection points) — touches all 11 files
   - 3b. Author starter `.game-of-cards/` stubs in `goc/templates/game_of_cards/` (DoD item 9)
   - 3c. (DoD item 10 already satisfied — this `audit_catalogue.md` is the disposition mapping; sub-card 6 consumes it directly. No `MIGRATION.md` is authored in the new repo.)
4. **PyPI release flow** (DoD items 11-13) — TestPyPI dry-run, GH Actions release workflow, first prod release. Can start once 1-3 are done.
5. **License** (DoD item 14) — independent; can land first.

Track 3 is the biggest. The generic-rewrite pass (3a) is the only place where I might want to pause for confirmation: dropping `/mindset` from skill bodies is a behavior-changing edit, and phasor-agents itself runs on these skills until sub-card 6 dogfood migration completes. Two options:

- **Option α** (preferred): work on the new-repo's templates only. Phasor-agents' `.claude/skills/` stays untouched until sub-card 6.
- **Option β**: rewrite phasor-agents' own skills first (so the generic templates are derived from a known-working state). Riskier — any regression hits the active /loop.

α is the cleaner path; the new-repo templates are derived from the audited current-state and the phasor-laced bits go into phasor-agents' future `.game-of-cards/` (authored in sub-card 6 from this catalogue mechanically).

---

## What's NOT in this catalogue (and why)

- **`.claude/agents/<persona>.md` bodies** — the 8 phasor-specific sub-agents (`bio-reviewer`, `neuroscientist`, etc.) are not in goc's scope. They stay in phasor-agents' `.claude/agents/`. The audit only flags **invocation sites** in goc-shipped skills; persona definitions are out of scope.
- **`docs/framework/*.md`** — phasor's framework docs aren't shipped by goc. Goc-shipped skills *read* them (`!`cat docs/framework/axioms.md``); the `!`cat`` paths move to `hooks/<skill>.md` (Category 1 + Category 7).
- **`paper/`, `demos/`, `verify/`, `tests/`, `phasor_agents/`, `tmp/` directories** — phasor-agents' filesystem layout. Captured in `file-path-map.md` for the consuming repo to author; goc engine never assumes a specific layout.
- **Custom phasor-agents commit-message conventions** (`Co-Authored-By` lines, `decide:` / `refine:` / `reduce:` prefixes) — these live in `prepare-commit/SKILL.md`, which is **not goc-shipped**. Stays in phasor-agents' `.claude/skills/` as a project-local skill (similar to `/mindset`).
- **`mindset/SKILL.md` body itself** — phasor-only skill. Stays in phasor-agents' `.claude/skills/mindset/`. Goc-shipped skills reference it via `hooks/<skill>.md` files, never directly.
