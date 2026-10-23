---
title: codex-only-install-pins-skills-source-to-plugin-skipping-parity-check
summary: "CONFIRMED by reproduce.py (2026-10-23), and wider than filed: every install that vendors `.codex/skills/` without vendoring Claude (codex-only, mixed `claude,codex`, even codex-only `--local-skills`) pins `skills_source: plugin`, and `validate_skill_dir_parity` then returns `[]` before it reaches either tree. A GoC skill missing from the vendored Codex tree therefore never fails `goc validate`. Open: whether the key describes Claude only or every host, see `## Decision required`."
status: open
worker: {who: "claude[bot]", where: main}
stage: null
contribution: high
created: "2026-05-27T14:02:43Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: a reproduce.py runs a codex-only `goc install` into a temp repo and asserts `.game-of-cards/config.yaml` records `skills_source: plugin` while `.codex/skills/` holds real vendored files and no Claude plugin exists — or disproves the claim.
  - [x] TDD: after simulating drift (delete a vendored `.codex/skills/<verb>/`), assert the parity validator returns `[]` (drift unreported) under the bad pin, and reports the missing skill once corrected.
  - [ ] PROCESS: decide the correct `skills_source` semantics for codex-only / multi-agent installs (does `plugin` mean "Claude plugin specifically", and should codex vendoring be tracked independently?). Record verdict in log.md.
  - [ ] TDD: a regression test in `tests/` pins the decided rule: drift in a vendored `.codex/skills/` fails `goc validate` after a codex-only, a mixed `claude,codex` and a codex-only `--local-skills` install, and reproduce.py exits 0.
  - [ ] MECHANICAL: the decided fix lands (the validator's `plugin` skip, plus the install pick and the upgrade re-pin if the option needs them), and the `skills_source` table in AGENTS.md says which host the key describes.
---

# Codex-only install pins `skills_source: plugin`, skipping the parity check

> **Confirmed 2026-10-23** by `reproduce.py`, which exits 1. The defect is
> wider than the title. It hits every install that vendors Codex without
> vendoring Claude, not only codex-only ones.

## Location

- `goc/install.py:1943`:
  `chosen_source = "vendored" if "claude" in local_skills_agents else "plugin"`.
  The pin asks only whether Claude is vendored.
- `goc/install.py:606`: `_should_use_local_skills` returns
  `agent != "claude" or local_skills`, so Codex is vendored on every install,
  whatever the flag says.
- `goc/engine.py:1480`: `validate_skill_dir_parity` returns `[]` when
  `effective_skills_source() == "plugin"`, before its loop over
  `.claude/skills` and `.codex/skills` (`:1488`). The docstring gives a reason
  for skipping `.claude/skills/` and none for `.codex/skills/`.
- `goc/engine.py:1497-1499`: the drift message tells both trees to run
  `goc upgrade --keep-local-skills` or to "set `skills_source: plugin` … to
  skip this check".
- `goc/install.py:2139`, `:2212`: `goc upgrade` reads and re-pins the key only
  `if "claude" in agents`, so no Codex upgrade ever revisits it.
- `AGENTS.md:320-329`: the section is titled "which install path owns
  `.claude/skills/`", but its table says `plugin` makes `goc validate` skip
  "the skill-dir parity check", which covers both trees. It also says
  `vendored` is "Written when `goc install --local-skills` is used", which is
  false for `--agents codex --local-skills`.

## What happens

`reproduce.py` installs into a temp repo with an empty HOME, so no Claude
plugin is present. It then deletes `.codex/skills/pull-card/` and runs
`goc validate`:

| install | pin written | parity validator after the deletion | `goc validate` |
|---|---|---|---|
| `--agents codex` | `plugin` | `[]` | exit 0 |
| `--agents claude,codex` | `plugin` | `[]` | exit 0 |
| `--agents codex --local-skills` | `plugin` | `[]` | exit 0 |

With the pin flipped to `vendored`, the same check reports
`.codex/skills: missing skills ['pull-card']` in all three rows. The check
works, and only the pin hides the drift. The mixed row is the one the
original DoD missed. There the pin is right for Claude, so fixing the install
pick alone cannot fix that row: the validator applies a value that describes
Claude to the Codex tree. `goc install` picks that mixed set on its own in any
repo that has both a Claude signal and a Codex signal (`AGENT_SIGNAL_PATHS`,
`goc/install.py:51`).

Repos installed before the key existed resolve `auto` through
`_claude_plugin_present()`. A legacy codex-only repo with a deleted Codex
skill was checked by hand on 2026-10-23. `goc validate` exits 1 on a host
without the Claude plugin and 0 on a host with it, so whether the Codex tree
is checked depends on Claude state on the machine that runs the check.

Plain `goc upgrade` restores the deleted directory and leaves the pin alone in
both the codex-only and the mixed repo. The drift can be repaired, but nothing
reports it. The drift message's `--keep-local-skills` advice is wrong for the
Codex tree: run with `--agents claude,codex`, it vendors Claude's skills,
hooks and settings entries and re-pins `skills_source: vendored`.

## Why it matters

The parity check is the only guard that keeps a vendored skill tree in step
with the templates of the goc that validates it. Every Codex consumer who did
not vendor Claude has that guard switched off. A goc release that adds a
skill, or a skill directory deleted by hand, still passes `goc validate` and CI.

## Decision required

**Reasoning.** The 2026-05-30 directive in log.md held the semantics back
until the defect was confirmed, and it now is. The fix depends on what
`skills_source` describes.
[codex-install-defaults-to-plugin-path](../codex-install-defaults-to-plugin-path/)
raises the same question: its option B says the key "must then say which
host it describes". Picking blindly risks per-host plumbing that option A of
that card never needs, or a Claude-only reading that its options B and C
would have to reopen.

**Option A: the key describes Claude only, and a vendored Codex tree is always checked.**
One value, read only for `.claude/skills/`. `.codex/skills/` counts as
vendored whenever it exists, which every install makes true today.

- Pros: the code already reads the key this way everywhere except the
  validator's early return. Install pins from Claude's mode, upgrade reads and
  re-pins it only when Claude is an agent, and AGENTS.md titles the section
  after `.claude/skills/`. The fix is small and single-site, and it turns the
  guard on for every Codex consumer at once.
- Cons: if `codex-install-defaults-to-plugin-path` later picks its B or C,
  the Codex check needs a signal of its own, and this reading must grow one
  then. Consumers whose Codex tree has already drifted see `goc validate` fail
  until they run `goc upgrade`.
- Preview: at `goc/engine.py:1480` the `plugin` skip moves inside the loop and
  skips only `.claude/skills`. The Codex tree's message at `:1497-1499` drops
  the `skills_source: plugin` escape and points at plain `goc upgrade`, which
  resyncs `.codex/skills/` in every mode. `AGENTS.md:328-329` says the key
  covers Claude only and that `--local-skills` does not change it on a
  codex-only install. Install and upgrade stay as they are.

**Option B: the key becomes per-host.**
Store Codex's mode beside Claude's, either as a mapping such as
`skills_source: {claude: plugin, codex: vendored}` or as a second key. Install
writes both, upgrade re-pins both, and the validator checks each tree against
its own value.

- Pros: one model for every host. It is needed anyway if
  `codex-install-defaults-to-plugin-path` picks B (Codex defaults to the
  plugin) or C (per-host detection). A per-host record would also tell
  `goc upgrade` that Claude is installed, which is the signal
  `goc-upgrade-drops-plugin-mode-claude-in-dual-claude-codex-installs`
  lacks (its option 3).
- Cons: it changes the config format, `get_skills_source` /
  `effective_skills_source`, `_write_skills_source`, install, upgrade, the
  validator and every doc that names the key, and repos already pinned to the
  single value need a migration. All of that describes a Codex mode that has
  only one possible value today.
- Preview: `goc/engine.py:5738` and `:5808` read a per-host value;
  `goc/install.py:1832` writes one; `:1943` pins Codex from
  `local_skills_agents`; `:2139` and `:2212` re-pin for Codex too; the loop at
  `goc/engine.py:1488` picks each tree's value.

**Recommendation:** Option A, decided together with
`codex-install-defaults-to-plugin-path`. It is right for today's
always-vendored Codex and fixes every Codex consumer with one change. If that
card moves Codex to the plugin, B's per-host value can later replace A's
"always check Codex" without reverting anything.

## Related decision

[codex-install-defaults-to-plugin-path](../codex-install-defaults-to-plugin-path/)
decides whether Codex installs keep vendoring `.codex/skills/` now that the
Codex plugin ships. Its option A pairs with Option A here. Its options B and
C need Option B here. Decide the two together.

Root: [goc-never-records-which-agent-harnesses-it-installed-or-in-which-mode](../goc-never-records-which-agent-harnesses-it-installed-or-in-which-mode/)
asks whether `goc install` should record install state at all. Its smallest
form is Option A here, plus writing the pin only when Claude is installed.
Its full form is Option B here. Either way, the validator scope at
`goc/engine.py:1480` comes first.

## Reproduce

```bash
uv run python .game-of-cards/deck/codex-only-install-pins-skills-source-to-plugin-skipping-parity-check/reproduce.py
```

The script exits 1 while the defect fires. It exits 0 once drift in a vendored
`.codex/skills/` fails `goc validate` after all three installs, or once an
install stops vendoring that tree. It exits 2 if the harness breaks.

Surfaced by: general-purpose audit hunter (install/sync seam), 2026-05-27.
