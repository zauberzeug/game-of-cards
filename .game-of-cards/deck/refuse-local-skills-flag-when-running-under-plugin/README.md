---
title: refuse-local-skills-flag-when-running-under-plugin
summary: "When the bundled `goc/` engine inside `claude-plugin/` is invoked (via `claude-plugin/bin/goc`), refuse `--local-skills` (on `goc install`) and `--keep-local-skills` (on `goc upgrade`) with a clear error directing the user to install via pipx instead. Once those flags can never reach the bundled engine, the engine no longer reads `templates/skills/` or `templates/hooks/`, so drop `claude-plugin/goc/templates/skills/` and `claude-plugin/goc/templates/hooks/{deck_prompt_router,deck_session_start}.py` from the plugin payload entirely. Eliminates ~half the surface area of the `validate_plugin_mirror_parity` tripwire and removes one drift bug class for good."
status: open
stage: null
contribution: high
created: 2026-05-09
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, infra, api-contract]
definition_of_done: |
  - [ ] Bundled engine (`claude-plugin/goc/`) detects plugin context, e.g. `PACKAGE_DIR.parent.name == "claude-plugin"` or equivalent — pick whichever is robust against `uv run --project` and direct `python -m goc` invocations
  - [ ] `goc install --local-skills` invoked from plugin context exits non-zero with a clear message: `--local-skills is not supported when running under the plugin (skills are already provided by claude-plugin/skills/). To use vendored skills, install goc via pipx instead: pipx install game-of-cards`
  - [ ] `goc upgrade --keep-local-skills` invoked from plugin context exits non-zero with the same shape of message
  - [ ] `goc install` and `goc upgrade` without those flags continue to work unchanged from plugin context (the common path: scaffold `.game-of-cards/`, merge `AGENTS.md` / `CLAUDE.md` blocks, no skill writes)
  - [ ] `claude-plugin/goc/templates/skills/` directory is removed from the plugin payload
  - [ ] `claude-plugin/goc/templates/hooks/{deck_prompt_router,deck_session_start}.py` are removed from the plugin payload (the flat `claude-plugin/hooks/` copies remain — those serve the plugin runtime, not the bundled engine)
  - [ ] `validate_plugin_mirror_parity` (`goc/engine.py`) is updated to no longer compare the now-removed nested directories; comments updated to reflect the narrower invariant
  - [ ] Pipx-installed `goc` (the non-plugin path) continues to honor `--local-skills` and `--keep-local-skills` exactly as today — the change is gated on plugin-context detection only
  - [ ] Regression test in `tests/test_install.py` (or a new file) covers: plugin-context-detected install rejects `--local-skills`, plugin-context-detected upgrade rejects `--keep-local-skills`, pipx-context install/upgrade still accept them
  - [ ] Regression test in `tests/test_plugin_mirror_parity.py` is updated to reflect the smaller mirror surface; the existing `test_real_repo_passes` still passes
  - [ ] CLAUDE.md "Plugin assets are duplicated" section is updated to remove the rows for `claude-plugin/goc/templates/skills/` and `claude-plugin/goc/templates/hooks/`, leaving only the rows that still apply
  - [ ] AGENTS.md / install-help docs note the plugin/pipx split for vendored-skills users
  - [ ] `uv run goc validate` passes
---

# Refuse `--local-skills` flag when running under plugin

## Why

The plugin payload ships **three** copies of every skill asset:

| Path | Purpose |
|---|---|
| `goc/templates/skills/` | source-of-truth (pipx wheel data) |
| `claude-plugin/skills/` | flat layout — Claude Code plugin runtime auto-discovers skills here |
| `claude-plugin/goc/templates/skills/` | nested layout — the bundled `goc/` package's `importlib.resources` lookup |

The first two are unavoidable: `claude-plugin/skills/` exists because the plugin runtime walks that exact path, and the marketplace install only extracts the `claude-plugin/` subtree (so a symlink would silently break). The card `generate-plugin-payloads-from-templates-on-release` (closed 2026-05-09) handles drift between (1) and (2) by generating (2) from (1) at release time.

The third copy — `claude-plugin/goc/templates/skills/` — is different. It exists only because `importlib.resources` resolves package data relative to the package directory on disk. It is read by the bundled engine in exactly two narrow situations:

1. `goc install --local-skills` invoked from plugin context (writes vendored `.claude/skills/` from templates).
2. `goc upgrade --keep-local-skills` invoked from plugin context (refreshes vendored `.claude/skills/` from templates).
3. `validate_skill_dir_parity` invoked from plugin context (compares an existing `.claude/skills/` to templates) — but this fires only if `.claude/skills/` already exists, which only happens after (1) or (2).

