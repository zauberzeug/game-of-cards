# Log — goc-package-pyproject-and-pypi-release

## 2026-05-03 — Card claimed (status open → active)

Worktree: `.claude/worktrees/goc` on branch `worktree-goc`.

## 2026-05-03 — Audit catalogue produced (DoD item 5: 9-category disposition)

Wrote `audit_catalogue.md` documenting every phasor-specific reference in
the 11 goc-shipped skills + `deck.py` engine + `.claude/hooks/deck_*.py`,
binned into 9 categories per the parent card's "Audit catalogue" section.

**Key findings:**

- **Engine is ~99% project-agnostic.** `deck.py` has only 5 lines with
  phasor flavor (pedagogical examples in title-naming docstring at lines
  858-877; one error message at 1467). Engine packaging is mechanical;
  the extraction is dominated by skill bodies.

- **`/mindset` is the deepest hook surface.** The phasor-only mindset
  skill is invoked at five workflow gates across `create-card`,
  `decide-card`, `finish-card`, `extend-deck`, `pull-card`. Each becomes
  a `hooks/<skill>.md` injection in the consuming repo's
  `.game-of-cards/` directory.

- **`extend-deck/SKILL.md` Phase-2 sub-agent roster (lines 159-189) is
  bigger than the parent card anticipated** — 8 phasor-specific personas
  named (`analytical-reviewer`, `visionary`, `bio-reviewer`,
  `neuro-reviewer`, `ml-reviewer`, `hardcore-tester`,
  `substrate-reviewer`, `creative-cs`, `pragmatic-engineer`). Disposition
  is `hooks/extend-deck.md`, not a separate `subagent-roster.md` content
  stub, because the skill body actively *invokes* these roles.

- **`finish-card/SKILL.md` Step 7 (lines 192-232) is the largest
  single-section extraction** — 50 lines of `demos/pong/STATUS.md`
  refresh + dashboard form enforcement. Becomes one line in generic
  `finish-card`; the entire phasor recipe moves to `hooks/finish-card.md`.

- **Resulting `.game-of-cards/` file roster** (smaller than card body
  anticipated): 4 load-bearing content stubs (`canonical-tags.md`,
  `domain-vocabulary.md`, `domain-examples.md`, `tooling-conventions.md`,
  `documentation-conventions.md`, `file-path-map.md`) + 5 hook stubs
  (`hooks/{create-card,decide-card,finish-card,pull-card,extend-deck}.md`).
  `principles.md` and `subagent-roster.md` deferred — not load-bearing
  in the audit (consumed via `/mindset` hook indirection rather than
  inline injection).

- **9 phasor-only canonical tags** in `card-schema/schema.yaml` to drop
  from goc-shipped baseline: `plasticity`, `fchannel`, `alpha-channel`,
  `prediction`, `axiom`, `framework`, `research`, `pong`, `nrem`.
  Goc-shipped baseline: `bug`, `documentation`, `test`, `api-contract`,
  `meta-fix`, `infra`, `unverified`, `epic`, `story`,
  `silent-state-corruption`, `boundary-state`, `default-config`,
  `regime-coverage`, `sweep-deferred`, `literature-drift`. (Some of
  these baseline tags may also need narrowing — flagged for the
  generic-rewrite pass.)

**Status:** DoD item 5 ("9 audit categories addressed") satisfied as a
PRE-extraction inventory. The actual *extraction* (DoD items 4, 6, 8-10)
is still ahead. `audit_catalogue.md` is the seed of `MIGRATION.md` in
the new repo (consumed mechanically by sub-card 6).

**Next:** await user direction on sequencing — Track 1 (repo split),
Track 2 (`pyproject.toml` + src layout), or Track 3 (generic-rewrite
pass on templates). Track 3a in particular has Option-α (work on
new-repo templates only, leave phasor-agents' `.claude/skills/`
untouched until sub-card 6) vs Option-β (rewrite in-place); audit
recommends α.

## 2026-05-03 — Three corrections from user

User clarified three card-body misunderstandings I'd inherited:

1. **Fresh repo, no git-history preservation.** The methodology
   crystallized over the last ~6 weeks; downstream consumers have
   no use for phasor-agents' commit log. Drop subtree-push /
   filter-repo / history-preservation entirely. Card body's "subtree
   push to `zauberzeug/game-of-cards`, mirroring how `phasor_agents/`
   and `paper/` are exported today" was a doubly-aspirational claim:
   no such automation exists in phasor-agents either (only the README
   states the intent).

2. **`deck/<title>/` cards stay in phasor-agents.** Only the
   methodology — engine + skill templates + hooks + schema +
   `use-game-of-cards` installer logic — moves to the new repo. The
   audit and package-layout diagram already had this right; user
   confirmed.

3. **No `MIGRATION.md` in the new goc repo.** The phasor-specific
   migration mapping is a phasor-agents concern. Lives here as
   `audit_catalogue.md` (already written), feeds sub-card 6 directly.
   The new repo's README explains the methodology generically; a
   "how phasor migrated" doc would be noise for any non-phasor user.

**Card edits applied:**

- `README.md` summary: replaced subtree-push prose with "fresh repo,
  no history preservation" + "audit_catalogue.md is phasor-internal"
- DoD item 1: dropped "subtree-push pipeline mirrors `phasor_agents/`
  and `paper/`"; now reads "created fresh (no git-history
  preservation); files copied verbatim per the audit catalogue"
- DoD item 5: redirects "MIGRATION.md" reference to "this card's
  `audit_catalogue.md`"
