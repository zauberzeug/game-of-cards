---
title: install-auto-detects-codex-from-the-shared-agents-md-briefing-file
status: open
stage: null
contribution: high
created: "2026-06-21T09:47:09Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: Decision recorded in `## Decision` — which signals are agent-exclusive enough to drive `goc install` auto-detection, and how to keep detecting a fresh Codex repo without false-positiving on `AGENTS.md`
  - [ ] TDD: reproduce.py exits zero before the fix, nonzero after (no over-detection in either case)
  - [ ] TDD: a Claude repo (CLAUDE.md + AGENTS.md briefing, no `.codex`) does NOT auto-install the Codex harness under a bare `goc install`
  - [ ] TDD: a Codex repo (AGENTS.md + `.codex`, plus a cross-agent `.mcp.json`) does NOT auto-install the Claude harness under a bare `goc install`
  - [ ] TDD: a genuine fresh Codex repo is still auto-detected per the recorded decision (no regression of the intended convenience)
  - [ ] MECHANICAL: `goc install --help` text reconciled if the "auto-detect Claude/Codex project markers" wording changes
  - [ ] PROCESS: `uv run goc validate` passes
---

# install-auto-detects-codex-from-the-shared-agents-md-briefing-file

`goc install`'s no-flag harness auto-detection treats `AGENTS.md` as a
Codex-exclusive marker and `.mcp.json` as a Claude-exclusive marker. Both are
**cross-agent** files, so the detector over-installs a harness the user never
asked for.

## Location

- `goc/install.py:49` — `AGENT_SIGNAL_PATHS` (the signal table)
- `goc/install.py:396` — `_detect_agent_surfaces` (consumes the table)
- `goc/install.py:1431` — install default flow: `detected_agents = _detect_agent_surfaces(target, ...)`

## What's broken

The signal table conflates each agent's *exclusive* install markers with
*shared* files that any agent (or no agent) may produce:

```python
AGENT_SIGNAL_PATHS = {
    "claude": (Path("CLAUDE.md"), Path(".claude"), Path(".mcp.json")),
    "codex": (Path("AGENTS.md"), Path(".codex")),
}
```

- **`AGENTS.md` is not a Codex marker.** It is GoC's *generic cross-agent
  briefing file* — `DEFAULT_BRIEFING_TARGET = "AGENTS.md"` (`goc/install.py:55`),
  and in this very repo `CLAUDE.md` is nothing but `@AGENTS.md`. AGENTS.md is the
  emerging universal agent-instructions standard, written by Claude-only setups
  too.
- **`.mcp.json` is not a Claude marker.** It is the Model Context Protocol
  config, consumed by many MCP clients (Codex included), not a Claude-exclusive
  artifact.

`_detect_agent_surfaces` returns *every* agent with any matching signal:

```python
def _detect_agent_surfaces(target, *, supported_agents=SUPPORTED_AGENTS):
    detected = []
    for agent in supported_agents:
        signals = AGENT_SIGNAL_PATHS.get(agent, ())
        if any((target / signal).exists() for signal in signals):
            detected.append(agent)
    return tuple(detected)
```

So a Claude repo whose `CLAUDE.md` imports an `AGENTS.md` briefing is detected as
`('claude', 'codex')`, and a bare `goc install` scaffolds the **Codex** harness
(`.codex/skills/`, a Codex block in `AGENTS.md`) the user never requested. The
symmetric case: a Codex repo that uses MCP servers (`.mcp.json` present) is
detected as Claude too.

### The maintainers already know AGENTS.md is a false signal

The OpenClaw-plugin branch of `install()` guards against exactly this, but only
for that one context (`goc/install.py:1423`):

```python
if not explicit_agents and _is_openclaw_plugin_context():
    # OpenClaw ships skills/hooks via its plugin runtime and has no harness
    # surface, so the default is no harness — never the Claude fallback, and
    # never auto-detecting Codex from the AGENTS.md briefing this very install
    # writes. Explicit --agents still overrides below.
    detected_agents = ()
    default_agents = ()
```

