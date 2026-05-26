---
title: openclaw-plugin-ported-skills-drift-silently-from-templates
summary: "The `openclaw-plugin/skills/` copies are hand-ported from `goc/templates/skills/` and, unlike the byte-for-byte-synced claude/codex mirrors, are not covered by any drift tripwire. They have silently rotted: re-running the porter rewrites 11 of 15 skills, so OpenClaw consumers receive stale skill guidance and CI cannot detect it."
status: done
stage: null
contribution: medium
created: "2026-05-26T13:05:49Z"
closed_at: 2026-05-26T19:46:13Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] `openclaw-plugin/skills/` is re-ported from the current templates (`python3 scripts/port_skills_to_openclaw.py`); the diff is reviewed (watch for the known porter quirk that strips `!cat` lines above the H1) and committed, leaving no template→port drift.
  - [x] A drift guard exists — a porter `--check` mode or a test — that fails when `openclaw-plugin/skills/` differs from a fresh re-port (i.e. asserts the porter is idempotent), wired into CI next to `python scripts/sync_plugin_assets.py --check`.
  - [x] The guard is demonstrated: it goes red on a deliberately-stale ported skill and green after a re-port.
worker: {who: "claude[bot]", where: main}
---

# openclaw-plugin-ported-skills-drift-silently-from-templates

## Summary

OpenClaw plugin skills live at `openclaw-plugin/skills/<name>/SKILL.md`. They are
**hand-ported** from the source-of-truth `goc/templates/skills/<name>/SKILL.md`
via `scripts/port_skills_to_openclaw.py` (the porter applies Codex/OpenClaw
invocation-neutral edits). Per `AGENTS.md`, these copies are deliberately **not**
part of the auto-sync that keeps `claude-plugin/` and `codex-plugin/` byte-for-byte
identical to source — the porter "runs once during scaffold" and the skills are
"independently maintained from then on."

The consequence: there is **no drift detector** for the ported OpenClaw skills.
The `claude-plugin`/`codex-plugin` engine + skill mirrors are rot-proofed by
`scripts/sync_plugin_assets.py --check` in CI. The OpenClaw ported skills have no
equivalent guard, so template edits that postdate the last port accumulate
silently.

## Empirical Evidence

On 2026-05-26, while closing `openclaw-kickoff-defaults-to-claude-install`, a
single-clause edit to the `openclaw-kickoff` template was followed by a re-port to
propagate it. Running `python3 scripts/port_skills_to_openclaw.py` rewrote **11 of
15** skills — far more than the one touched:

```
advance-card, card-schema, create-card, deck, finish-card, kickoff,
next-card, openclaw-kickoff, pull-card, refine-deck, scan-deck
```

The diffs were not cosmetic. Examples of contract drift the ported copies were
missing relative to current templates:

- the **impediment overlay** (`waiting_on` / `waiting_until`, `goc wait`) — absent
  from the ported `advance-card`;
- the **typed supersession link** — ported `advance-card` still documented
  `goc status <title> superseded` without the `--by <successor>` flag that sets
  the bidirectional `superseded_by` / `supersedes` edge;
- updated invocation phrasing ("run `goc show <title>` yourself with the real
  title bound").

That re-port churn was reverted as out-of-scope for that card; this card tracks
doing it properly.

## Why It Matters

OpenClaw consumers install these skills and act on them. Stale skill bodies teach a
workflow the engine no longer matches — e.g. an agent following the ported
`advance-card` would record a supersession without the typed link the validator and
record-axis now expect, or never learn the impediment overlay exists. Because the
byte-for-byte sync tripwire explicitly excludes OpenClaw skills, CI stays green
while the guidance rots. The drift is invisible until someone happens to re-port.

## Location

- `openclaw-plugin/skills/` — the 15 ported skill copies (drifted).
- `goc/templates/skills/` — source of truth.
- `scripts/port_skills_to_openclaw.py` — the porter; needs an idempotence/`--check`
  mode.
- `scripts/sync_plugin_assets.py` — the analogous guard for claude/codex; the model
  to follow.
- `AGENTS.md` "OpenClaw plugin payload" section — documents the manual-port policy;
  update if the guard changes the contract.

## Fix Directions

1. **Re-port + commit** (clears the current backlog): run the porter, review the
   diff carefully (the porter has a known quirk — `PREFLIGHT_RE` greedily strips
   `!cat` injection lines above a skill's H1; see project memory), commit.
2. **Add a drift guard** (the durable fix): give the porter a `--check` mode (or a
   pytest) that re-ports into a temp tree and diffs against the committed
   `openclaw-plugin/skills/`, failing on any difference. Wire it into CI beside
   `sync_plugin_assets.py --check`. Without this, the skills will rot again.
3. **Optional:** fold the re-port into the `sync-plugin-assets` pre-commit hook so
   OpenClaw skills auto-regenerate-and-stage like the claude/codex mirrors. The
   reason they are separate today is the porter's non-trivial normalization, but
   that can run in the hook too. Decide whether manual review of ported output is
   still wanted before adopting this.

## Origin

Discovered during `openclaw-kickoff-defaults-to-claude-install` (closed
2026-05-26): re-porting to propagate one template edit revealed the broader
backlog. That card kept its scope to the engine fix and reverted the porter churn;
this card owns the re-port and the missing guard.