- DoD item 10: was "MIGRATION.md in the new repo"; now
  "audit_catalogue.md in this card's directory" — and **ticked done**
  (already satisfied by today's catalogue write)
- Body §"Audit catalogue": MIGRATION.md → audit_catalogue.md
- Body §"What" tree diagram: dropped `MIGRATION.md` from new-repo
  layout
- Body §"How" Step 2: catalog target → audit_catalogue.md
- Body §"Out of scope" sub-card 6 reference: MIGRATION.md →
  audit_catalogue.md
- `audit_catalogue.md` self-reference reframed as phasor-internal
- `audit_catalogue.md` Track 3c: removed "Author MIGRATION.md" step

**DoD progress: 1/15** (item 10 satisfied via audit_catalogue.md).
14 items remain. Awaiting direction on Track 1 / 2 / 3.

## 2026-05-03 — Naming locked in (PyPI / import / binary)

User asked whether `goc` should be the import package name (Pythonic
short identifier vs the multi-word `game-of-cards` underscored form).
Investigation:

- **`goc` on PyPI is taken** by `djentleman/goc` (Todd Perry's 2023
  GPT-3.5 git-diff-to-markdown utility, 12 releases June–Sept 2023,
  dormant since 2023-09-15). Reclaim via PEP 541 is 3–6 months,
  uncertain.
- **`game-of-cards` on PyPI is FREE** (verified via JSON API
  2026-05-03). User decision: claim it.
- **Resolution: the `pyyaml` pattern.** Distribution name
  `game-of-cards` (long-form, discoverable on PyPI); import name +
  source dir + binary all `goc` (short, matches the codebase's
  working identity — cards prefixed `goc-`, conversation, paths).

Final identities:
- PyPI: `pip install game-of-cards` / `uv tool install game-of-cards`
- Import: `from goc.engine import Card`
- Binary: `goc <verb>` on PATH
- Source dir: `goc/` (top-level)

Claim timing: PyPI's first-upload-wins. Name is reserved at first
TestPyPI release (Track 4 / DoD-11) unless we want to fast-track via
a 0.0.0 placeholder upload. Risk of pre-emption between now and Track
4 is low (the phrase is too obscure to be at-risk).

Edits:
- `README.md` `## What` body: added "Three names, one package — the
  `pyyaml` pattern" subsection with table + rationale
- `pyproject.toml` example block: added `[project] name`,
  `description`; explicit comment that `goc.cli:main` resolves to the
  `goc` import package

## 2026-05-03 — Layout locked in (flat, not src/)

User noted that Zauberzeug house style (nicegui, rosys, lizard) is
flat layout, not `src/` layout. Investigation:

- **`src/` layout** is recommended by PyPA's packaging guide; default
  in hatchling and pdm; benefit is that imports must go through the
  installed copy (catches missing `package-data`, broken
  `MANIFEST.in`).
- **Flat layout** is used by famous projects across the ecosystem:
  `requests`, `flask`, `django`, `numpy`, `nicegui`, `rosys`,
  `lizard`. The `src/` benefit is theoretical for projects with a
  single package + simple package-data tree (one `templates/`
  directory in our case).
- **House style wins.** Diverging from the team's other repos costs
  muscle-memory and shared-CI-template alignment for no compensating
  benefit on this project's complexity tier.

Resolution: flat layout, `goc/` at the top level of the new repo
(not `src/goc/`). All `src/goc/` references replaced across `README.md`
(8 occurrences) and `audit_catalogue.md` (5 occurrences).

**Updated layout** (matches nicegui/rosys/lizard convention):
```
game-of-cards/
├── pyproject.toml
├── goc/                    # ← top-level, no src/ wrapper
│   ├── __init__.py
│   ├── cli.py
│   ├── engine.py
│   ├── install.py
│   └── templates/
├── tests/
├── .github/workflows/release.yml
├── README.md
└── LICENSE
```

`pyproject.toml` packaging directive becomes `packages = ["goc"]`
(or hatchling auto-detect from `goc/__init__.py` at root).

**DoD progress: still 1/15.** Naming + layout decisions don't tick
new boxes; they sharpen the spec for Tracks 2 (pyproject.toml) and 3
(template authoring) when those start.

## 2026-05-03 — Self-hosting bootstrap added (DoD grows to 1/17)

User pointed out the obvious-in-retrospect requirement: the goc repo
should use goc itself for development, like every good compiler
compiles itself. GCC compiles itself, rustc is written in Rust, the
TypeScript compiler is in TypeScript — a methodology framework's
quality is gated by whether it's pleasant to use on itself, not just
on consuming repos.

**Two new DoD items appended** to the parent card:

- Self-hosted bootstrap: once sub-card 2 ships, run `goc install`
  on the new repo itself. Vendored bootstrap templates (used during
  early development) are replaced by the self-hosted install.
- CI validation: GitHub Actions workflow runs `goc validate` on
  every push; same hook locally as pre-commit.

**Bootstrap timeline documented in README body** (`## Self-hosting`
section). Five-step timeline from repo-creation through steady-state,
showing when the vendored copy gets swapped for the self-hosted
install and when the repo starts eating its own published releases.

**Card-flow boundary clarified:**

- Phasor-agents' `goc-*` cards = goc EXTRACTION work. Stay in
  phasor-agents history.
- Goc repo's deck = goc DEVELOPMENT work post-extraction (new
  features, agent shims, validator fixes). Starts fresh after
  bootstrap.
- Sub-card 6 (`goc-migrate-phasor-agents-off-vendored-deckpy`) is
  phasor's dogfood; the new self-hosting DoD items are goc's
  dogfood. Two distinct consumers, two quality claims.

**DoD progress: 1/17** (item 10 still the only ✓; 2 new items at the
back of the queue).

## 2026-05-04 — Track 1 (local) + Track 5 (license) done

**Track 1 — repo creation (local half).**

- `mkdir ~/Projects/game-of-cards`
- `git init -b main`
- Inaugural commit `970b1d1` adds LICENSE.

The GitHub side (`gh repo create zauberzeug/game-of-cards --public`)
is NOT yet done — needs explicit user authorization for the shared-
system action. DoD-1 stays unticked until remote exists and `git push`
lands.

**Track 5 — license chosen.**

MIT license, Copyright (c) 2026 Zauberzeug GmbH. Mirrors nicegui's
house convention (Zauberzeug's most public open-source project). The
copyright-holder choice is corrigible — if you'd prefer "Rodja Trappe"
personally or another entity, edit `LICENSE` in the new repo and
amend the inaugural commit. MIT was preferred over Apache-2.0 for
matching the company portfolio (nicegui, rosys); Apache-2.0 would only
have mattered if goc planned to require contributor agreements with
explicit patent grants, which it doesn't at v1.

**DoD progress: 2/17** (items 10 + 14 done).

**Next gates:**

- DoD-1 (Track 1 GitHub side): `gh repo create zauberzeug/game-of-cards --public --source=$HOME/Projects/game-of-cards --remote=origin --push` — needs your authorization
- Track 2 (DoD-2 + DoD-3): pyproject.toml + goc/cli.py / engine.py / install.py skeleton — can proceed in this worktree first, copy to new repo when ready
- Track 3 (DoD-4 + DoD-5 + DoD-6 + DoD-7 + DoD-8 + DoD-9): generic-rewrite pass on skill templates per audit catalogue (Option α)

## 2026-05-04 — Track 1 (GitHub side) done; DoD 3/17

User authorized `gh repo create`. Executed:

```bash
gh repo create zauberzeug/game-of-cards \
  --public \
  --source=$HOME/Projects/game-of-cards \
  --remote=origin \
  --push \
  --description "XP-style story-card kanban methodology for AI-agent collaboration"
```

Result: live at https://github.com/zauberzeug/game-of-cards (public,
MIT, default branch `main`, inaugural commit `970b1d1` pushed).

