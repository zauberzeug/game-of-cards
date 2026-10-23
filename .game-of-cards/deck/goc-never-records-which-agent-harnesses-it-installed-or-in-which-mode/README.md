---
title: goc-never-records-which-agent-harnesses-it-installed-or-in-which-mode
summary: "goc install records neither which agent harnesses it set up nor each one's skills mode, so goc upgrade and goc validate re-derive both from proxies on every run: skill-tree folders, a skills_source value that only describes Claude, and whether the machine running the check has the Claude plugin. Each proxy is wrong for some supported install, which has produced a dual install whose upgrade drops Claude, Codex installs whose vendored skills are never parity-checked, and a Codex install-default decision that cannot be taken without a per-host mode. One mechanism decision, record install state or keep inferring it, answers all three."
status: open
stage: null
contribution: high
created: "2026-10-23T04:44:50Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: the mechanism is decided via `goc decide` on this card (Option A, record install state, or Option B, keep inferring it), with the reason
  - [ ] PROCESS: if Option A, this card's body states the record's shape and the one-time backfill rule for existing installs, so the instance cards implement one rule
  - [ ] PROCESS: `goc-upgrade-drops-plugin-mode-claude-in-dual-claude-codex-installs`, `codex-only-install-pins-skills-source-to-plugin-skipping-parity-check` and `codex-install-defaults-to-plugin-path` each get a log.md entry naming the option they take under the decision, and their `## Decision required` sections are updated to match
---

# goc never records which agent harnesses it installed, or in which mode

## Location

- `goc/install.py:1943`:
  `chosen_source = "vendored" if "claude" in local_skills_agents else "plugin"`.
  This is the only install state `goc install` writes. It holds a single value,
  and that value is derived from Claude alone.
- `goc/install.py:468-488`: `_detect_installed_surfaces` "Uses each harness's
  skill-tree directory as the canonical install marker". `goc upgrade` consumes
  it at `goc/install.py:2066`: `default_agents = installed or DEFAULT_AGENTS`.
- `goc/engine.py:1480`: `validate_skill_dir_parity` returns `[]` when
  `effective_skills_source() == "plugin"`, before it checks either
  `.claude/skills` or `.codex/skills`.
- `goc/engine.py:5819`: in a repo with no pin,
  `return "plugin" if _claude_plugin_present() else "vendored"` decides by
  what is installed on the machine running the check.

## What's broken

Each question about an install is answered by a proxy, recomputed on every
`goc upgrade` and `goc validate`:

| question | proxy today | wrong for |
|---|---|---|
| Is Claude installed? | `.claude/skills/` exists | plugin-mode Claude, the default, which writes no `.claude/skills/` |
| Is Codex installed? | `.codex/skills/` exists | nothing yet, because every Codex install vendors. It breaks as soon as Codex can use its plugin |
| Claude's skills mode | `skills_source` | codex-only installs, which pin `plugin` although no Claude exists |
| Codex's skills mode | the same `skills_source` value | every install that does not vendor Claude, whose Codex tree then goes unchecked |
| Any mode, unpinned repo | the validating machine's Claude plugin | the same repo, which passes on one machine and fails on another |

The instances, all from this one root:

- [goc-upgrade-drops-plugin-mode-claude-in-dual-claude-codex-installs](../goc-upgrade-drops-plugin-mode-claude-in-dual-claude-codex-installs/)
  (open, decision). A no-flag `goc upgrade` in a `claude,codex` repo drops
  Claude. Its four candidate signals are this card's question asked from the
  upgrade side. Its option 3 is a per-agent install ledger, and its option 1
  (`skills_source`) fails because of the codex-only pin.
- [codex-only-install-pins-skills-source-to-plugin-skipping-parity-check](../codex-only-install-pins-skills-source-to-plugin-skipping-parity-check/)
  (open, decision). The Claude-derived pin switches off the Codex tree's
  parity check. Its Option B, a per-host key, is the full form of Option A
  below.
- [codex-install-defaults-to-plugin-path](../codex-install-defaults-to-plugin-path/)
  (open, decision). Its options B and C make Codex's mode vary per repo,
  which only a record or a new Codex proxy can carry.
- [upgrade-default-adds-claude-to-codex-repos](../upgrade-default-adds-claude-to-codex-repos/)
  (done 2026-05-05). Its fix introduced the skill-tree proxy, which fixed
  codex-only repos and broke dual ones. It is the family's first instance and
  the cause of the second.

