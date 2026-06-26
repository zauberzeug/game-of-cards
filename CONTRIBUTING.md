# Contributing to Game of Cards

Thanks for your interest in contributing!
This page is the short version — the long-form context lives in
[`README.md`](README.md) (methodology), [`AGENTS.md`](AGENTS.md) (deck workflow),
[`CLAUDE.md`](CLAUDE.md) (project conventions), and the header comment of
[`.github/workflows/release.yml`](.github/workflows/release.yml) (release machinery).

## About the project

Game of Cards is a deck-based methodology and CLI for human + AI
contributors. This repository is both the source tree for the `goc`
package *and* its own consumer — it dogfoods every change. The Python
package is small (4 source files under `goc/`); most of the surface
area is in the `goc/templates/` payload that `goc install` ships into
consuming repos, and in the two plugin payloads (`claude-plugin/`,
`openclaw-plugin/`) that mirror it.

## Reporting issues

Bugs and feature requests go to [GitHub Issues](https://github.com/zauberzeug/game-of-cards/issues).
Include enough detail that someone reading cold can act on it —
which command you ran, what you expected, what actually happened, and
the relevant versions (`uv run goc --version` and OS).

## Setting up your environment

You need Python 3.10+ and [`uv`](https://docs.astral.sh/uv/) installed.

```bash
git clone git@github.com:zauberzeug/game-of-cards.git
cd game-of-cards
uv sync                              # install dev environment
uv run goc --help                    # exercise the CLI from source
uv run goc validate                  # check every card's frontmatter
```

Useful commands during development:

```bash
uv build                                       # produce wheel + sdist in dist/
pre-commit run --all-files                     # sync plugin assets + goc validate
python3 scripts/sync_plugin_assets.py --check  # verify claude-plugin/ is in sync
```

The plugin payloads (`claude-plugin/`, `openclaw-plugin/`) are
**byte-for-byte mirrors** of `goc/` and `goc/templates/`. A pre-commit
hook regenerates them on every commit; CI fails the build if they
drift. **Always edit the source under `goc/templates/` — never the
mirrors directly.** Details in [`CLAUDE.md`](CLAUDE.md).

## Working with the deck (Game of Cards)

Persistent work — bug fixes, features, refactors, docs — flows
through the deck under `.game-of-cards/deck/`. Each task is a
directory with frontmatter, a body, and a Definition of Done. The
agent (or you) files a card, claims it, implements, and closes it.

```bash
uv run goc                            # show open queue
uv run goc --board                    # kanban view
uv run goc new "my-card-title"        # file a new card
uv run goc status my-card-title active  # claim it
uv run goc done my-card-title         # close (after DoD ticks)
```

More on the workflow lives in [`AGENTS.md`](AGENTS.md); the verb-level
CLI reference is in [`goc.md`](goc.md).

## Coding conventions

Project-specific conventions (template/mirror dogfooding, version
literals, marker-bounded merges, etc.) are documented in
[`CLAUDE.md`](CLAUDE.md). Read it before non-trivial changes — most
"surprises" in the codebase are dogfooding side effects that the file
already explains.

General style:

- Python 3.10+, type hints where they aid readability (not religiously).
- Single quotes for strings; f-strings preferred.
- Edit `goc/templates/...` and re-run `goc upgrade` rather than
  editing `.claude/skills/...` directly (the latter is a consumer
  copy of the former and gets overwritten on upgrade).

## Before submitting a pull request

Two checks gate every PR:

```bash
pre-commit run --all-files     # formats, mirrors plugin assets, runs goc validate
uv run goc validate            # explicit re-run (pre-commit also calls this)
```

Pre-commit handles the plugin-asset byte-mirror, which is the most
common drift cause. CI runs `python scripts/sync_plugin_assets.py
--check` and fails on any mismatch.

For non-trivial changes, **work on a feature branch**, not on `main`.
File a card first if the work doesn't already have one — the card is
the design doc the next reader (human or agent) needs to understand
what shipped and why.

## Release process

Releases publish to **PyPI, npm, and ClawHub** via OIDC trusted
publishing. No long-lived tokens in repo secrets; each registry is a
one-time trusted-publisher configuration (see the
[`release.yml` header](.github/workflows/release.yml) for the setup
trail).

The maintainer's single action to ship a release:

```bash
gh workflow run release.yml -f version=X.Y.Z
```

That one command:

1. Rewrites the version literals in `goc/__init__.py` and the four
   plugin manifests.
2. Builds the wheel + sdist with the new version pinned.
3. Runs the end-to-end auto-bootstrap smoke test.
4. Creates and pushes the tag `vX.Y.Z` from HEAD.
5. Publishes to PyPI and npm via OIDC, then auto-dispatches the workflow
   again on the tag to publish ClawHub. ClawHub's trusted-publish
   requires the dispatched commit to equal the published commit, so its
   leg must run from the tag ref rather than the from-`main` dispatch —
   this second dispatch is automatic, so it stays one human command.

**The git tag IS the version.** Humans never edit version literals —
the workflow is the version writer. A commit that touches a version
literal trips an in-job tripwire and fails the release.

**Recovery / republish on an existing tag** (if a publish leg
transient-fails):

```bash
gh workflow run release.yml --ref vX.Y.Z                       # all legs
gh workflow run release.yml --ref vX.Y.Z -f clawhub_only=true  # ClawHub only
```

This re-runs the publish path on the existing tag; the tag-creation
step is a no-op in `mode=tag`. Registries reject duplicate publishes,
so this is idempotent for already-shipped channels and a fresh
publish for any that failed. The `clawhub_only` form is the lean path
that mirrors the automatic tag re-dispatch — it skips smoke/PyPI/npm and
publishes only ClawHub.

**Dry-run preview** (build + smoke, no publishes):

```bash
gh workflow run release.yml -f dry_run=true
```

`git push origin vX.Y.Z` no longer triggers a release on its own —
the workflow only enters via `workflow_dispatch`. The two-step
canonical flow that earlier docs may reference (`git push tag` + `gh
workflow run`) was superseded; see card
`find-single-trigger-release-flow-for-all-three-registries` for the
constraint trail.

## For maintainers

- **Trusted-publisher configuration** — the one-time setup for each
  registry (PyPI, npm, ClawHub) is documented in the
  [`release.yml` header comment](.github/workflows/release.yml).
- **Plugin asset mirrors** — auto-synced by `scripts/sync_plugin_assets.py`
  via the pre-commit hook; CI fails on drift. Don't edit
  `claude-plugin/` or `openclaw-plugin/goc/` directly.
- **OpenClaw skills** — *not* auto-synced from `goc/templates/skills/`.
  Re-port with `python3 scripts/port_skills_to_openclaw.py` after a
  source-skill rewrite; review the diff before committing.

## Thank you!

Issues and PRs welcome — the project is small enough that even small
improvements are visible.