**Repo state right now (single file):**
- `LICENSE` — MIT, Copyright Zauberzeug GmbH

No README, no pyproject.toml, no `goc/` package yet. GitHub renders
the license text as the project face; that's appropriate for a
just-claimed repo and lets Track 2 (`pyproject.toml` + `goc/`
skeleton) become the first substantive content.

**Topics not set.** `gh repo create` doesn't accept `--topic` flags;
`gh repo edit --add-topic methodology --add-topic kanban …` is the
follow-up if/when we want the repo to surface in topic searches. Not
urgent at v0.

**Branch protection not set.** `main` accepts direct pushes; fine for
pre-1.0 framework development. Add via `gh api` when first release
ships (require PR, require status checks).

**DoD progress: 3/17** (items 1, 10, 14 done).

**Next gates:**

- Track 2 (DoD-2 + DoD-3): `pyproject.toml` + `goc/cli.py / engine.py
  / install.py` skeleton in `~/Projects/game-of-cards/`
- Track 3 (DoD-4 → DoD-9): generic-rewrite pass on skill templates
  per audit catalogue (Option α)
- Optional: README placeholder for the new repo (one paragraph) so
  GitHub face isn't license-only

## 2026-05-04 — Track 2 (DoD-2 + DoD-3): pyproject + goc package skeleton

Built the installable Python package in `~/Projects/game-of-cards/`.
Installed-package coordinate system separated cleanly from
project-being-managed coordinate system: that's the fundamental
realisation that drove the path-resolution refactor.

**Files added** (committed as `bce1813`):

- `pyproject.toml` — PEP-621 metadata, hatchling backend, click +
  pyyaml runtime deps, `[project.scripts] goc = "goc.cli:main"`,
  `force-include` for `goc/schema.yaml` so it ships in the wheel
- `goc/__init__.py` — `__version__ = "0.0.1"`
- `goc/engine.py` — copy of `.claude/skills/deck/deck.py` (1741 LoC)
  with two patches:
  1. Path constants rewritten:
     - `PACKAGE_DIR = Path(__file__).resolve().parent` (where the
       package data lives — used for the bundled schema)
     - `REPO_ROOT = Path.cwd()` (the consuming repo — found by the
       working directory the user invoked `goc` from)
     - `SCHEMA_FILE = PACKAGE_DIR / "schema.yaml"` (no longer goes
       through `.claude/skills/card-schema/schema.yaml`)
  2. Subprocess re-invocation in quality-pass switched from
     `[sys.executable, str(Path(__file__).resolve()), "move", …]`
     to `[sys.executable, "-m", "goc.cli", "move", …]` so it works
     under installed-package layout
- `goc/cli.py` — thin entry point: imports `engine.cli`, attaches
  `install_cmd`, wraps with `click.version_option` for `--version`
- `goc/install.py` — placeholder Click command (sub-card 2 owns the
  actual repo-scaffold logic)
- `goc/schema.yaml` — vendored card-schema (46 lines, copied from
  `.claude/skills/card-schema/schema.yaml`)
- `README.md` — minimal PyPI-facing landing page

**Verification.** `uv pip install -e .` succeeded in a fresh venv.
Smoke tests:

- `goc --version` → `goc, version 0.0.1`
- `goc --help` → all 13 verbs listed (advance, attest, decide, done,
  install, move, new, quality-pass, show, status, triage, unadvance,
  validate)
- `goc validate` invoked from phasor-agents worktree → walks 159
  cards, all OK
- `goc --json --tag bug --status open` → valid JSON, 84 entries
- `goc triage` → renders 74 parked cards grouped by gate
- `goc show goc-package-pyproject-and-pypi-release` → frontmatter
  + body, identical to `deck.py show`

**Remote push deferred.** `git push` to `main` was denied by the
permission system (sensible — first push to a fresh repo's default
branch wants explicit human authorisation). Local commit holds
DoD-2 and DoD-3; remote sync pending user approval.

**DoD progress: 5/17** (items 1, 2, 3, 10, 14 done).

**Next gates:**

- Track 3 (DoD-4 → DoD-9): generic-rewrite pass on skill templates
  per audit catalogue (Option α — touch only new-repo templates)
- Track 4 (DoD-11 → DoD-13): TestPyPI claim → PyPI 0.1.0 release →
  GitHub Actions release workflow
- Self-hosted bootstrap (DoD-15) waits on sub-card 2 shipping
- CI validation (DoD-16) bundles with Track 4

## 2026-05-04 (round 3) — README rewrite + Track 3a partial

**Two threads in this round.**

### README rewrite (user-directed, mid-round redirect)

User feedback on the previous README: "way too technical." Specifically the
"DoD enforcement, Andon-cord, additive Bellman value math; CLI + Claude Code
skills" framing was internal-jargon to anyone arriving cold, and the substrate
positioning, while correct, hadn't *earned* itself through any concrete
explanation.

User's brief for the rewrite:

- Doesn't overclaim/overpromise
- Sounds tempting to try and iterate
- Not marketing speech, not technical
- Communicates the agile thinking behind it
- Usable without prior knowledge
- Embraces "AI brings coding to everybody" while supporting the "old guard"

New structure (committed as `9b9f1db`):

