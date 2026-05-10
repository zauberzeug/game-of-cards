# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## This repo *is* `goc` — and it dogfoods itself

The package under `goc/` is the Game of Cards CLI; the assets under
`.claude/`, `.game-of-cards/`, and the `<!-- BEGIN GOC -->` block below
are this repo's own *consumer* copy of what `goc install` ships. The
deck under `deck/` is real work for the tool itself (cards prefixed
`goc-*`). Behavior you observe here is the behavior shipped to
consumers — there is no separate "framework" repo.

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
3.10–3.13; the validation step is what gates card-frontmatter drift.

Releases publish to three registries — PyPI, npm, ClawHub — on a
single tag push. PyPI + npm authenticate via OIDC trusted publishing
(no token); ClawHub authenticates via a stored `CLAWHUB_TOKEN` repo
secret (a personal `clawhub login` token that lives in repo settings,
not in the codebase).

**The git tag IS the version** — `pyproject.toml` declares
`dynamic = ["version"]` and hatch-vcs reads `git describe --tags` at
build time; the four plugin manifests (`openclaw-plugin/package.json`
+ `package-lock.json`, `claude-plugin/.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`) and `goc/__init__.py`'s
`__version__` literal are rewritten from the same tag value by
`scripts/release_rewrite_versions.py` inside the workflow. Humans
never edit version literals; a tagged commit that touches any of
those files trips the in-job tripwire and fails the build.

Canonical flow:

```
git tag vX.Y.Z && git push origin vX.Y.Z
```

That's it. The tag-push triggers PyPI + npm + ClawHub publishes in
parallel.

Why ClawHub uses a token instead of OIDC: their official reusable
workflow refuses OIDC handshakes on `push` events. Without a token,
each release would need a manual `gh workflow run release.yml --ref
vX.Y.Z` follow-up. The token avoids that two-step. Rotate by
re-running `clawhub login` then `jq -r .token "$HOME/Library/Application
Support/clawhub/config.json" | gh secret set CLAWHUB_TOKEN`.

See `.github/workflows/release.yml` header comment for trusted
publisher + secret configuration details.

## Code architecture

The Python package is intentionally small (4 source files):

- **`goc/cli.py`** — thin Click entry point. Imports the engine's Click
  group, bolts on `install` + `upgrade` from `install.py`, and adds
  `--version`. Wired as `goc = "goc.cli:main"` in `pyproject.toml`.
- **`goc/engine.py`** — ~1.8 kLOC, the bulk of the tool: frontmatter
  parser, schema loader, card loader, validator, value/edge graph,
  table/board renderers, and every verb except install/upgrade
  (`new`, `status`, `done`, `attest`, `decide`, `advance`, `unadvance`,
  `move`, `triage`, `show`, `quality-pass`, `validate`).
- **`goc/install.py`** — `install` and `upgrade` commands. Reads
  templates via `importlib.resources` so it works from a wheel.
- **`goc/schema.yaml`** — single source of truth for card frontmatter
  (loaded by `engine.load_schema()`; inlined into the `card-schema`
  skill body at install time).

`engine.py` resolves `DECK_DIR = Path.cwd() / "deck"`, so running `goc`
from the repo root operates on the repo's own deck.

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

### Skill and config files have two copies — edit the template

Because this repo dogfoods itself, every file under `.claude/skills/`,
`.claude/hooks/`, and `.game-of-cards/` is a
*consumer copy* of the corresponding file under `goc/templates/`. The
next `goc upgrade` overwrites the consumer copy from the template.
**When editing skill bodies, hook scripts, or per-repo config stubs,
edit `goc/templates/...` and re-run `goc upgrade`** (or edit both
copies in lockstep). Editing only `.claude/skills/...` is silently
lost on the next upgrade.

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

**Do not edit `claude-plugin/` directly.** The `sync-plugin-assets`
pre-commit hook (`scripts/sync_plugin_assets.py`) auto-regenerates those
files from the source-of-truth on every commit and stages the changes
automatically. CI runs `python scripts/sync_plugin_assets.py --check`
and fails the build on any drift. Plugin-specific files that are NOT
auto-synced: `claude-plugin/hooks/hooks.json`, `claude-plugin/bin/goc`,
`claude-plugin/settings.json`, `claude-plugin/README.md`.

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
  are **TypeScript ports** registered via `api.on('session_start' | …)`.
  Claude Code's Python hook scripts under `goc/templates/hooks/` are
  used only by the `--local-skills` install path on Claude — the
  OpenClaw plugin reimplements them in TS inside `index.ts`.

| Plugin path | Source-of-truth |
|---|---|
| `openclaw-plugin/goc/` | `goc/` (engine, schema, templates — auto-synced) |
| `openclaw-plugin/skills/<name>/SKILL.md` | `goc/templates/skills/<name>/SKILL.md` (hand-ported with invocation-neutral edits via `scripts/port_skills_to_openclaw.py`) |

The auto-synced engine pair (`goc → openclaw-plugin/goc`) is enforced
by the same byte-for-byte tripwire as the Claude one. Skills are NOT
auto-synced — they go through the porting script once during scaffold
and are independently maintained from then on. To re-port (e.g., after
a major rewrite of the source skills), re-run
`python3 scripts/port_skills_to_openclaw.py` and review the diff.

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
`<!-- BEGIN GOC v… -->` and `<!-- END GOC -->`. Content above or below
those markers is preserved across `goc install` / `goc upgrade`. This
section is therefore safe to extend; the block below it is generated
from `goc/templates/CLAUDE_GOC.md` and round-trips cleanly.

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

<!-- BEGIN GOC IMPORT -->
@AGENTS.md
<!-- END GOC IMPORT -->

