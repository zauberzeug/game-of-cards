---
title: plugin-auto-detection-misses-versioned-marketplace-paths
summary: "`_claude_plugin_present()` scans only 2 levels under `~/.claude/plugins/`, but Claude Code's marketplace layout nests the payload at `cache/<marketplace>/<plugin>/<version>/skills/` (4 levels). Auto-detection silently falls back to `vendored`, `goc install`/`upgrade` pins the wrong `skills_source`, and `goc validate` then fires a misleading skill-parity error in repos that ARE plugin-mode."
status: open
stage: null
contribution: medium
created: "2026-05-19T04:38:44Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] `_claude_plugin_present()` returns True for `<root>/cache/<marketplace>/<plugin>/<version>/skills/` layouts (modern Claude Code marketplace)
  - [ ] Still returns True for legacy direct (`<root>/game-of-cards*/skills/`) and 2-level (`<root>/<any>/game-of-cards*/skills/`) layouts
  - [ ] Returns False when no `game-of-cards*` directory contains a `skills/` subtree
  - [ ] Doesn't follow symlinks into infinite loops (verified by including a self-referential symlink in the reproduce.py fixture)
  - [ ] `reproduce.py` exits 0 after the fix (and exited non-zero before)
  - [ ] `uv run goc validate` passes
---

# plugin-auto-detection-misses-versioned-marketplace-paths

## What's broken

`goc validate` reports a `validate_skill_dir_parity` error in repos where the Claude Code GoC plugin IS installed but `.game-of-cards/config.yaml` either has no `skills_source` key or has `skills_source: auto`. The user-visible message:

```
ERROR: .claude/skills: missing skills ['advance-card', 'audit-deck', 'card-schema',
  'claude-kickoff', 'create-card', 'decide-card', 'deck', 'finish-card', 'kickoff',
  'next-card', 'pull-card', 'refine-deck', 'retrospective', 'scan-deck', 'standup']
  that goc templates ship; run `goc upgrade --keep-local-skills` to resync
```

The parity check itself is behaving correctly per its contract (`goc/engine.py:636`). The actual defect is upstream — auto-detection misidentifies the repo as `vendored` when it should be `plugin`.

## Root cause

`_claude_plugin_present()` at `goc/engine.py:2529-2560` scans candidate roots (`$CLAUDE_PLUGIN_ROOT`, `~/.claude/plugins/`) for any directory whose name starts with `game-of-cards` and contains a direct `skills/` child. The scan descends only two levels:

```python
# goc/engine.py:2549-2558
for child in root.iterdir():
    if not child.is_dir():
        continue
    if child.name.startswith("game-of-cards") and (child / "skills").is_dir():
        return True
    for grand in child.iterdir() if child.is_dir() else ():
        if grand.name.startswith("game-of-cards") and (grand / "skills").is_dir():
            return True
```

Claude Code's marketplace install layout (verified on 2026-05-19 against the live tree at `~/.claude/plugins/` on this machine) puts the plugin payload four levels under the root:

```
~/.claude/plugins/cache/zauberzeug-claude/game-of-cards/0.0.18/skills/
~/.claude/plugins/cache/game-of-cards/game-of-cards/0.0.12/skills/
```

The structure is `cache-or-data/<marketplace>/<plugin>/<version>/skills/`. The scanner never reaches the version directory, so `(plugin / "skills").is_dir()` is always False at the levels it does check.

When the scan returns False, `effective_skills_source()` at `goc/engine.py:2563-2574` falls through to `vendored`:

```python
configured = get_skills_source()
if configured != "auto":
    return configured
return "plugin" if _claude_plugin_present() else "vendored"
```

Two call sites consume this value:

1. **`goc validate`** (via `validate_skill_dir_parity` at `goc/engine.py:654`) — skips the parity check in `plugin` mode and runs it in `vendored` mode. This is the call site that fires the user-visible error.
2. **`goc upgrade`** (`goc/install.py:1236`) — uses `effective_skills_source()` to pick the mode, then pins it via `_write_skills_source()` at line 1320. So a buggy detection observed during upgrade gets persisted into the config.

`goc install` is NOT affected: line 1094 picks the mode from `--local-skills` directly, not from the detector. So fresh installs without `--local-skills` always write `skills_source: plugin` regardless of plugin presence.

Repos with an `auto` (or unset) config and a plugin-mode runtime end up in this bad state through one of:
- An older goc version that wrote `auto` or nothing on install, plus a current `goc validate` invocation hitting the bad scan.
- A `goc upgrade` run while the buggy detector mis-reports plugin absence, which pins `vendored` durably.

After install/upgrade has pinned `skills_source: vendored`, fixing the scanner alone won't recover the repo — the explicit value wins. That's intentional (users who deliberately set `vendored` should keep it). Recovery for already-pinned repos is a hand edit of `.game-of-cards/config.yaml`.

## Why it matters

Every fresh repo that runs `goc install` on a machine with a marketplace-installed plugin gets pinned to `vendored` mode, even though the user has the plugin and never asked to vendor skills. The user then either:

1. Lives with a noisy `goc validate` error forever, or
2. Runs `goc upgrade --keep-local-skills` (the error's suggested fix), which pins them as `vendored` even harder and copies a tree of skill files they didn't want, or
3. Discovers `.game-of-cards/config.yaml` and hand-edits `skills_source: plugin`.

Only option 3 actually solves the problem, and nothing in the user surface points at it without reading source code.

## Fix

Replace the depth-locked nested loop with a bounded `rglob` that finds `game-of-cards*` directories at any depth under each candidate root, then accepts the payload if `skills/` is a direct child OR a grandchild (covering the version-pinned layout):

```python
def _claude_plugin_present() -> bool:
    candidates: list[Path] = []
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        candidates.append(Path(env_root))
    candidates.append(Path.home() / ".claude" / "plugins")

    for root in candidates:
        try:
            if not root.exists() or not root.is_dir():
                continue
        except OSError:
            continue
        # CLAUDE_PLUGIN_ROOT may point directly at the payload.
        if (root / "skills").is_dir() and root.name.startswith("game-of-cards"):
            return True
        try:
            for plugin_dir in root.rglob("game-of-cards*"):
                if not plugin_dir.is_dir():
                    continue
                if (plugin_dir / "skills").is_dir():
                    return True
                # Version-pinned layout: <plugin>/<version>/skills/
                try:
                    for version_dir in plugin_dir.iterdir():
                        if version_dir.is_dir() and (version_dir / "skills").is_dir():
                            return True
                except OSError:
                    continue
        except OSError:
            continue
    return False
```

`Path.rglob` does not follow symlinks by default in Python 3.10-3.13, so symlink loops can't deadlock the scan. The name-prefix predicate keeps the walk narrow even on directories with many sibling plugins.

This change is forward-only: repos already pinned to `skills_source: vendored` keep that pinning. The deck has a separate concern (worth filing later) around offering a one-shot `goc repair` or similar to re-resolve `skills_source` against a fixed detector, but that's out of scope for this card.

## Empirical evidence

See `reproduce.py`. Pre-fix it exits 1 with `_claude_plugin_present() returned False for a versioned layout`; post-fix it exits 0.
