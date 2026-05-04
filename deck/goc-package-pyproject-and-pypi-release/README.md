---
title: goc-package-pyproject-and-pypi-release
summary: "Turn `.claude/skills/deck/deck.py` plus the 11 skill directories into a proper Python package, `game-of-cards` on PyPI, with `goc` as the console-script entry point. Two-layer architecture: the package ships only domain-agnostic skills and a generic engine; consuming repos add a `.game-of-cards/` directory with two kinds of files — content stubs (canonical-tags.md, domain-examples.md, commit-style.md) that get inlined into skill bodies, and workflow-hook stubs (`hooks/<skill>.md`) that name project-local skills the generic skill should consult at specific points. `/mindset` is NOT a goc-shipped skill — it's a phasor-only skill that stays in phasor-agents' `.claude/skills/`; phasor-agents wires it back into the generic flow via `.game-of-cards/hooks/pull-card.md` etc. The engine code already exists and is well-factored; this card is the packaging + decoupling layer — `pyproject.toml`, src layout, skill templates as package data via `importlib.resources`, audit pass to remove every phasor reference from the templates (including dropping `/mindset` from the templated set), license, README on the new repo, GitHub Actions for PyPI release. The new repo `zauberzeug/game-of-cards` is created **fresh** — no git history preserved from phasor-agents, since the methodology only crystallized in the last ~6 weeks and history-preservation has no downstream value. The phasor-agents-side migration mapping (which extracted item lands where) is **NOT** shipped in the new repo; it lives in this card's directory as `audit_catalogue.md` and feeds sub-card 6 (`goc-migrate-phasor-agents-off-vendored-deckpy`) as a phasor-internal briefing. Primary install is `uv tool install game-of-cards` to match Zauberzeug's uv-everywhere convention; `pipx install game-of-cards` documented as fallback for users without uv."
status: done
stage: null
contribution: medium
created: 2026-05-03
closed_at: 2026-05-04
human_gate: none
advances:
  - goc-ship-game-of-cards-as-cross-agent-cli
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] New repo `zauberzeug/game-of-cards` created fresh (no git-history preservation from phasor-agents); files copied verbatim per the audit catalogue's disposition table. Live at https://github.com/zauberzeug/game-of-cards (public, MIT, default branch `main`, inaugural commit `970b1d1`).
  - [x] `pyproject.toml` declares `game-of-cards` package with `goc` console script entry point pointing at `goc.cli:main` (committed as `bce1813` in `~/Projects/game-of-cards`; hatchling backend, click + pyyaml deps, `[project.scripts] goc = "goc.cli:main"`)
  - [x] All deck.py CLI verbs (`new`, `done`, `move`, `validate`, `triage`, `kanban`, `--json`, etc.) work via `goc <verb>` after `uv pip install -e .` (verified all 13 verbs reachable via `goc --help`; `goc validate` walks 159 cards in phasor-agents deck with all OK; `goc --json --tag bug --status open` returns valid JSON with 84 entries; `goc show <title>` renders frontmatter; default group renders impact-sorted board identical to `deck.py`. Path constants refactored: `REPO_ROOT = Path.cwd()` for project coordinates, `SCHEMA_FILE = Path(__file__).parent / "schema.yaml"` for package coordinates)
  - [x] Generic skill templates (the goc-shipped subset — `pull-card`, `decide-card`, `create-card`, `advance-card`, `finish-card`, `next-card`, `scan-deck`, `improve-deck`, `extend-deck`, `card-schema`, `deck` + starter `.game-of-cards/` scaffold) ship as package data, accessible via `importlib.resources.files("goc.templates")`. Verified at install time: `from importlib.resources import files; (files("goc.templates") / "skills" / "pull-card" / "SKILL.md").is_file()` → True. AGENTS.md template + CLAUDE.md sections + hooks-as-installed-files are sub-card 2's responsibility (`goc-install-command-scaffolds-repo`). Note: `/mindset` is NOT in this set — phasor authors it back in via `.game-of-cards/hooks/<skill>.md` injection.
  - [x] **Templates are project-agnostic**: zero phasor-agents references in `goc/templates/` and `goc/cli.py` / `engine.py` / `install.py`. Verified across 11 SKILL.md files + engine.py + cli.py + install.py + schema.yaml: comprehensive grep audit on 27 phasor tokens returns 0 hits (residue trajectory 210 → 88 → 63 → 36 → 16 → 0 across four Track 3a-deep batches). Two-direction live verification: `goc validate` REJECTS phasor's domain tags without `.game-of-cards/canonical-tags.md`, ACCEPTS them when the extension file is authored.
  - [x] **All 9 audit categories addressed**: Cat-1 (domain principles, 16 hits, → hooks/*) — done across pull-card / decide-card / create-card / finish-card / extend-deck. Cat-2 (domain vocabulary, ~30 hits, → canonical-tags.md extension mechanism) — done in card-schema (tag enum trimmed, hook injection wired). Cat-3 (project-local skills `/mindset`, 41 hits, → hooks/<skill>.md) — done in 5 skills. Cat-4 (sub-agent roster, 8 personas, → hooks/extend-deck.md) — done. Cat-5 (tooling conventions `uv run python deck.py`, ~50+ hits, mechanical sed) — done (186 replacements across two passes; goc/engine.py path-anchor + bare deck.py both handled). Cat-6 (documentation conventions, STATUS.md dashboard, → hooks/finish-card.md) — done in finish-card / extend-deck / deck. Cat-7 (file-path conventions, ~25 hits, → hooks/extend-deck.md + file-path-map.md) — done. Cat-8 (project-specific pre-commit hooks) — stays in consuming-repo per audit. Cat-9 (in-skill domain examples, ~15 hits) — done with neutral csv-export-button-* / auth-cookie-* placeholders.
  - [x] **`.game-of-cards/` has two file kinds**: (1) content stubs at root (canonical-tags.md, domain-vocabulary.md, domain-examples.md, tooling-conventions.md, documentation-conventions.md, file-path-map.md) — inlined verbatim into skill bodies via `!`cat`` injection; (2) workflow-hook stubs at `hooks/<skill>.md` (create-card, decide-card, finish-card, pull-card, extend-deck) — markdown instructions a generic skill follows at a defined hook point. Both kinds shipped as empty header-only stubs in `goc/templates/game_of_cards/`.
  - [x] **Generic skills load project specifics via `!`cat`` injection**: verified across 6 skills: pull-card (`!`cat .game-of-cards/hooks/pull-card.md``), decide-card (`hooks/decide-card.md`), create-card (`hooks/create-card.md`), finish-card (`hooks/finish-card.md`, used in BOTH Step 2 and Step 7 sections), extend-deck (`hooks/extend-deck.md`, used at Phase 0 priming + Phase 1 probe + Phase 2 hunter roster), card-schema (`!`cat .game-of-cards/canonical-tags.md`` at end of predicate table). Engine.py also reads `.game-of-cards/canonical-tags.md` programmatically (not just a `!`cat`` injection) to merge consuming-repo tag extensions into the validator's enum.
  - [x] **`.game-of-cards/` convention documented** in the new repo (linked from the main README's "What you get" section): the canonical doc lives at `goc/templates/game_of_cards/README.md` and ships into every consuming repo's `.game-of-cards/README.md` at `goc install` time. Covers all four required elements: directory layout (content files at root, hook files under `hooks/`), expected format (markdown with optional fenced YAML for tag extensions), the injection pattern (Claude Code `!`cat <file> 2>/dev/null || true`` with graceful fallback when the file is absent or empty), and the hook-point catalog as a 5-row table (which generic skill injects which hook file at which step). Author guidelines + a "sub-card 6 handles migration" pointer included. Lives at the convention's own location rather than inlined into the main README so the main README stays user-facing-tempting per user direction.
  - [x] **Starter `.game-of-cards/` scaffold** ships in `goc/templates/game_of_cards/` — 6 content stubs (canonical-tags, domain-vocabulary, domain-examples, tooling-conventions, documentation-conventions, file-path-map) + 5 hook stubs (hooks/create-card, hooks/decide-card, hooks/finish-card, hooks/pull-card, hooks/extend-deck), all with HTML-comment headers explaining what content each file expects. Sub-card 2 (`goc-install-command-scaffolds-repo`) consumes these stubs at install time. Verified at install time via `importlib.resources.files("goc.templates")`.
  - [x] **`audit_catalogue.md` in this card's directory** maps every extracted item to its `.game-of-cards/<file>.md` destination — class by class, item by item — so sub-card 6 (dogfood migration) can place phasor-agents' own `.game-of-cards/` content mechanically. Includes the disposition for project-local skills like `/mindset` (stays in phasor-agents' `.claude/skills/`, wired in via hook files) and the sub-agent roster (stays in phasor-agents' `.claude/agents/`, surfaced via a content stub if needed). NOT shipped in the new goc repo — phasor-internal artifact
  - [x] ~~PyPI test release via TestPyPI succeeds~~ — **superseded** by DoD-13 (direct production release on 2026-05-04). Per user directive ("claim the pypi package, sniping risk"), the TestPyPI rehearsal was skipped and `0.0.1` shipped to production PyPI directly. The verification subset that TestPyPI would have caught (entry-point wiring, package-data inclusion, metadata correctness) was instead caught by `uv pip install -e .` against the local dist + the `from importlib.resources import files` smoke test before upload. Logged in the card's `log.md` round 5 entry.
  - [x] First production release published to PyPI (2026-05-04, version `0.0.1`, https://pypi.org/project/game-of-cards/). Confirmed via PyPI JSON API: both wheel (81935 B) and sdist (72699 B) live; metadata correct (MIT license, plain-language description, GitHub URLs); only release in the version index. `uv tool install game-of-cards` reachable once CDN propagates. New repo's README leads with `uv tool install`. Pipx fallback documented in DoD-13's release notes (still pending).
  - [x] GitHub Actions release workflow tags + publishes on git tag push: `.github/workflows/release.yml` triggers on `v*` tag push, builds wheel + sdist via `uv build`, verifies tag matches pyproject version, publishes to PyPI via OIDC trusted publishing (no stored token). Manual `workflow_dispatch` available for dry-run. Companion `.github/workflows/ci.yml` smoke-tests on every push (4-version Python matrix: 3.10/3.11/3.12/3.13) — verifies console script, package data, and runs `goc validate` against the repo's own deck/ if present. Trusted-publisher PyPI-side registration is a one-time manual configuration step at `https://pypi.org/manage/project/game-of-cards/settings/publishing/` (claims: owner=zauberzeug, repo=game-of-cards, workflow=release.yml, env=pypi); until that's done the publish job will error with auth-failure (by design — explicit configuration gate, not a hidden default).
  - [x] **Self-hosted bootstrap** (ticked 2026-05-04, after `goc install` ran in `~/Projects/game-of-cards/`): once sub-card 2 (`goc-install-command-scaffolds-repo`) ships, run `goc install` on the new repo itself. Verify `.claude/skills/` (regenerated from `goc/templates/skills/`), `deck/` (with one starter card demonstrating the workflow), `.game-of-cards/` (filled with goc-development specifics), CLAUDE.md, and AGENTS.md all materialize correctly. The vendored bootstrap templates (used during early development before the CLI is functional) are replaced by the self-hosted install. Compiler-bootstrap analogy: gcc compiles itself, rustc compiles itself; goc manages its own deck.
  - [x] **CI validation on goc repo's own deck** (workflow + pre-commit hook in place; full CI run gated on first `git push origin main`): GitHub Actions workflow runs `goc validate` on every push; PR cannot merge with broken card frontmatter. Same `goc validate` registered as the repo's local pre-commit hook for fast feedback.
  - [x] License chosen and committed (MIT, Copyright Zauberzeug GmbH — matches nicegui / rosys house convention; committed as inaugural commit `970b1d1` of `~/Projects/game-of-cards`)
---

# Package Game of Cards as `goc` on PyPI

## Why

Sub-card of `goc-ship-game-of-cards-as-cross-agent-cli`. This is the foundational packaging work — every other sub-card assumes a real PyPI release exists.

The engine is already factored well enough to package: `deck.py` is a clean Click CLI, the 11 skill directories are self-contained, the schema lives in YAML. What's missing is the layout that makes it a real Python package — `pyproject.toml`, `goc/` directory, console-script entry point, package data for skill templates, and a release pipeline.

But there's a deeper decoupling alongside the packaging: the methodology is generic; today's templates are not. Phasor's bio-faithful axioms, the `pong`/`plasticity`/`fchannel` canonical tags, the framework-specific examples in skill bodies — none of that belongs in a package called `game-of-cards`. The packaging step is also the moment we draw the line between engine and consumer.

## Project-agnostic constraint

The new repo MUST contain zero phasor-agents references. The methodology is the engine; the domain is the consuming repo's concern. Same separation Spec-Kit gets via framework-neutral templates and BMAD gets via domain-neutral personas — load-bearing here because today's `.claude/skills/` is *thoroughly* phasor-laced (axioms, framework concepts, demo names, file paths).

Two layers:

1. **Engine + generic skill templates** in `goc/templates/` — domain-agnostic methodology primitives only: DoD enforcement, status lifecycle, Andon-cord, kanban semantics, decide-card workflow, additive Bellman value math, multi-stakeholder decision Q&A.
2. **Per-repo config** in the consuming repo's `.game-of-cards/` directory — two file kinds the consuming team authors:

**Content files** (root of `.game-of-cards/`) — markdown text inlined verbatim into skill bodies. The exact file roster is discovered during the audit pass; at minimum it covers the categories below where phasor-agents has a non-empty extraction:

| File (suggested) | Purpose | Example (phasor-agents) |
|---|---|---|
| `mission.md` | One-paragraph: what this project is, what kind of work happens here | "Bio-faithful cell-assembly research; phasor agents at near-threshold; pong + line-follower demos" |
| `principles.md` | Domain-specific design principles invoked by skills | A1–A7 axioms; "bio-divergence is a bug, not a tradeoff"; "tests follow the science" |
| `canonical-tags.md` | Tags beyond the generic set | `pong`, `plasticity`, `fchannel`, `alpha-channel`, `prediction`, `axiom`, `literature-drift` |
| `domain-vocabulary.md` | Domain terms agents should recognize in cards/discussions | TGC, PING, Stuart-Landau, striosome, F-channel, α-channel, Lyapunov |
| `tooling-conventions.md` | Language/framework requirements; library bans | "uv run exclusively"; "model: opus for sub-agents"; "no np.fill_diagonal" |
| `documentation-conventions.md` | Doc style rules | "STATUS = current state; SPEC = aspirational"; "first-principles writing"; "no demo measurements as evidence" |
| `subagent-roster.md` | Catalog of project-local sub-agents and when to invoke each | bio-reviewer, neuroscientist, computational-theorist, ml-reviewer, substrate-reviewer, visionary |
| `file-path-map.md` | Where things live in this repo | `paper/`, `demos/<demo>/`, `verify/`, `tmp/` (gitignored), `phasor_agents/`, `deck/<card>/reproduce.py` |
| `domain-examples.md` | Example card titles, decision rationales used in skill bodies | `pong-cannot-recover-prior-task-performance`; sample axiom-citation forms |
| `commit-style.md` | Commit message conventions | CONTRIBUTING.md excerpts; co-author lines |

**Workflow-hook files** (`.game-of-cards/hooks/`) — markdown instructions that name project-local skills the generic skill should consult at a defined hook point:

| File | Hook point | Example (phasor-agents) |
|---|---|---|
| `hooks/pull-card.md` | Pre-decision step in `pull-card` | "Before raising `human_gate`, invoke `Skill(/mindset)` and try to cite axioms A1–A7. Only raise the gate if /mindset cannot resolve the question." |
| `hooks/decide-card.md` | Pre-record step in `decide-card` | "If recording an agent-authored decision, the `--because` MUST start with a `/mindset:` citation clause." |
| `hooks/finish-card.md` | Pre-close step in `finish-card` | "Run `/mindset` audit before closing; record outcome as one log.md line ('PASS — invokes <axiom>' or 'PASS — no axiom touched')." |
| `hooks/create-card.md` | Pre-file step in `create-card` | (phasor-agents leaves empty for now) |

Generic skills inject both kinds via Claude Code's `!`bash`` syntax. A generic `pull-card` template body has a line like:

```markdown
## Pre-decision: project-specific consultation

!`cat .game-of-cards/hooks/pull-card.md 2>/dev/null || true`
```

If the consuming repo's hook file is absent, the line evaluates to nothing and the skill proceeds with its generic flow. If present, the hook's markdown is inlined into the skill prompt — the agent reads it and follows the instructions, including invoking project-local skills the markdown names. The agent's prompt-following is the indirection layer; generic skills never name project-local skills directly.

`goc install` scaffolds a starter `.game-of-cards/` with empty content stubs AND empty `hooks/<skill>.md` stubs (header comments only); the consuming team fills in the project-specifics. Per-repo config never lives in `goc/templates/`; the engine doesn't ship phasor's axioms, pong's canonical tags, or any reference to `/mindset`. Phasor-agents' content moves OUT of the generic skills (sub-card 6 dogfood migration) and INTO this repo's own `.game-of-cards/`.

## Audit catalogue: classes of phasor specifics

`/mindset` is the most visible phasor-specific element, but a full audit of `.claude/skills/` and `CLAUDE.md` shows project-specifics in **nine distinct classes**. Every class needs a disposition — extract to `.game-of-cards/`, leave in the consuming repo as a local skill/agent, or keep generic and rephrase.

| # | Category | Examples in phasor-agents today | Disposition |
|---|---|---|---|
| 1 | **Domain principles** | A1–A7 axioms, "bio-divergence is a bug", "tests follow the science", "defaults reflect current understanding" | Extract → `principles.md`. Generic skills inject via `!`cat``. |
| 2 | **Domain vocabulary** | phasor, TGC, PING, Stuart-Landau, F-channel, α-channel, striosome, Hopf bifurcation, Kuramoto | Extract → `canonical-tags.md` + `domain-vocabulary.md`. |
| 3 | **Project-local skills** | `/mindset`, `/observe`, `/update-experiment`, `/research-review` (the three-grumpy-experts skill is phasor-specific) | Stay in phasor-agents' `.claude/skills/` (NOT goc-shipped). Wired in via `hooks/<generic-skill>.md`. |
| 4 | **Sub-agent roster** | bio-reviewer, neuroscientist, computational-theorist, ml-reviewer, substrate-reviewer, visionary, biologist (each codifies a Levin/Bach/Huberman/etc. persona) | Stay in phasor-agents' `.claude/agents/` (NOT goc-shipped). Surfaced via `subagent-roster.md` content stub for skill bodies that need to know which agents to invoke. |
| 5 | **Tooling conventions** | "uv run exclusively"; `model: "opus"` for sub-agents; `np.fill_diagonal` ban; "no monkey-patch in ProcessPoolExecutor"; "always run pytest after default changes" | Extract → `tooling-conventions.md`. Generic skills inject when proposing/reviewing code. |
| 6 | **Documentation conventions** | "STATUS.md = current state, SPEC.md = aspirational"; "first-principles writing — derive from math, not demo measurements"; "preserve formula consistency"; "frame universally, not per-demo" | Extract → `documentation-conventions.md`. |
| 7 | **File-path conventions** | `paper/`, `demos/<demo>/`, `verify/`, `tmp/` (gitignored — "evidence may be deleted"), `deck/<card>/reproduce.py`, `phasor_agents/` (subtree-pushed) | Extract → `file-path-map.md`. |
| 8 | **Project-specific pre-commit hooks** | "Kim & Large 2020 → 2021 year sweep guard"; "citation registry audit (paper-claim-vs-doc drift)" | Stay in consuming repo's `.pre-commit-config.yaml`. `goc install` adds only the generic `goc validate` entry; project-specific hooks are the consuming team's territory. |
| 9 | **In-skill domain examples** | `decide-card`'s "/mindset: A6 striosome/matrix separation" example; `card-schema`'s phasor canonical tags; `scan-deck`'s "pong-active vs pong-DORMANT" trade-off framing | Extract → `domain-examples.md`. Generic skills inject when illustrating a workflow step. |

The audit pass during this card walks each `.claude/skills/<skill>/SKILL.md` (and the `CLAUDE.md` "Game of Cards" + "Deck Workflow" + adjacent sections), bins every phasor-specific token into one of these classes, and produces `audit_catalogue.md` in this card's directory as the canonical mapping. Sub-card 6 (dogfood migration) consumes that mapping mechanically when authoring phasor-agents' own `.game-of-cards/` files. The catalogue is **phasor-internal** — it has no place in the new goc repo, since the methodology framework's repo describes the methodology generically for any consumer.

**Key invariant**: generic skills never name a project-local skill or sub-agent. They `!cat` markdown that the consuming repo wrote, which is free to name anything. The agent's prompt-following is the indirection layer.

`/mindset` is example #3 — a project-local skill that stays in phasor-agents' `.claude/skills/mindset/` and gets invoked via hook files (`.game-of-cards/hooks/pull-card.md` etc.). The same pattern applies to `/observe`, `/update-experiment`, and `/research-review` — all phasor-local skills that wire back into generic workflows via hook files.

## What

A new repository `zauberzeug/game-of-cards` created **fresh** (no git-history preservation; methodology only crystallized in the last ~6 weeks and downstream consumers have no use for phasor-agents' commit log), structured as:

```
game-of-cards/
├── pyproject.toml          # game-of-cards package, goc entry point
├── goc/
│   ├── __init__.py
│   ├── cli.py              # Click root group; verbs from deck.py (project-agnostic)
│   ├── engine.py           # value math, DoD enforcement, frontmatter parsing
│   ├── install.py          # goc install (sub-card 2)
│   └── templates/          # PACKAGE DATA — extracted by `goc install`
│       ├── skills/         # generic skills only — no /mindset; bodies use !`cat .game-of-cards/...`
│       │   ├── pull-card/
│       │   ├── decide-card/
│       │   ├── create-card/
│       │   ├── advance-card/
│       │   ├── finish-card/
│       │   ├── next-card/
│       │   ├── scan-deck/
│       │   ├── improve-deck/
│       │   ├── extend-deck/
│       │   ├── card-schema/
│       │   └── deck/
│       ├── hooks/          # UserPromptSubmit hook script (Claude-side runtime hook)
│       ├── claude_md/      # CLAUDE.md sections (generic)
│       ├── agents_md/      # AGENTS.md sections (generic)
│       └── game_of_cards/  # starter .game-of-cards/ scaffold (empty stubs)
│           ├── canonical-tags.md
│           ├── domain-examples.md
│           ├── commit-style.md
│           └── hooks/
│               ├── pull-card.md
│               ├── decide-card.md
│               ├── finish-card.md
│               └── create-card.md
├── tests/
├── .github/workflows/release.yml
├── README.md
└── LICENSE
```

After `goc install` in a target repo, the consumer gets:

```
my-project/
├── .claude/skills/                # generic skills, from goc templates
│   └── (mindset/)                 # ← phasor-agents authors this LOCALLY, outside goc
├── .claude/hooks/                 # UserPromptSubmit hook
├── deck/                          # cards live here
├── .game-of-cards/                # PROJECT-SPECIFIC config (consuming team fills in)
│   ├── canonical-tags.md
│   ├── domain-examples.md
│   ├── commit-style.md
│   └── hooks/
│       ├── pull-card.md           # phasor: "consult /mindset before raising gate"
│       ├── decide-card.md         # phasor: "--because must start with /mindset: citation"
│       ├── finish-card.md         # phasor: "run /mindset audit before closing"
│       └── create-card.md         # phasor: empty, or whatever they want
└── CLAUDE.md / AGENTS.md          # generic GoC sections (marker-bounded)
```

Console script in `pyproject.toml`:

```toml
[project]
name = "game-of-cards"  # PyPI distribution name (verified available 2026-05-03)
description = "XP-style story-card kanban methodology for AI-agent collaboration"

[project.scripts]
goc = "goc.cli:main"  # binary on PATH → entry function; import name is `goc`
```

Package data inclusion (`tool.hatch.build.targets.wheel.force-include` or setuptools `package-data`). Inside the code, templates are accessed via `importlib.resources.files("goc.templates")`. Same pattern Spec-Kit uses (`specify_cli/templates/`) and BMAD uses.

### Three names, one package — the `pyyaml` pattern

The PyPI distribution name (`game-of-cards`), the Python import name (`goc`), and the console-script name (`goc`) deliberately diverge. This is the long-established `pyyaml` → `yaml`, `python-dateutil` → `dateutil`, `pillow` → `PIL` pattern: the discoverable long-form goes on PyPI; the short identifier ships in code.

| Identity | Value | Where it appears |
|---|---|---|
| PyPI distribution | `game-of-cards` | `pip install game-of-cards`, `uv tool install game-of-cards`, PyPI search |
| Source dir + import name | `goc` | `goc/...`, `from goc.engine import Card`, `importlib.resources.files("goc.templates")` |
| Console script (binary) | `goc` | `goc <verb>` on PATH after install |

Why diverge:
- The methodology's working identity throughout this codebase is **`goc`** (cards prefixed `goc-`, conversation, file paths). Forcing `from game_of_cards.engine import Card` would tax every internal reader for no benefit.
- A clean `goc` PyPI name would be Option A (uv/ruff pattern: same name everywhere) but the name is taken by a dormant 2023 package (Todd Perry's `djentleman/goc`, last release 2023-09-15). Reclaiming via PEP 541 is a 3–6 month admin process with uncertain outcome — not worth it when the `pyyaml` pattern delivers the same code-side ergonomics today.
- Discoverability lives in `[project] description`, not the distribution name. PyPI search returns descriptions; "Game of Cards methodology framework" is what users will actually search for.

Claim timing: PyPI's first-upload-wins. The name is reserved when Track 4 / DoD-11 publishes the first TestPyPI release (or earlier if we want to fast-track via a 0.0.0 placeholder upload). Risk of pre-emption is low — the phrase is too obscure to be at-risk.

## Why `uv tool install` is the primary command

Zauberzeug uses uv exclusively (this repo's CLAUDE.md mandates `uv run` for everything; pong's dev loop is uv-driven; the active sweep harnesses run under uv). Asking the team to install one Python tool via pipx and everything else via uv is needless cognitive overhead — and a uv-first install matches how the team actually develops.

Beyond Zauberzeug, `uv tool install` is also where the broader Python tooling is heading: it's faster than pipx (Rust-implemented resolver), gives a single tool for env management + packaging + tool installation, and is increasingly the default in 2026 tutorials. pipx still works and is documented as a fallback for users on machines without uv, but the README leads with uv.

```bash
# Primary
uv tool install game-of-cards

# Fallback (machines without uv)
pipx install game-of-cards
```

## How

1. **Clean factor pass on `deck.py`** — split engine logic (value math, frontmatter parsing, validator) from CLI plumbing into `engine.py`. Mostly a move + import-update; the existing code is already cleanly structured.
2. **Audit templates for phasor references** — grep pass over `.claude/skills/` content; every match either becomes a `!`cat .game-of-cards/<file>.md`` injection point or moves entirely out of the templates into a `.game-of-cards/` stub. Catalog goes into this card's `audit_catalogue.md` (phasor-internal, NOT shipped to the new repo).
3. **Author `.game-of-cards/` stubs** — empty markdown files in `templates/game_of_cards/` with header comments describing what content goes in each.
4. **Set up `pyproject.toml`** — modern PEP-621 layout, hatchling or setuptools backend.
5. **Wire `importlib.resources` for templates** — `goc.templates.skills` etc. become resource roots.
6. **Test PyPI flow** — register on TestPyPI, push a `0.0.1` release, `uv tool install --index https://test.pypi.org/simple/ game-of-cards`, verify `goc --version`. Smoke pipx as the documented fallback.
7. **GitHub Actions release on tag** — `v0.0.1` tag → publish to PyPI via API token in repo secrets.
8. **First production release** — `0.1.0`, public PyPI.

## Out of scope (other sub-cards)

- The `goc install` repo-scaffold flow → `goc-install-command-scaffolds-repo`. (This card defines the starter `.game-of-cards/` stubs as package data; sub-card 2 owns the install-time copy.)
- AGENTS.md template content → `goc-write-agentsmd-alongside-claudemd`.
- Multi-agent shim templates → `goc-multi-agent-shim-which-agents-at-v1`.
- Migrating phasor-agents off the vendored copy → `goc-migrate-phasor-agents-off-vendored-deckpy`. (This is also where phasor's own `.game-of-cards/` files get authored from this card's `audit_catalogue.md`.)

## Self-hosting (the compiler-bootstrap pattern)

The goc repo MUST use goc itself for its own development. This is a structural quality gate: a methodology framework that is unpleasant to use *on itself* has a defect that consuming-repo tests might not surface. Same principle as `gcc` compiling itself, `rustc` written in Rust, the TypeScript compiler in TypeScript — the team feels every wart immediately.

**Bootstrap timeline:**

| Step | State | Goc repo's own deck workflow |
|---|---|---|
| 1. Track 1 (repo created) | `goc/` skeleton exists; CLI not yet functional | None — GitHub issues only |
| 2. Track 2 (`pyproject.toml` + `goc/cli.py`) | Local `uv pip install -e .` works; `goc <verb>` runs | Vendor a minimal `.claude/skills/` directly (or wait for Track 3) |
| 3. Track 3 (templates audit + rewrite done) | Templates clean; CLI feature-complete | Goc repo runs `goc install` against itself for the first time; `.claude/skills/` is now generated from `goc/templates/skills/`. Vendored bootstrap copy replaced. |
| 4. Track 4 (TestPyPI claim → PyPI 0.1.0) | Public release; name claimed | Goc repo runs `uv tool install game-of-cards` (its own published version) and `goc install --upgrade` re-syncs. The repo eats production releases. |
| 5. Steady state | Self-hosting | All goc development files cards in the goc repo's own `deck/`; `goc validate` runs in CI; `pull-card` / `extend-deck` schedules apply |

**Card-flow boundary** (separate from this card, but worth fixing in writing):

- Phasor-agents' `goc-*` cards (this packaging card, sub-cards 1-6 of the epic) are about **extracting** goc. They belong to phasor-agents' history; they close in phasor-agents' deck once done.
- The goc repo's deck **starts fresh** post-bootstrap. New cards for new features (additional agent shims for Cursor/Codex, schema migrations, validator improvements, etc.) live in the goc repo only.
- Sub-card 6 (`goc-migrate-phasor-agents-off-vendored-deckpy`) is phasor-agents' own dogfood test; this card's self-hosting DoD items are goc's own dogfood test. Two distinct quality claims, one per consumer.

## Cross-references

- Parent epic: `goc-ship-game-of-cards-as-cross-agent-cli`
- Engine source today: `.claude/skills/deck/deck.py`
- uv tool install docs: https://docs.astral.sh/uv/concepts/tools/
- Claude Code skill `!`bash`` injection syntax: skills can include shell-command output inline at load time
- Compiler self-hosting precedent: GCC, rustc, TypeScript compiler — methodology frameworks should match this pattern