Out of scope: [goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install](../goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install/)
asks which *files* GoC owns, not which hosts and modes it installed.
[install-auto-detects-codex-from-the-shared-agents-md-briefing-file](../install-auto-detects-codex-from-the-shared-agents-md-briefing-file/)
asks which hosts a user has *before* the first install. A record of install
state would answer neither.

## Empirical evidence

Both live instances reproduce on main at `0a457032` (2026-10-23).
`goc-upgrade-drops-plugin-mode-claude-in-dual-claude-codex-installs/reproduce.py`:

```text
installed_claude_in_plugin_mode = 'skills_source: plugin' (no .claude/skills: True)
.claude/skills present          = False
.codex/skills present           = True
_detect_installed_surfaces      = ('codex',)
no-flag upgrade would target    = ('codex',)

DEFECT CONFIRMED: Claude was installed but a no-flag `goc upgrade` silently drops it (Claude briefing/import wiring never refreshed).
```

`codex-only-install-pins-skills-source-to-plugin-skipping-parity-check/reproduce.py`
exits 1. The codex-only, `claude,codex` and codex-only `--local-skills`
installs all pin `plugin`, and a deleted `.codex/skills/pull-card/` still
passes `goc validate`.

## Why it matters

Three high-contribution cards are parked on decisions that share this root.
Each local fix needs its own signal, and each signal is evaluated again on
every run, so its failure mode never goes away. The family has already
reopened once: the fix for `upgrade-default-adds-claude-to-codex-repos`
created the dual-install drop. Recording install state turns those per-run
guesses into one migration.

## Decision required

**Reasoning.** Option A adds a persisted contract to
`.game-of-cards/config.yaml`, a file `goc upgrade` never overwrites. Every
existing install also needs a one-time backfill, inferred from the same
proxies this card calls wrong. Option B adds nothing persistent but keeps one
heuristic per question alive for good. Both are defensible, and choosing
which one the project owns is a maintainer call.

**Option A: record install state at install time.**
In its smallest form, `skills_source` is written only when Claude is
installed and describes only Claude: its presence records Claude, and its
value records Claude's mode. Codex needs no entry while every Codex install
vendors `.codex/skills/`. It gets one, in the per-host form of the codex-only
card's Option B, if `codex-install-defaults-to-plugin-path` moves Codex to the
plugin. `goc upgrade` backfills each existing install once. A `plugin` pin
with no Claude briefing footprint in `CLAUDE.md` is a codex-only install and
loses the key. A footprint with no pin is a pre-pin Claude install and gains
one. The footprint signal is the upgrade card's option 4.

- Pros: upgrade reads "Claude is installed" from the record instead of
  guessing, so the dual-install drop is fixed without a per-run heuristic.
  The codex-only card's fix becomes principled, and Codex install-default B
  or C reduces to adding a Codex entry. Inference survives only in the
  backfill, once per repo.
- Cons: codex-only installs stop writing the key, which changes what
  `goc install` writes. The backfill can misread a repo that an earlier
  upgrade already damaged. Install, upgrade, validate, AGENTS.md and the
  tests all change together.
- Preview: `goc/install.py:1943-1944` pins only `if "claude" in agents`.
  `goc/install.py:468-488` reads the record before the skill-tree folders.
  `goc/install.py:2094-2100`, `:2139` and `:2212` read and re-pin from it.
  `goc/engine.py:1480` applies the `plugin` skip to `.claude/skills` only.
  The `skills_source` section of `AGENTS.md` is rewritten to match.

**Option B: keep inferring, and give each instance its own signal.**
The codex-only card takes its Option A, the validator scope only. The upgrade
card picks one of its signals, most likely its option 4, which is evaluated
on every upgrade. The Codex install-default card adds a Codex proxy if it
picks B or C.

- Pros: nothing new is persisted, no backfill is needed, and each fix is
  small and ships alone.
- Cons: every signal runs on every upgrade or validate, so each failure mode
  the upgrade card lists stays live instead of being paid once. Three signals
  must stay consistent with each other, and the next host or mode reopens the
  family.
- Preview: `goc/engine.py:1480` is scoped as in Option A.
  `goc/install.py:468-488` gains a Claude-footprint check.
  `goc/install.py:1943` is unchanged.

**Recommendation:** Option A in its smallest form. It replaces a heuristic
that runs every time with a backfill that runs once, and its first step, the
validator scope at `goc/engine.py:1480`, is the change the codex-only card
already recommends, so that work is kept if the call goes to Option B.