In every other plugin flow — and there are many: default `goc install`, `goc new`, `goc done`, `goc validate` in a non-vendored repo, `Skill(create-card)`, etc. — the bundled engine never reads `templates/skills/` at all.

So the third copy serves the "plugin AND vendored skills" combination, which has no real use case:

- Anyone who needs vendored skills (CI without plugin support, repos that fork or template GoC, environments that won't allow `~/.claude/` writes) should install via `pipx install game-of-cards`. Pipx ships its own templates.
- Anyone who has the plugin already gets skills via `claude-plugin/skills/`. They have no reason to also write a checked-in `.claude/skills/` copy.
- The combination "plugin user runs `--local-skills`" creates a confusing dual source of truth (skills come from both `claude-plugin/skills/` AND `.claude/skills/`) and currently silently shadows the plugin's copy with the locally-written one.

## What

Make the bundled engine refuse the flag combination that justifies the third copy, then drop the third copy.

### Detection

The bundled engine detects it is running under the plugin by inspecting where its own package files live. Two robust candidates:

```python
PLUGIN_CONTEXT = PACKAGE_DIR.parent.name == "claude-plugin"
# or
PLUGIN_CONTEXT = "claude-plugin" in PACKAGE_DIR.parts
```

The first form is precise — it requires the `goc/` package to sit directly inside a `claude-plugin/` directory, which is exactly how the plugin extracts. Pick it unless investigation surfaces a counter-example (e.g. a developer running the bundled engine directly via `uv run --project claude-plugin/`).

### Failure mode

When `--local-skills` (install) or `--keep-local-skills` (upgrade) is passed under plugin context:

```
ERROR: --local-skills is not supported when running under the plugin.
       Skills are already provided by claude-plugin/skills/ and registered with Claude Code.

       To use vendored skills (e.g. for CI without plugin support, or a forked GoC),
       install goc via pipx instead:

           pipx install game-of-cards
           goc install --local-skills

       Or remove --local-skills from this invocation to use the plugin path.
```

Exit non-zero so scripts notice. Same shape of message for `--keep-local-skills`.

### Payload reduction

Once the flags can never reach the bundled engine, these directories are dead weight:

- `claude-plugin/goc/templates/skills/` (whole tree)
- `claude-plugin/goc/templates/hooks/deck_prompt_router.py`
- `claude-plugin/goc/templates/hooks/deck_session_start.py`

Delete them. Update `validate_plugin_mirror_parity` to reflect the narrower invariant — it now only checks the flat `claude-plugin/skills/` and `claude-plugin/hooks/` mirrors against `goc/templates/`.

The other things still in `claude-plugin/goc/templates/` — `AGENTS_GOC.md`, `CLAUDE_GOC.md`, `game_of_cards/`, the `user-prompt-submit.py` legacy hook — stay, because they are read by the bundled engine on the *common* `goc install` / `goc upgrade` path, regardless of `--local-skills`.

### Pipx path is unaffected

A user who runs `pipx install game-of-cards` and then `goc install --local-skills` from the pipx-installed binary is **not** in plugin context. The detection returns `False`, the flag is honored as today, and templates are read from the pipx wheel's own `goc/templates/skills/`. No change to that path.

## Risks and edge cases

- **Developer running the bundled engine directly during plugin development.** If a contributor does `uv run --project claude-plugin/ goc install --local-skills` while iterating on the plugin, they hit the new error. That's a feature: they should install via pipx for that workflow. Document in CONTRIBUTING.md / AGENTS.md if it surprises anyone.
- **Marketplace installs that extract to a path other than `claude-plugin/`.** If Claude Code's marketplace ever changes its extraction path, the detection breaks. Mitigation: make detection forgiving (any ancestor named `claude-plugin` triggers it, not just the immediate parent), and add a regression test that catches the rename.
- **Symmetry with future `codex-plugin/` and `openclaw-plugin/`.** When those land, apply the same pattern: refuse `--local-skills` from `codex-plugin/` and `openclaw-plugin/` contexts too. File follow-up cards rather than over-engineering the detection now.

## Why this is the right fix

The currently-closed `generate-plugin-payloads-from-templates-on-release` card chose to *generate* the duplicates rather than eliminate the need for them. That was the right call for the flat `claude-plugin/skills/` layout, where the plugin runtime requires the files at exactly that path. For the nested `claude-plugin/goc/templates/`, the duplication exists only to support a flag combination that nobody should use — so eliminating the use case is cheaper than generating the bytes.

After this card lands, the plugin's relationship to skills is clean and one-way: the plugin runtime owns `claude-plugin/skills/`, the bundled engine never touches skills directly. The "plugin AND vendored" mode dies and `--local-skills` becomes a pipx-only flag.

## DoD enforcement

The DoD checkboxes above are the closure contract. The card cannot close until every box is checked.