The comment — *"never auto-detecting Codex from the AGENTS.md briefing"* — is the
smoking gun: AGENTS.md presence is a known false positive for Codex. The fix was
scoped only to the OpenClaw path; the ordinary Claude/Codex install path is still
exposed.

## Empirical evidence

`reproduce.py` (exits 0 — defect fires):

```
Case A (CLAUDE.md + AGENTS.md + .claude): detected = ('claude', 'codex')
Case B (AGENTS.md + .codex + .mcp.json): detected = ('claude', 'codex')

AGENT_SIGNAL_PATHS = {'claude': ['CLAUDE.md', '.claude', '.mcp.json'], 'codex': ['AGENTS.md', '.codex']}

DEFECT REPRODUCED:
  - Case A: 'codex' auto-detected from the shared AGENTS.md briefing in a Claude-only repo ...
  - Case B: 'claude' auto-detected from the cross-agent .mcp.json in a Codex repo ...
```

## Why it matters

`goc install` is the first command a new user runs. Auto-installing an unrequested
harness writes `.codex/` skill trees and an extra marker block into the user's
`AGENTS.md`, surprising them and creating drift they must notice and remove by
hand. It is the install-time mirror of the (closed,
`contribution: high`) [upgrade-default-adds-claude-to-codex-repos](../upgrade-default-adds-claude-to-codex-repos/),
which fixed the *upgrade* path by introducing `_detect_installed_surfaces`
(skills-dir as the canonical, agent-exclusive marker). The install default path
never adopted that canonical signal and still leans on the loose file table.

Reachability: `goc new` / kickoff write `AGENTS.md` as the default briefing
target, and many repos already carry an `AGENTS.md` and/or `.mcp.json` before
GoC is installed — so the false-positive input is the *common* case, not a
contrived one.

## Decision required

The naive fix — drop `AGENTS.md` from the Codex signals and `.mcp.json` from the
Claude signals — has a real cost: **`AGENTS.md` is the only pre-install signal
that says "this is a Codex repo."** A genuinely fresh Codex repo has no `.codex/`
directory yet, so removing `AGENTS.md` would make a bare `goc install` in a Codex
repo silently fall back to the Claude default — re-introducing the very
"wrong-agent default" class the upgrade card closed. Pick the resolution:

- **Option A — Contextual disambiguation.** Treat `AGENTS.md` as a Codex signal
  *only when no Claude-exclusive marker is present* (`CLAUDE.md` / `.claude`).
  `AGENTS.md` alone → Codex; `AGENTS.md` + `CLAUDE.md` → Claude only. Symmetrically
  drop `.mcp.json` from the Claude set (it is never a sole, reliable Claude
  signal — `.claude` covers real Claude installs). Preserves fresh-Codex
  detection; kills both false positives. Most surgical.
- **Option B — Exclusive-markers only.** Reduce the table to
  `claude: (CLAUDE.md, .claude)`, `codex: (.codex,)`. A fresh Codex repo (no
  `.codex` yet) then falls to the documented `claude` default unless `--codex` is
  passed. Simplest table; regresses fresh-Codex convenience (must teach users to
  pass `--codex`, and reconcile the `--help` wording).
- **Option C — Adopt the canonical detector.** Reuse the upgrade path's
  `_detect_installed_surfaces` (skills-dir marker) for the install default too,
  unifying the two detectors. But the skills dir only exists *after* an install,
  so for a truly fresh repo this degenerates to Option B's behavior — fold in a
  pre-install heuristic or accept the `claude` fallback.

Recommendation: **Option A** — it removes both false positives with the least
behavior change and keeps fresh-Codex auto-detection working. See the symmetric
prior art in `_detect_installed_surfaces`'s docstring on agent-exclusive markers.

## Fix (pending decision)

Per the chosen option, rewrite `AGENT_SIGNAL_PATHS` and/or
`_detect_agent_surfaces` at `goc/install.py:49`/`:396`, add regression coverage
mirroring `reproduce.py`'s two cases plus a fresh-Codex positive case, and
reconcile the `goc install --help` "auto-detect Claude/Codex project markers"
wording (`goc/cli.py`) if the contract changes. **Do not apply until the gate is
lowered.**
