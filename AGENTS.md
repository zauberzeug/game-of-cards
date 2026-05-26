# Agent Guidelines

This file provides guidance to AI agents when working with code in this repository.

## Repo-Local GoC Command

This repository is the source tree for the `goc` package. Run GoC commands
from the repo root as `uv run goc ...`; do not assume a bare `goc` executable
is available on PATH in this repo. Translate every bare `goc ...` example in
the generated guidance below to `uv run goc ...` while working here.

## This repo *is* `goc` — and it dogfoods itself

The package under `goc/` is the Game of Cards CLI; the assets under
`.claude/`, `.game-of-cards/`, and the `<!-- BEGIN GOC -->` block below
are this repo's own *consumer* copy of what `goc install` ships. The
deck under `.game-of-cards/deck/` is real work for the tool itself.
Behavior you observe here is the behavior shipped to consumers — there
is no separate "framework" repo.

## Common commands

```bash
uv sync                            # install dev environment
uv pip install --system -e .       # editable install (what CI does)
uv run goc --help                  # exercise the CLI from source
uv run goc validate                # check every card's frontmatter
uv build                           # produce wheel + sdist in dist/
pre-commit run --all-files         # sync plugin assets + goc validate
python scripts/sync_plugin_assets.py --check  # verify claude-plugin/ is in sync
```

No pytest suite exists yet. `.github/workflows/ci.yml` is a
build + console-script + `goc validate` smoke matrix on Python
3.10-3.13; the validation step is what gates card-frontmatter drift.

Releases publish to three registries — PyPI, npm, ClawHub — all via
OIDC trusted publishing. No long-lived tokens in repo secrets; each
publish target is a one-time configuration (web UI for PyPI/npm,
`clawhub package trusted-publisher set ...` for ClawHub) that authorizes
this workflow to mint short-lived publish credentials at run time.