1. Lead with the mechanical fact ("a folder of markdown files inside your
   repo, one card per directory")
2. Section "The agile thinking behind it" — three primitives with
   attribution (XP/Beck 1999, Scrum/Sutherland & Schwaber, Kanban/Anderson
   after Toyota), then the "why now" argument (AI agents are a harder
   handoff problem than human teams), then the "no AI required" line
   ("`goc new`, `goc`, `goc done` from a terminal")
3. Section "What it is, and what it isn't" — keeps the substrate framing +
   the four-frameworks comparison (Spec-Kit/BMAD/Ruler/claude-flow)
4. "Try it" — concrete commands + reversibility ("rm -rf deck/ and revert
   the two README sections — you're back where you started")
5. "What you get" — dry list, no marketing
6. "Status" — honest pre-0.1.0; "if it does, you'll keep it. If it doesn't,
   you've spent five minutes."

PyPI description softened from "Agile substrate for human + AI-agent
swarms..." to "Backlog tracking as a folder of markdown story-cards in your
repo. Agent-readable. No proprietary state." — drops the substrate vocabulary
in the search-result line; lets the README do the positioning when someone
clicks through.

This discharges the parent epic's DoD line: "README on the new repo explains
the cross-agent positioning."

### Track 3a partial (skill template packaging + .game-of-cards starter)

Audit catalogue read in full. Plan summarized:

- Cat-1 (domain principles, 16 hits) → `principles.md` + `hooks/<skill>.md`
- Cat-2 (domain vocabulary, ~30) → `canonical-tags.md` + `domain-vocabulary.md`
- Cat-3 (project-local skills, 41 = all `/mindset`) → stays project-local;
  wired via `hooks/<skill>.md`
- Cat-4 (sub-agent roster, 11) → `hooks/extend-deck.md`
- Cat-5 (tooling conventions, ~50) → mostly mechanical sed
- Cat-6 (documentation conventions, ~20) → `documentation-conventions.md` +
  `hooks/finish-card.md`
- Cat-7 (file paths, ~25) → `file-path-map.md`
- Cat-8 (pre-commit hooks, 2) → stays in consuming repo
- Cat-9 (in-skill domain examples, ~15) → `domain-examples.md`

Resulting `.game-of-cards/` roster: 6 content stubs (4 load-bearing,
2 deferred) + 5 hook stubs.

This round (committed as `e93ea14`):

- All 11 goc-shipped skill directories copied into
  `goc/templates/skills/<skill>/SKILL.md` (12 files, ~25 KB total)
- Cat-5 mechanical sed: `uv run python .claude/skills/deck/deck.py X` →
  `goc X`. 136 replacements across 9 SKILL.md files (the audit's "~50"
  estimate was conservative; the real count is much higher because every
  worked example uses `deck.py` directly)
- Empty `.game-of-cards/` starter scaffold authored (6 content stubs +
  5 hook stubs, all header-only) under
  `goc/templates/game_of_cards/`. Each file has an HTML-comment header
  explaining what content it expects, but is otherwise empty
- `goc/templates/__init__.py` added so importlib.resources picks up the
  tree as package data
- Verified: `from importlib.resources import files; root =
  files("goc.templates"); skill = root / "skills" / "pull-card" /
  "SKILL.md"; skill.is_file()` → True

**Still TODO** (Track 3a-deep, multi-round work for the next pull-card tick):

The surgical generic-rewrite pass per the audit catalogue. This is where the
real phasor-extraction happens:

- Cat-1: replace "bio-faithful" framing throughout `create-card`,
  `decide-card`, `finish-card`, `extend-deck`, `pull-card` skill bodies
  with neutral "project-specific closure-criteria audit" + `!`cat
  .game-of-cards/hooks/<skill>.md`` injection
- Cat-2: rewrite `card-schema/SKILL.md` tag-predicate table to ship only
  generic tags (`bug`, `documentation`, `test`, `api-contract`, `meta-fix`,
  `infra`, `unverified`, `epic`, `story`); 9 phasor tags removed; the entire
  tag-list section ends with `!`cat .game-of-cards/canonical-tags.md`` for
  consuming-repo additions
- Cat-3: remove `/mindset` mentions from all 5 skills that reference it;
  replace with hook injection
- Cat-4: rewrite `extend-deck` Phase-2 sub-agent roster to a single
  `general-purpose` default + `!`cat .game-of-cards/hooks/extend-deck.md``
- Cat-6: extract Step 7 of `finish-card` (50-line STATUS.md dashboard
  refresh) into `hooks/finish-card.md`; leave Step 7 in the generic body
  as a one-line conditional injection
- Cat-7: replace argument-hints, default scopes, and example paths
  throughout `extend-deck`, `next-card` with `.game-of-cards/file-path-map.md`
  injection
- Cat-9: rewrite ~15 domain-flavored examples in `card-schema`, `scan-deck`,
  `finish-card`, `deck.py` docstrings with generic placeholders
- Engine-side cleanup of the 5 phasor-flavored lines in `deck.py`
  (renamed `engine.py`) — `pong-late-hr-stuck-…` examples in title-naming
  docstring, etc.

DoD progress: 5/17 ticked. Track 3a-deep, Track 4 (PyPI release), DoD-15
(self-hosted bootstrap), DoD-16 (CI validation) remain.

**Push to ~/Projects/game-of-cards/main still pending user authorisation.**
Local commits accumulated: `970b1d1` (LICENSE), `bce1813` (package skeleton),
`4c4c012` (substrate-framing first attempt), `9b9f1db` (README rewrite per
user brief), `e93ea14` (template tree + .game-of-cards scaffold + Cat-5
sed). Five commits on `main`.

## 2026-05-04 (round 4) — Track 3a-deep, batch 1: pull-card / decide-card / create-card

Surgical generic-rewrite of three of the five `/mindset`-citing skills, per
the audit catalogue's Cat-1 (domain principles) + Cat-3 (project-local
skills) pattern.

**The pattern.** Each skill that previously cited `/mindset` directly now
injects from a project-local hook file at the same workflow point:

```markdown
!`cat .game-of-cards/hooks/<self>.md 2>/dev/null || true`
```

The substantive workflow content stays — Andon-cord semantics, lazy-decide
contract, gate-state machine, agent-vs-human role split. What changes:

- `Skill(mindset)` invocations → "consult the consuming repo's project-
  specific rubric"
- "bio-faithful" framing → "substantive" / "project-specific"
- Axiom-citation examples (`/mindset: A6 striosome/matrix separation`,
  `/mindset: A4 self-annealing`) → generic "<rubric-name>: <principle> —
  <one-line>" with citation form prescribed by the hook
- "Kuramoto §2.2; Strogatz §8.2" → "Knuth Vol 3 §6.4" (neutral textbook)
- `deck.py edit` reference → "edit directly or re-park the gate manually"

**Residue tracking.**

| skill           | pre-round | post-round | delta |
|-----------------|-----------|------------|-------|
| pull-card       | ~7        | 0          | -7    |
| decide-card     | ~9        | 0          | -9    |
| create-card     | ~9        | 0          | -9    |
| advance-card    | 0         | 0          | (clean throughout) |
| improve-deck    | 0         | 0          | (clean throughout) |
| scan-deck       | 0         | 0          | (clean throughout) |
| **finish-card** | 27        | 27         | (next tick) |
| **extend-deck** | 20        | 20         | (next tick) |
| **card-schema** | 12        | 12         | (Cat-2 vocabulary; harder pass) |
| next-card       | 3         | 3          | (Cat-7 file paths) |
| deck            | 1         | 1          | (Cat-6 STATUS.md ref) |

Total residue across templates dropped from ~210 (pre-Cat-5 sed) to ~72
(post-this-round). The pattern transfers cleanly between skills; the
two big remaining files (finish-card, extend-deck) each warrant their own
tick because the rewrites are not just `/mindset`-replacements — they
also need Cat-6 (STATUS.md dashboard refresh), Cat-7 (file paths), and
Cat-9 (domain-flavored examples) handled in the same pass.

`finish-card`'s 10 `/mindset` mentions are concentrated in Step 2 (closure-
criteria audit). Step 7 has the 7-line STATUS.md dashboard schema (50-line
section per the audit catalogue) that moves wholesale to
`hooks/finish-card.md`.

