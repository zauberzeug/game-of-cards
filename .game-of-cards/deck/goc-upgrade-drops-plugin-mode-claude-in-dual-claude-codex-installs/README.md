---
title: goc-upgrade-drops-plugin-mode-claude-in-dual-claude-codex-installs
summary: "A no-flag `goc upgrade` in a dual `--agents claude,codex` install silently drops Claude. `_detect_installed_surfaces` uses each harness's skill-tree directory as the sole install marker, but plugin-mode Claude (the default) writes no `.claude/skills/`. Codex being vendored makes `installed` non-empty, so the `installed or DEFAULT_AGENTS` fallback never restores Claude and its briefing/import wiring is never refreshed."
status: open
stage: null
contribution: high
created: "2026-07-01T01:33:53Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: Decision recorded — which signal reliably identifies a plugin-mode Claude install without re-introducing the ambient-`CLAUDE.md` over-detection that `upgrade-default-adds-claude-to-codex-repos` fixed.
  - [ ] TDD: reproduce.py exits zero (a dual claude+codex install's no-flag upgrade retains `claude` in the default agent set).
  - [ ] TDD: regression coverage exercises no-flag upgrade for plugin-mode-Claude + vendored-Codex, plugin-mode-Claude-only, and vendored-Claude-only installs.
  - [ ] TDD: a genuinely Codex-only repo (no Claude ever installed) still does NOT gain Claude on no-flag upgrade — the fix must not regress the sibling.
  - [ ] MECHANICAL: `uv run goc validate` passes.
---

# `goc upgrade` drops plugin-mode Claude in dual claude+codex installs

## Location

- `goc/install.py:411-432` — `_detect_installed_surfaces` (the detector)
- `goc/install.py:1686-1687` — `upgrade()` consumes it: `default_agents = installed or DEFAULT_AGENTS`
- `goc/install.py:1566-1567` — `goc install` pins `skills_source` (`vendored` iff Claude vendored, else `plugin`)

## What's broken

`upgrade()` chooses which agent harnesses a no-flag `goc upgrade` refreshes
from `_detect_installed_surfaces`, which detects an install purely by the
presence of that harness's skill-tree directory:

```python
def _detect_installed_surfaces(target, templates, *, supported_agents=SUPPORTED_AGENTS):
    """... Uses each harness's skill-tree directory as the canonical install
    marker, since those paths are agent-specific ..."""
    detected: list[str] = []
    for agent in supported_agents:
        ...
        if shim.skills and (target / shim.skills.target).is_dir():
            detected.append(agent)
    return tuple(detected)
```

But **plugin mode is the default for Claude Code** — `goc install` without
`--local-skills` writes `skills_source: plugin` and deliberately creates **no**
`.claude/skills/` tree (skills come from the plugin payload). So a plugin-mode
Claude install leaves no skill directory and is invisible to this detector.

For a Claude-only plugin repo the bug is masked: `_detect_installed_surfaces`
returns `()`, and `upgrade()`'s fallback `default_agents = installed or
DEFAULT_AGENTS` yields `("claude",)`, which happens to be correct. The failure
surfaces in a **dual `goc install --agents claude,codex`** repo: Codex vendors
`.codex/skills/`, so `installed == ("codex",)` is non-empty, the fallback never
fires, and Claude is silently dropped from the upgrade.

Because `"claude" not in agents`, the upgrade never runs `_sync_claude_import`
or refreshes the Claude briefing block: `CLAUDE.md` keeps pointing at whatever
it did before, the AGENTS.md GoC block may be re-pointed for Codex, and Claude
Code loses its methodology briefing on a routine `goc upgrade` — no error, no
warning.

This is the exact inverse blind spot of the closed card
[upgrade-default-adds-claude-to-codex-repos](../upgrade-default-adds-claude-to-codex-repos/),
whose fix *introduced* `_detect_installed_surfaces` to stop a no-flag upgrade
from adding Claude to Codex-only repos.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-upgrade-drops-plugin-mode-claude-in-dual-claude-codex-installs/reproduce.py` (trailing lines):

```text
installed_claude_in_plugin_mode = 'skills_source: plugin' (no .claude/skills: True)
.claude/skills present          = False
.codex/skills present           = True
_detect_installed_surfaces      = ('codex',)
no-flag upgrade would target    = ('codex',)

DEFECT CONFIRMED: Claude was installed but a no-flag `goc upgrade` silently
drops it (Claude briefing/import wiring never refreshed).
```

## Why it matters

`goc install --agents claude,codex` is a documented, supported flow, and a
no-flag `goc upgrade` is advertised as *the* basic upgrade command. A user who
follows both loses the Claude briefing on the next upgrade with no diagnostic.
The reachability path is entirely inside shipping code: `install()` at
`install.py:1554-1567` writes plugin-mode Claude + vendored Codex; the next
`upgrade()` at `install.py:1686` reads `_detect_installed_surfaces` and drops
Claude.

## Decision required

The fix is a detector change, but the *right signal* for "Claude was installed
in plugin mode" is a genuine judgment call, and the obvious candidates each
have a failure mode:

1. **Read `skills_source` from `.game-of-cards/config.yaml`.** Clean and
   already the repo's persisted mode marker — but `goc install` writes
   `skills_source` **unconditionally** (`plugin` even for a *codex-only*
   install, `install.py:1566`), so `skills_source: plugin` alone does NOT
   prove Claude was installed. Would need pairing with another Claude-specific
   signal.
2. **Union with `_detect_agent_surfaces` (ambient `CLAUDE.md` / `.claude/`
   signals).** Directly re-introduces the over-detection that
   `upgrade-default-adds-claude-to-codex-repos` fixed: a Codex-only repo that
   merely *has* a hand-written `CLAUDE.md` would gain Claude on upgrade.
3. **Add a per-agent install ledger** (e.g. record installed agents in
   `config.yaml` at install time) and detect from that. Most robust, but a new
   persisted field and a migration path for existing installs.
4. **Detect plugin-mode Claude from its briefing/import footprint** (a
   GoC-managed `@AGENTS.md`/`@CLAUDE.local.md` import in `CLAUDE.md`), which
   only a Claude install writes — but this must be distinguished from a
   user-authored import to avoid option 2's regression.

Pick the signal (or combination) before implementing. The DoD's Codex-only
regression box guards against reintroducing the sibling bug.