**The git tag IS the version** — `pyproject.toml` declares
`dynamic = ["version"]` and hatch-vcs reads `git describe --tags` at
build time (overridden in CI by `SETUPTOOLS_SCM_PRETEND_VERSION` so
the wheel reports the right version even before the tag is created).
The five plugin manifests (`openclaw-plugin/package.json` +
`package-lock.json`, `claude-plugin/.claude-plugin/plugin.json`,
`codex-plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`),
`goc/__init__.py`'s `__version__`
literal, and the two dogfood self-host surfaces
(`.game-of-cards/deck/.goc-version`, `AGENTS.md`'s `<!-- BEGIN GOC
vX.Y.Z -->` marker) are rewritten from the input version by
`scripts/release_rewrite_versions.py` inside the workflow, then
committed back to main by the build job as
`release: bump version literals to vX.Y.Z` (under the
`github-actions[bot]` identity) so consumers reading the git tree
directly — plugin managers read the checked-in payloads —
see the correct version, and so that
`tests/test_version_surfaces.py` stays green on the bot's release
commit. Humans never edit the publish-channel version literals; the
in-job tripwire fails the build on any human commit that touches
those six files, while explicitly exempting the bot's own
release-bump commits so the *next* release dispatch reads the
previous release's commit as HEAD without tripping. (`AGENTS.md` is
NOT in the tripwire's tracked set — humans edit its non-marker
content freely.)

Canonical flow:

```bash
gh workflow run release.yml -f version=X.Y.Z
```

That single command publishes to PyPI, npm, AND ClawHub from one
`workflow_dispatch` event. The workflow itself commits the version
literals back to `main` and tags the rewrite commit as `vX.Y.Z` (as
the last two steps of the build job, after every consistency check
passes), then the three publish jobs run in parallel. ClawHub's OIDC
trusted publisher accepts `workflow_dispatch` events regardless of ref,
so a dispatch from `refs/heads/main` publishes the ClawHub leg natively
— no second event needed. There is no `CLAWHUB_TOKEN` secret; adding
one actively breaks releases (the reusable workflow's token-override
path authenticates as a different publisher than the OIDC path that
registered the package, and the Convex store rejects publishes with
`Package already exists and belongs to another publisher`).

Recovery / republish on an existing tag (if a publish job
transient-failed):

```bash
gh workflow run release.yml --ref vX.Y.Z
```

`git push origin vX.Y.Z` from a maintainer machine no longer triggers
a release — the workflow only runs on `workflow_dispatch`. The closed
predecessor card `auto-publish-npm-and-clawhub-on-tag-push` documented
a two-step tag-push + workflow-dispatch flow; that conclusion was
superseded by
`find-single-trigger-release-flow-for-all-three-registries`, which
verified that the workflow_dispatch event type (not the ref) is what
the ClawHub validator cares about.

See `.github/workflows/release.yml` header comment for trusted
publisher configuration details.

## Code architecture

The Python package is intentionally small:

- **`goc/cli.py`** — thin Click entry point. Imports the engine's Click
  group, bolts on `install` + `upgrade` from `install.py`, and adds
  `--version`. Wired as `goc = "goc.cli:main"` in `pyproject.toml`.
- **`goc/engine.py`** — the bulk of the tool: frontmatter parser, schema
  loader, card loader, validator, value/edge graph, table/board
  renderers, and every verb except install/upgrade (`new`, `status`,
  `done`, `attest`, `decide`, `advance`, `unadvance`, `move`, `triage`,
  `show`, `quality-pass`, `validate`).
- **`goc/install.py`** — `install` and `upgrade` commands. Reads
  templates via `importlib.resources` so it works from a wheel.
- **`goc/schema.yaml`** — single source of truth for card frontmatter
  (loaded by `engine.load_schema()`; inlined into the `card-schema`
  skill body at install time).

`engine.py` resolves `DECK_DIR` to the canonical `.game-of-cards/deck/`
path, with legacy `deck/` fallback and dual-tree conflict detection.
Running `uv run goc` from the repo root operates on this repo's own
deck.

### Templates ship as package data

`goc/templates/` is bundled into the wheel and is the source of truth
for everything `goc install` writes into a consuming repo:

| Template path | Installed to |
|---|---|
| `templates/skills/<verb>/` | `<repo>/.claude/skills/<verb>/` |
| `templates/hooks/<name>.py` | `<repo>/.claude/hooks/<name>.py` |
| `templates/game_of_cards/` | `<repo>/.game-of-cards/` |
| `templates/AGENTS_GOC.md`, `templates/CLAUDE_GOC.md` | merged into AGENTS.md / CLAUDE.md |

The hook list is derived from `templates/hooks/*.py` at install time
(see `deck_hook_scripts` in `goc/install.py`); dropping a new `.py`
file in that directory wires it into the install copy and the parity
mirrors automatically. The event mapping (`SessionStart`, `Stop`, etc.)
stays explicit in `GOC_CLAUDE_HOOKS`, and `goc validate` enforces that
every script has a registration and every registration points at a
real file.

### Skill and hook files have two copies — edit the template, sync handles the rest

Because this repo dogfoods itself, every file under `.claude/skills/`,
`.claude/hooks/`, and `.codex/skills/` is a *consumer copy* of the corresponding file
under `goc/templates/`. **Always edit `goc/templates/...`** — the
`sync-plugin-assets` pre-commit hook regenerates those
mirrors from the templates on every commit and stages them
automatically, the same way it already does for `claude-plugin/`,
`codex-plugin/`, and `openclaw-plugin/`. CI runs `python scripts/sync_plugin_assets.py
--check` and fails the build on any drift, so editing only
`.claude/skills/...` or `.codex/skills/...` is now CI-detectable (it gets
overwritten by the next pre-commit pass).

The `.game-of-cards/` content stubs (project-local deck README,
config) and `.claude/settings.json` (project-specific permission
allow-list) are NOT in the auto-sync — they're meant to be customized
per repo. The `<!-- BEGIN GOC vX.Y.Z -->` marker in `AGENTS.md` and
the `.goc-version` sentinel are rewritten by the release workflow
(see release section above), so they're also out of scope for the
pre-commit sync.

### `skills_source` — which install path owns `.claude/skills/`

`.game-of-cards/config.yaml` holds a `skills_source` key, written by
`goc install` and read by both `goc upgrade` and `goc validate`. It is
the per-repo signal that says where Claude Code's GoC skills come from:

| Value | Meaning |
|---|---|
| `plugin` | Skills come from the Claude Code plugin payload (`${CLAUDE_PLUGIN_ROOT}/skills/`). `goc upgrade` does not write `.claude/skills/`, `.claude/hooks/`, or GoC entries in `.claude/settings.json`. `goc validate` skips the skill-dir parity check. Written when `goc install` is run *without* `--local-skills`. |
| `vendored` | Skills are checked into source control under `.claude/skills/`. `goc upgrade` refreshes those templates in place; `goc validate` enforces parity. Written when `goc install --local-skills` is used. |
| `auto` / unset | The engine detects whether a Claude Code GoC plugin payload is present on the host (looks under `$CLAUDE_PLUGIN_ROOT` and `~/.claude/plugins`). Plugin found -> behave as `plugin`. Plugin not found -> behave as `vendored`. This is the fallback for legacy installs that predate the key. |

Switching modes is a manual config edit. To move a vendored repo to
plugin mode: edit `skills_source: plugin` in
`.game-of-cards/config.yaml`, then `goc upgrade` — which detects the
leftover `.claude/skills/` and prompts for cleanup. The cleanup only
removes GoC-managed skill directories, hook files, and settings
entries; non-GoC skills in `.claude/skills/` are preserved. Declining
the cleanup is a strict no-op (the buggy "decline re-vendors and
deletes user skills" path that motivated this design is gone).

Bootstrap: `.claude/skills/_goc-bootstrap.sh` lives under
`.claude/skills/` but is sourced from
`goc/templates/bootstrap/_goc-bootstrap.sh` (not
`goc/templates/skills/`). The sync script handles this via a
`preserve_files` set on the skills dir-sync so the bootstrap isn't
deleted as "not in src", with a separate single-file sync pair
keeping its contents current.

### Plugin assets are auto-synced — edit only the template

The Claude Code plugin payload at `claude-plugin/` ships skills, hook
scripts, and a copy of the entire `goc/` package plus a `bin/goc`
wrapper. Because Claude Code's marketplace install only extracts the
`source: ./claude-plugin` subtree, those assets must be **real files**
(not symlinks pointing outside the subtree, which silently disappear on
consumer install). They are byte-for-byte copies of the source-of-truth
files:

| Plugin path | Source-of-truth |
|---|---|
| `claude-plugin/skills/` | `goc/templates/skills/` |
| `claude-plugin/hooks/deck_prompt_router.py` | `goc/templates/hooks/deck_prompt_router.py` |
| `claude-plugin/hooks/deck_session_start.py` | `goc/templates/hooks/deck_session_start.py` |
| `claude-plugin/hooks/pattern_generalization_check.py` | `goc/templates/hooks/pattern_generalization_check.py` |
| `claude-plugin/goc/` | `goc/` (entire package — engine, schema, templates) |

The Codex plugin payload at `codex-plugin/` follows the same real-file
principle, with Codex-specific frontmatter normalization for skills:

| Plugin path | Source-of-truth |
|---|---|
| `codex-plugin/skills/` | `goc/templates/skills/` filtered for Codex |
| `codex-plugin/hooks/deck_prompt_router.py` | `goc/templates/hooks/deck_prompt_router.py` |
| `codex-plugin/hooks/deck_session_start.py` | `goc/templates/hooks/deck_session_start.py` |
| `codex-plugin/hooks/pattern_generalization_check.py` | `goc/templates/hooks/pattern_generalization_check.py` |
| `codex-plugin/goc/` | `goc/` (entire package — engine, schema, templates) |

The flat `claude-plugin/skills/` and `claude-plugin/hooks/` paths exist
so Claude Code's plugin runtime auto-discovers them at the layout it
expects. The nested `claude-plugin/goc/templates/...` mirrors the rest
of the package (engine, schema, agents, game_of_cards templates, etc.)
but **deliberately omits** `templates/skills/` and the
`deck_prompt_router` / `deck_session_start` hook templates: the bundled
engine refuses `--local-skills` on `goc install` and `--keep-local-skills`
on `goc upgrade` (see `_is_plugin_context` in `goc/install.py`), so
those templates are never read from inside the plugin payload. To
vendor skills into source control, install via `pipx install
game-of-cards` instead — that path keeps the full template tree.

**Do not edit `claude-plugin/` or `codex-plugin/` directly.** The `sync-plugin-assets`
pre-commit hook (`scripts/sync_plugin_assets.py`) auto-regenerates those
files from the source-of-truth on every commit and stages the changes
automatically. CI runs `python scripts/sync_plugin_assets.py --check`
and fails the build on any drift. Plugin-specific files that are NOT
auto-synced: `claude-plugin/hooks/hooks.json`, `claude-plugin/bin/goc`,
`claude-plugin/settings.json`, `claude-plugin/README.md`,
`codex-plugin/.codex-plugin/plugin.json`, `codex-plugin/hooks/hooks.json`,
`codex-plugin/bin/goc`, `codex-plugin/README.md`, and
`.agents/plugins/marketplace.json`.

### OpenClaw plugin payload — same engine, different host shape

A second plugin payload lives at `openclaw-plugin/` for [OpenClaw](https://openclaw.ai),
the Node-based personal AI assistant. OpenClaw plugins have a fundamentally different
shape from Claude Code's:

- The plugin entry is **TypeScript**, not file-static. `openclaw-plugin/index.ts`
  exports a `definePluginEntry({ register(api) })` callback that registers
  capabilities programmatically.
- OpenClaw has **no auto-PATH-prepend** for plugin `bin/` directories
  (verified via spike on the
  `provide-openclaw-plugin-for-skills-and-hooks` card). So `goc` is
  exposed as a **registered tool** via `api.registerTool('goc', ...)`,
  not a shell binary on PATH. The tool handler shells out to
  `python3 -m goc.cli` with `PYTHONPATH` set to the plugin root.
- The three GoC lifecycle hooks (session-start active-card reminder,
  deck-first prompt-injection, pattern-generalization self-assessment)
  are **TypeScript ports** registered via `api.on('session_start' | ...)`.
  Claude Code's Python hook scripts under `goc/templates/hooks/` are
  used only by the `--local-skills` install path on Claude — the
  OpenClaw plugin reimplements them in TS inside `index.ts`.

| Plugin path | Source-of-truth |
|---|---|
| `openclaw-plugin/goc/` | `goc/` (engine, schema, templates — auto-synced) |
| `openclaw-plugin/skills/<name>/SKILL.md` | `goc/templates/skills/<name>/SKILL.md` (hand-ported with invocation-neutral edits via `scripts/port_skills_to_openclaw.py`) |

The auto-synced engine pair (`goc -> openclaw-plugin/goc`) is enforced
by the same byte-for-byte tripwire as the Claude one. Skills are NOT
auto-synced into the commit — they go through the porting script, whose
output is reviewed and committed by hand (unlike the claude/codex
mirrors, the porter applies non-trivial normalization worth eyeballing).
To re-port (e.g., after editing a source skill), re-run
`python3 scripts/port_skills_to_openclaw.py` and review the diff.

The port is deterministic, so a drift guard keeps it honest even though
it is not auto-staged: `scripts/port_skills_to_openclaw.py --check`
re-ports into memory and fails on any difference from the committed
`openclaw-plugin/skills/`. The same comparison is enforced in CI by
`tests/test_plugin_mirror_parity.py` (it calls the porter's
`drifted_skills()` from the regression-test suite), so a template edit
that is not followed by a re-port turns the build red instead of rotting
silently. The guard lives in a test, not a `ci.yml` step, because the
autonomous bot's `GITHUB_TOKEN` cannot edit files under
`.github/workflows/`. The porter is idempotent — re-running `--check`
immediately after a re-port is always green.

OpenClaw-plugin-specific files that are NOT auto-synced:
`openclaw-plugin/index.ts`, `openclaw-plugin/package.json`,
`openclaw-plugin/openclaw.plugin.json`, `openclaw-plugin/tsconfig.json`,
`openclaw-plugin/README.md`, `openclaw-plugin/skills/`.

### Plugin runs goc from a vendored engine — Python 3.10+ is the only host prerequisite

`claude-plugin/bin/goc` is a shell wrapper that invokes the bundled engine
via `python3 -m goc.cli` with `PYTHONPATH` pointing at the plugin root.
Claude Code auto-prepends the plugin's `bin/` directory to the Bash tool's
PATH while the plugin is enabled, so skill bodies keep calling plain
`goc <verb>` and the wrapper transparently runs the vendored engine.
No venv, no `uv`, no first-call latency.

The traditional `pipx install game-of-cards` recipe remains documented as
the fallback for environments that want a globally-installed `goc` binary
outside of the plugin.

### Marker-bounded merge for AGENTS.md / CLAUDE.md

`install._append_marker_block` rewrites only the content between
`<!-- BEGIN GOC vX.Y.Z -->` and `<!-- END GOC -->`. Content above or below
those markers is preserved across `goc install` / `goc upgrade`. This
section is therefore safe to extend; the block below it is generated
from `goc/templates/AGENTS_GOC.md` and round-trips cleanly. In this repo,
`CLAUDE.md` intentionally contains only `@AGENTS.md` so Claude Code loads
this shared file without duplicating the guidance.

## Parallel-Agent Commit Safety

Multiple agents may work on local `main` at the same time. Treat Git's
index as shared state: before staging, run `git diff --cached --name-only`.
If it lists files you did not stage, another agent is in its commit
window; wait with a short backoff or surface the collision instead of
pushing through.

When it is your turn, stage only explicit file paths with
`git add <path>...`. Do not use `git add .`, `git add -A`, directory-wide
adds, `git stash`, or destructive cleanup (`git restore`, `git checkout --`,
`git reset --hard`, `git clean`) to isolate your work; those operations can
move or discard another agent's WIP. Verify the staged set with
`git diff --cached --stat`, then commit with an explicit pathspec:
`git commit -- <path>...`. The pathspec is the last guard against
accidentally bundling unrelated staged files. For high-risk shared-main
commits, prepare the commit in a temporary worktree instead.

## Card authoring rules

When filing GoC cards in this repo:

- **English only.** All card titles, summaries, body, and DoD items
  are written in English, even when the conversation that motivated
  the card was in another language. Cards are read cold by future
  agents and contributors who may not share the original language.
- **No direct quotes from discussions.** Do not paste verbatim
  quotes from meetings, transcripts, chat, or coding-coffee
  retrospectives into card bodies. Synthesize the technical content
  into the card's own voice. Quotes age poorly, attribute work to
  individuals who may not want to be cited, and pull conversation
  context into a permanent artefact where it does not belong.
- **No references to internal events or projects by name.**
  Specifically: do not name internal meetings (e.g. coding coffee),
  internal projects (e.g. Zoe), or individual participants in card
  bodies. State the technical motivation directly. If a card needs
  context that only an internal source provides, summarize the
  technical fact, not its origin.
- **YAML format for list fields:** `advances` and `advanced_by` use
  block-style (one `- item` per line) when non-empty; empty lists
  stay as `[]`. The `tags` field uses inline flow style. The emitter
  enforces this automatically; when editing frontmatter by hand,
  follow the same convention to avoid merge conflicts.
- **`worker` field:** Optional free-form identifier naming who should or
  does work on a card. Use a flat string for a single identifier
  (`worker: rodja`), or a mapping when branch context is known
  (`worker: {who: rodja, where: feature/foo}`). The flat form is sugar
  for `{who: <value>}`. The value is unregistered — use a person slug,
  a machine name, or a capability tag (e.g. `gpu-required`, `human`,
  `rendering-expert`). The field persists after close as a historical
  record; `goc status <title> active` auto-populates it at claim time.
  Filter with `goc --worker <X>` or set `GOC_WORKER` env var for
  runner-specific queue views.

<!-- BEGIN GOC v0.0.20 -->
## Game of Cards — methodology runtime

This repo uses [Game of Cards](https://github.com/zauberzeug/game-of-cards):
tasks are directories under `.game-of-cards/deck/` with frontmatter,
body, and a Definition-of-Done. The CLI is `goc` (`goc --help`).

When the user asks for persistent work, the agent invokes the matching
GoC skill — file → claim → implement → close — silently. The card
records intent; the implementation lands. The user sees `goc` (queue)
or `goc --board` (kanban) only if they ask.

**Skills carry the methodology** (loaded on demand):

- `deck` — overview, operating modes, Andon cord, daily verbs.
- `card-schema` — frontmatter, DoD, status enums, YAML conventions.
- `create-card` / `advance-card` / `finish-card` — file, claim, close.
- `pull-card` / `next-card` / `scan-deck` — queue and browse.
- `kickoff` — first-time setup in a fresh repo.

Project-local extensions live under `.game-of-cards/`; see its
`README.md` if present. The `<!-- BEGIN GOC -->` markers above are the
discovery signal that this repo uses GoC.

**Closure is not frozenness.** When new evidence surfaces after a card
closes, file a new card for the new work and amend the closed card
with a forward pointer (dated `log.md` append; optional `> Later
evidence:` line atop the README). See `Skill(finish-card)` "After
closure" for the format.

**The deck is both a scheduler and a record.** The scheduler axis
walks `advances` edges across live cards to compose priority; the
record axis walks edges that include closed cards so a cold reader
can reconstruct the history of a decision. Closed-card relationship
edges are first-class: `goc validate` enforces referential integrity
for both axes regardless of either endpoint's status, and supersession
records a typed `superseded_by` / `supersedes` link (set atomically
by `goc status <old> superseded --by <new>`) so a reader landing on
a `superseded` card can be routed forward without parsing prose. See
`Skill(card-schema)` "Deck as scheduler vs deck as record" for the
full invariants.
<!-- END GOC -->