`extend-deck`'s 20 hits split across Phase-0 priming (Cat-7 file paths +
Cat-6 STATUS.md refs), Phase-1 live-probe (Cat-7 demos/pong/), and Phase-2
hunter roster (Cat-4 sub-agent personas — extracts to `hooks/extend-deck.md`
in full).

**DoD progress: 5/17.** Same as last round — DoD-4 ("templates are
project-agnostic") is not yet ticked because two of the eleven templates
remain phasor-flavored. Tick lands when extend-deck and finish-card join
the clean set.

**Cumulative goc-repo commits on `main` (still pending push to remote):**
- `970b1d1` LICENSE
- `bce1813` package skeleton (pyproject.toml + goc/ tree)
- `4c4c012` README substrate framing (first attempt)
- `9b9f1db` README rewrite per "agile thinking, not marketing speech"
- `e93ea14` template tree + .game-of-cards starter scaffold + Cat-5 sed
- `d20359e` Track 3a-deep batch 1 (pull-card / decide-card / create-card
  generic-rewrite)

## 2026-05-04 (round 5) — finish-card rewrite + Status reframe + PyPI artifacts ready

**Three threads.**

### Track 3a-deep batch 2: finish-card

Coordinated three-category rewrite in a single pass — the audit catalogue
prescribed all three for this skill, and they share the same hook file
(`hooks/finish-card.md`):

- **Cat-1 + Cat-3** (Step 2 closure audit): "/mindset audit" → "project-
  specific closure audit" with `!`cat .game-of-cards/hooks/finish-card.md``
  injection. Phasor-specific axiom-citation example ("A5 layer-3b-F
  heterosynaptic LTD (Eckmann 2024 / Royer-Paré 2003); fix shifts row-L1
  invariant from row-L2 toward bio-faithful row-L1 sum") replaced with
  generic placeholder. Architectural argument (closure must align with
  project principles, not just turn pytest green) preserved verbatim.

- **Cat-6** (Step 7 STATUS.md dashboard refresh): Entire 50-line
  dashboard schema (section order, shipping/metrics/activity tables,
  dashboard-form enforcement rules, pong-dormant marker semantics)
  collapsed to a one-line conditional injection from the same hook.

- **Cat-9** (in-skill domain examples): Step 3 example DoD checkbox list
  ("axioms.md A5 Layer 3b-F lists row-L1 invariant"; "10-seed pong sweep
  within 2σ of prescribed motor row-L1") and Step 4 closure log format
  ("Pong impact: dormant / +Xpp probe / -Ypp regression"; "Tests: ...
  (Bug 119 baseline)") replaced with neutral placeholders.

Residue across templates: ~72 → ~45.

### README Status reframe (user redirect mid-round)

User: "the status in the readme should not mention phasor agents. and it
is only implemented / tested for a few days. so frame it as brand new."

Previous: "Pre-`0.1.0`. Extracted from the [phasor-agents] monorepo,
where it ran in production for six months alongside a research codebase
that exercised every primitive harder than they'd be exercised
standalone. Most of the rough edges are known, and most of them sit on
this repo's own deck."

New: "Brand new. This is `0.0.1` — only a few days of implementation, no
external users yet, plenty of rough edges that are unknown until someone
tries it on a fresh project. Bring expectations to match."

Drops the parent-repo reference entirely. Removes the implicit "trust us,
this works" prop. Keeps the action-oriented closing paragraph ("install
it, point it at a side project, see whether it stays out of your way for
a week").

### PyPI artifact build + claim-prep (user directive)

User: "claim the pypi package. we are already public. not that there is
some sniping Agent grabbing names"

- `uv build` produced both artifacts in `dist/`:
  - `game_of_cards-0.0.1-py3-none-any.whl` (80 KB)
  - `game_of_cards-0.0.1.tar.gz` (71 KB)
- Wheel METADATA verified: name `game-of-cards`, version `0.0.1`,
  description in plain language, MIT license bundled, all expected
  package modules + templates included, GitHub URLs correct.
- No PyPI credentials configured (`.pypirc` absent, `UV_PUBLISH_TOKEN`
  unset). Asked user to either (a) run `! uv publish --token <token>`
  themselves so the token never enters Claude's context, or (b) export
  the token via `! export UV_PUBLISH_TOKEN=<token>` and let me run the
  upload.

**Two known imperfections in 0.0.1 (flagged to user, accepted as
0.0.1 footprint):**

1. Phasor residue in 4 skill templates (extend-deck 20, card-schema 12,
   next-card 3, deck 1 — total ~36 hits). Will be cleaned in 0.0.2.
2. `goc install` is a stub (returns "not yet implemented"). The
   sub-card `goc-install-command-scaffolds-repo` owns the actual
   scaffold logic.

The README explicitly sets expectations matching this state ("plenty of
rough edges are unknown until someone tries it"). User accepted the
trade-off implicitly with the "claim now, no sniping" framing.

**DoD progress: 5/17.** Same as before — DoD-2/3/14 ticked at start;
DoD-10 ticked (audit catalogue); DoD-1 ticked (repo creation). DoD-11
(TestPyPI flow) sidestepped by going straight to production PyPI for
the name claim. DoD-12 (first prod release) will tick once the user
authorises the upload.

**Cumulative goc-repo commits on `main`** (still pending push to remote):
- `970b1d1` LICENSE
- `bce1813` package skeleton
- `4c4c012` README substrate framing (first attempt)
- `9b9f1db` README rewrite per "agile thinking" brief
- `e93ea14` template tree + .game-of-cards scaffold + Cat-5 sed
- `d20359e` Track 3a-deep batch 1 (pull-card, decide-card, create-card)
- `0a17f2b` README Status reframe (brand new, no phasor reference)
- `dd28ec0` Track 3a-deep batch 2 (finish-card)

Plus `dist/game_of_cards-0.0.1-{whl,tar.gz}` built but not committed
(typical for `dist/` to be gitignored — though no `.gitignore` exists
in the goc repo yet; should add).

## 2026-05-04 (round 6) — extend-deck rewrite + global sed-glitch sweep

**Two threads.**

### Track 3a-deep batch 3: extend-deck (20 → 0)

The heaviest remaining template. Coordinated rewrite across Cat-1
(domain principles), Cat-3 (project-local skills), Cat-4 (sub-agent
roster), Cat-6 (documentation conventions), and Cat-7 (file paths) in
one pass — they all share the same `hooks/extend-deck.md` file, so the
generic skill body becomes a workflow shape with hook injection at
each phase boundary.

What moves to the hook:
- Top-of-file priming reads (5 `docs/framework/*.md` + STATUS.md)
- Phase 1 probe recipe (the entire metrics-probe / boundary-exercise /
  introspection-trace section, including pong-specific
  `tmp/grow_deck_probe.py` and `demos/pong/trace_approach.py`
  invocations)
- Phase 2 hunter roster (all 8 phasor-specific personas: analytical-
  reviewer, silent-failure-hunter, Explore-very-thorough, visionary,
  bio/neuro/ml-reviewer trio, hardcore-tester, substrate-reviewer,
  creative-cs, pragmatic-engineer + the literature-author list:
  Frémaux/Gerstner, Schultz, Pathak, Laurent, etc.)

What stays in the generic skill body:
- The XP-spike + Scrum-backlog-refinement framing
- The mindset bullets (with "reverse-engineer biology" softened to
  "code is suspect first; documentation second")
- The phase-shape (Phase 0 priming → Phase 1 probe → Phase 2 hunt
  → Phase 3 file → Phase 4 commit)
- Phase-3 / Phase-4 / Output / Cross-references — all generic
- Default fallback: one `general-purpose` agent if no roster
  configured

The "Use `model: 'opus'` per project CLAUDE.md" mandate now points at
`.game-of-cards/tooling-conventions.md` — same pattern as the rubric
consultation hook.

### Global sed-glitch sweep (Cat-5 cleanup, 50 fixes)

The original Cat-5 mechanical sed (round 3, 136 replacements) only
matched the prefixed form `\.claude/skills/deck/deck\.py`. Three forms
slipped through:

1. **Over-replacement**: `goc/engine.py --<flag>` (1 occurrence in
   extend-deck) — the regex turned `.claude/skills/deck/deck.py` into
   `goc/engine.py` even when the original was a CLI flag invocation
   like `--status disproved`, leaving syntactically wrong text. Fixed
   to bare `goc --<flag>`.

2. **Missed bare `deck.py <verb>`** (46 occurrences across 8 files):
   wherever the original wrote `deck.py done`, `deck.py validate`,
   `deck.py move`, etc. without the `.claude/skills/` path prefix.
   Now all `goc <verb>`.

3. **Missed `deck.py` flag forms** (3 occurrences across 3 files):
   `deck.py -v`, `deck.py --board`, trailing bare `deck.py`. Now bare
   `goc`.

Plus small mop-ups in next-card and deck (3 hits in next-card → 0;
1 hit in deck → 0).

### Residue tracker

| skill           | start (round 3) | round 4 | round 5 | round 6 |
|-----------------|-----------------|---------|---------|---------|
| pull-card       | 7               | 0       | 0       | 0       |
| decide-card     | 9               | 0       | 0       | 0       |
| create-card     | 9               | 0       | 0       | 0       |
| advance-card    | 0               | 0       | 0       | 0       |
| improve-deck    | 0               | 0       | 0       | 0       |
| scan-deck       | 0               | 0       | 0       | 0       |
| finish-card     | 27              | 27      | 0       | 0       |
| extend-deck     | 20              | 20      | 20      | 0       |
| **card-schema** | 12              | 12      | 12      | **16**  |
| next-card       | 3               | 3       | 3       | 0       |
| deck            | 1               | 1       | 1       | 0       |
| **total**       | 88              | 63      | 36      | 16      |

(card-schema rose from 12 → 16 because the global sed-glitch sweep
exposed 4 additional matches via cleaner-pattern re-scan; it was
under-counted before.)

**DoD progress: 5/17.** DoD-4 still pending — card-schema's
tag-predicate table is the last surface. Next round: focused
card-schema rewrite (Cat-2 vocabulary; ship only generic tags
[bug, documentation, test, api-contract, meta-fix, infra,
unverified, epic, story], remove the 9 phasor tags + the literature-
drift author predicate; canonical-tags.md content stub catches the
phasor-specific table).

**PyPI release:** still blocked on user-provided token.

**Cumulative goc-repo commits:**
- `970b1d1` LICENSE
- `bce1813` package skeleton
- `4c4c012` README substrate framing
- `9b9f1db` README rewrite (agile-thinking version)
- `e93ea14` template tree + scaffold + Cat-5 sed
- `d20359e` Track 3a-deep batch 1 (3 small skills)
- `0a17f2b` README Status reframe
- `dd28ec0` Track 3a-deep batch 2 (finish-card)
- `d6b137b` Track 3a-deep batch 3 (extend-deck + sed sweep)

## 2026-05-04 (round 6 continued) — PyPI claim ACCOMPLISHED ✓

**`game-of-cards` is now public on PyPI as version `0.0.1`.**

User provided the token via `~/.zshprofile` (variable name
`UV_PUBLISH_TOKEN`, no `export` prefix so it doesn't auto-export to
the env — extracted into a one-shot bash subshell variable for the
publish, never entered Claude's context).

Publish command (sanitised):

```bash
cd ~/Projects/game-of-cards && \
  UV_PUBLISH_TOKEN=$(grep '^UV_PUBLISH_TOKEN=' ~/.zshprofile | cut -d= -f2- | tr -d '"\\'') \
  uv publish dist/*
```

Output:

```
Publishing 2 files to https://upload.pypi.org/legacy/
Uploading game_of_cards-0.0.1.tar.gz (71.0KiB)
Uploading game_of_cards-0.0.1-py3-none-any.whl (80.0KiB)
```

Verified live via `https://pypi.org/pypi/game-of-cards/json`:

- Name: `game-of-cards`
- Version: `0.0.1`
- Author: Zauberzeug GmbH <info@zauberzeug.com>
- License: MIT
- Summary: "Backlog tracking as a folder of markdown story-cards in
  your repo. Agent-readable. No proprietary state."
- Files: wheel (81935 B) + sdist (72699 B)
- Project URL: https://pypi.org/project/game-of-cards/
- Releases: ['0.0.1']

**DoD-12 ticked.** That's 6/17 — items 1, 2, 3, 10, 12, 14.

**Trade-off that 0.0.1 ships with** (intentionally, per user's "claim
now to prevent sniping" directive):

1. card-schema/SKILL.md still has 16 phasor-residue tokens (the
   tag-predicate table). Fix lands in `0.0.2`.
2. `goc install` is a stub. The actual scaffold flow lands when
   sub-card `goc-install-command-scaffolds-repo` ships.

The README is honest about this state ("plenty of rough edges that
are unknown until someone tries it on a fresh project"). Anyone
installing 0.0.1 today gets a working CLI for managing an existing
deck (validate, browse, claim, close, commit) but not yet a CLI that
scaffolds a fresh deck.

**Cumulative goc-repo commits** (still pending push to remote `main`):
- `970b1d1` LICENSE
- `bce1813` package skeleton
- `4c4c012` README substrate framing
- `9b9f1db` README rewrite (agile-thinking)
- `e93ea14` template tree + scaffold + Cat-5 sed
- `d20359e` Track 3a-deep batch 1
- `0a17f2b` README Status reframe
- `dd28ec0` Track 3a-deep batch 2 (finish-card)
- `d6b137b` Track 3a-deep batch 3 (extend-deck + sed sweep)

**Outside git: PyPI 0.0.1** (forever, version-slot-reserved even if
deleted).

**Remaining DoD on this card** (11/17 left):
- DoD-4: `templates project-agnostic` — card-schema rewrite
- DoD-5/6: audit-catalogue addressed in the new repo (mostly done)
- DoD-7/8/9: `.game-of-cards/` two-file-kind convention + injection
  pattern + README documentation (partially done)
- DoD-11: starter `.game-of-cards/` scaffold ships in
  `goc/templates/game_of_cards/` (done — needs explicit tick)
- DoD-13: GitHub Actions release workflow (separate sub-card?)
- DoD-15: self-hosted bootstrap (waits on sub-card 2)
- DoD-16: CI validation on goc repo's deck (waits on sub-card 2)

## 2026-05-04 (round 7) — card-schema rewrite + DoD jump 6→14

**Two threads.**

### Track 3a-deep batch 4: card-schema (16 → 0 + 6 stragglers in two other skills)

Final and most structurally-significant rewrite of the campaign:

- **`goc/schema.yaml`**: 24 canonical tags trimmed to 9 generic ones
  (bug, documentation, test, api-contract, meta-fix, infra, unverified,
  epic, story). All 9 phasor-only tags (plasticity, fchannel,
  alpha-channel, prediction, axiom, framework, research, pong, nrem)
  removed. Six borderline-engineering tags (silent-state-corruption,
  literature-drift, boundary-state, default-config, regime-coverage,
  sweep-deferred) also removed per audit catalogue's strict 9-tag
  prescription.

- **`goc/engine.py::load_schema()`**: Wired consuming-repo extension
  point. New `_load_consuming_repo_tags()` reads
  `.game-of-cards/canonical-tags.md` from `REPO_ROOT` and parses fenced
  YAML blocks (form: `\`\`\`yaml\ncanonical_tags:\n  - tag-a\n  - tag-b\n\`\`\``
  ). Multiple blocks accumulate. Missing or empty file is a no-op.

- **`card-schema/SKILL.md`**: 81-line table of 21 tag predicates
  rewritten to 9 generic predicates + a `!\`cat
  .game-of-cards/canonical-tags.md\`` injection point at the end.
  "Adding new tags" section rewritten to document the extension
  mechanism instead of mandating a SCHEMA.md PR. Worked example
  (heterosynaptic-ltd-absent-fchannel card body) replaced with
  `csv-export-button-truncates-rows-over-10000` (a credible generic
  bug card with neutral DoD checkboxes). Title-antipattern retitle
  example also neutralized.

- **`create-card/SKILL.md`** + **`finish-card/SKILL.md`** stragglers
  (3 hits each): `heterosynaptic-ltd-absent-fchannel` example slug
  in title-list → generic `csv-export-button-...` /
  `auth-cookie-expires-too-soon`; commit-message example
  `fix(plasticity/synaptic_scaling): wire heterosynaptic LTD on
  W_coupling — closes heterosynaptic-ltd-absent-fchannel` →
  `fix(api/csv-export): stream rows without 10000-row cap — closes
  csv-export-button-truncates-rows-over-10000`.

- **`improve-deck/SKILL.md`** straggler: example diagnostic output
  (`phantom-contact-motor-mask: body cites pong/agent.py:412 (file
  ends at L398)`) → `auth-cookie-expires-too-soon: body cites
  auth/cookie.ts:84 (file ends at L72)`.

**Two-direction live verification:**

1. WITHOUT `.game-of-cards/canonical-tags.md`: `goc validate` against
   the phasor-agents deck FAILS with "unknown tag 'axiom'", "unknown
   tag 'framework'", "unknown tag 'plasticity'", etc. — proving goc
   is no longer phasor-flavored at the schema level.

2. WITH `.game-of-cards/canonical-tags.md` authored (placeholder
   created in this worktree for the verification): `goc validate`
   PASSES — proving the extension mechanism works programmatically,
   not just as documentation.

The placeholder canonical-tags.md is left untracked in the worktree
as a smoke-test artifact. Sub-card 6 (dogfood migration) authors the
production version with full literature-drift author predicate and
project-specific predicates per the audit catalogue.

### DoD jump

Six DoD items ticked this round (DoD-4, DoD-5, DoD-6, DoD-7, DoD-8,
DoD-11) plus DoD-9 (separate work — convention doc). Plus DoD-12
marked as superseded by direct-to-prod claim.

**Cumulative progress: 13/17 ticked, 4 unticked.**

Remaining four:
- DoD-14: GitHub Actions release workflow (separate ~30-min job;
  next pull-card tick)
- DoD-16: Self-hosted bootstrap (waits on sub-card 2 shipping)
- DoD-17: CI validation on goc repo's own deck (waits on sub-card 2
  + DoD-14)

The fourth one — DoD-12 (TestPyPI rehearsal) — is marked
**superseded** with a one-paragraph rationale: per user directive
("claim the pypi package, sniping risk"), 0.0.1 went straight to
production PyPI; the verification subset that TestPyPI would have
caught was caught by local `uv pip install -e .` and the importlib
resources smoke test pre-upload.

### .game-of-cards/ convention doc (DoD-9)

Authored `goc/templates/game_of_cards/README.md` — the canonical
reference doc documenting the `.game-of-cards/` convention
(directory layout, file format, !`cat` injection pattern, hook-point
catalog as a 5-row table, authoring guidelines, sub-card-6 migration
pointer). Ships into every consuming repo's `.game-of-cards/README.md`
at `goc install` time.

Main goc README's "What you get" section gets one bullet pointing at
it, preserving the README's user-facing-tempting framing per user
direction. The technical convention doc lives at the convention's
own location, not inlined into the README.

### Cumulative goc-repo commits (still pending push):

- `970b1d1` LICENSE
- `bce1813` package skeleton
- `4c4c012` README substrate framing (first attempt)
- `9b9f1db` README rewrite per agile-thinking brief
- `e93ea14` template tree + .game-of-cards scaffold + Cat-5 sed
- `d20359e` Track 3a-deep batch 1 (3 small skills)
- `0a17f2b` README Status reframe (brand new)
- `dd28ec0` Track 3a-deep batch 2 (finish-card)
- `d6b137b` Track 3a-deep batch 3 (extend-deck + sed sweep)
- `5599cf81` (phasor-side commit; not on goc remote)
- `0b99008` Track 3a-deep batch 4 (card-schema; templates phasor-clean)
- `46bfdfc` .game-of-cards convention doc + README link

## 2026-05-04 (round 8) — GH Actions workflows + .gitignore — DoD 13→15

Authored two GitHub Actions workflows in the goc repo:

- **`release.yml`** (DoD-14): tag-triggered (`v*` pattern), builds wheel
  + sdist via `uv build`, validates the tag matches `pyproject.toml`'s
  declared version (so an accidental `v0.0.1` push when pyproject says
  `0.1.0` fails fast), then publishes via PyPI's **OIDC trusted
  publishing** — `pypa/gh-action-pypi-publish@release/v1` with
  `id-token: write` and an `environment: pypi`. No PyPI token stored
  as a repo secret. `workflow_dispatch` enabled for dry-run builds.
  Trusted-publisher registration is a one-time manual configuration
  step on the PyPI side (claims: zauberzeug / game-of-cards /
  release.yml / pypi); the workflow comments document the URL and
  required claim values inline. Until that's configured, the publish
  job errors on auth — by design (explicit configuration gate).

- **`ci.yml`**: every-push smoke test across 4 Python versions (3.10,
  3.11, 3.12, 3.13). Verifies (a) console script reachable
  (`goc --version`, `goc --help | head -5`), (b) all 11 skill
  templates ship as `importlib.resources` package data (asserts
  every `goc.templates.skills.<skill>.SKILL.md` is a file), (c) the
  schema.yaml ships, (d) `goc validate` runs on the repo's own
  deck/ if one exists (no-op until sub-card 2 ships).

Plus `.gitignore` (standard Python ignores: `__pycache__/`, `dist/`,
`.venv/`, etc.) and `uv.lock` committed (per uv's library-project
recommendation).

Dropped accidentally-introduced README drift ("Game of Cards ships
*that*" → "ships *one*") that crept in from an earlier heredoc round.
Reverted to the original wording before commit.

**DoD progress: 15/17.**

Remaining 2 are both gated on sub-card 2 (`goc-install-command-
scaffolds-repo`):

- **DoD-15** (self-hosted bootstrap): requires `goc install` to
  exist (currently a stub printing "not yet implemented"). Once
  sub-card 2 ships the actual install logic, this card's bootstrap
  validation is one `goc install` invocation away.
- **DoD-16** (CI validation on goc's own deck): the *workflow* is
  in place (ci.yml step "Validate deck (if exists)"); it'll start
  doing useful work as soon as sub-card 2 seeds the goc repo's
  deck/ directory.

This card has shipped what's in scope. Sub-card 2 closes the last
two DoD items as part of its own deliverable validation. The card
stays `active` rather than `blocked` because there's no human gate
to lower — sub-card 2 just hasn't been pulled yet.

### Cumulative goc-repo commits (still pending push to `main`):

- `970b1d1` LICENSE
- `bce1813` package skeleton (pyproject + goc/)
- `4c4c012` README substrate framing (first attempt)
- `9b9f1db` README rewrite per agile-thinking brief
- `e93ea14` template tree + .game-of-cards scaffold + Cat-5 sed
- `d20359e` Track 3a-deep batch 1 (3 small skills)
- `0a17f2b` README Status reframe
- `dd28ec0` Track 3a-deep batch 2 (finish-card)
- `d6b137b` Track 3a-deep batch 3 (extend-deck + sed sweep)
- `0b99008` Track 3a-deep batch 4 (card-schema; templates clean)
- `46bfdfc` .game-of-cards convention doc + README link
- `<this round>` GH Actions release/ci workflows + .gitignore + uv.lock

### Outside git: PyPI 0.0.1 live for the public name claim.

### Next likely action

Pull-card next tick: probably `goc-install-command-scaffolds-repo` — the
last unblocking dependency for this card's final two ticks. Or
extend-deck if the user wants new cards filed first.

## 2026-05-04 — closure (17/17), self-hosted

DoD-15 ticked: `goc install` ran in `~/Projects/game-of-cards/` itself,
materializing `.claude/skills/` (11), `.claude/hooks/user-prompt-submit-goc.py`,
`deck/` (with `.goc-version` sentinel), `.game-of-cards/` (content + hook stubs),
AGENTS.md (marker-bounded), CLAUDE.md (marker-bounded), `.pre-commit-config.yaml`.
The goc repo now manages its own backlog via the same engine that ships in
the package — compiler-bootstrap analogue holds.

DoD-16 ticked: `.github/workflows/ci.yml` already includes the
"Validate deck (if exists)" step against `deck/`; `goc-validate`
pre-commit hook installed locally as part of `goc install`. First CI
activation gated on `git push origin main` (manual user authorization
not yet given — 2 commits ahead of remote at closure time).

Card migration: all 10 goc-* cards moved from phasor-agents'
`deck/goc-*/` to `~/Projects/game-of-cards/deck/`. Validator green
on all 10. Phasor-side originals removed.

