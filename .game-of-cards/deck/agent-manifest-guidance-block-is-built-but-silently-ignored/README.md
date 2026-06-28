---
title: agent-manifest-guidance-block-is-built-but-silently-ignored
summary: "The Claude agent manifest declares a `guidance` block intended to drive briefing writes to `CLAUDE.md`, and `_load_agent_shim` builds `GuidanceBlock` tuples from it onto `AgentShim.guidance` — but nothing in the codebase reads that attribute. The actual briefing flow uses hardcoded `AGENTS_GUIDANCE` / `CLAUDE_GUIDANCE` module constants. The dead schema misleads any future agent-shim author who adds a `guidance` block expecting it to take effect."
status: open
stage: null
contribution: medium
created: "2026-06-02T04:39:27Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: Decision recorded on the card body (Option A or B) with a one-line rationale.
  - [ ] MECHANICAL: Implementation lands consistently per the chosen option — `manifest.json` files, `AgentShim` definition, and `_load_agent_shim` updated together.
  - [ ] TDD: `uv run python .game-of-cards/deck/agent-manifest-guidance-block-is-built-but-silently-ignored/reproduce.py` exits zero (dead-data inconsistency is gone).
  - [ ] TDD: `uv run python -m unittest discover -s tests` passes.
  - [ ] MECHANICAL: Plugin mirrors regenerated (`uv run python scripts/sync_plugin_assets.py`) if the engine package changed and committed alongside the fix.
  - [ ] PROCESS: `uv run goc validate` is clean.
---

# Agent manifest's `guidance` block is built but silently ignored

## Location

- `goc/install.py:107` — `AgentShim.guidance` field declaration
- `goc/install.py:342-356` — `_load_agent_shim` builds `GuidanceBlock` tuples from `manifest["guidance"]` and assigns them to the shim
- `goc/templates/agents/claude/manifest.json:17-23` — declares the block the engine never reads
- `goc/templates/agents/codex/manifest.json:13` — declares `guidance: []`
- `goc/install.py:111-112, 136-140` — the actual briefing flow reads from module-level constants `AGENTS_GUIDANCE` / `CLAUDE_GUIDANCE`, not from the per-agent shim

## What's broken

The Claude manifest declares a per-agent briefing fragment:

```json
"guidance": [
  {
    "source": "CLAUDE_GOC.md",
    "target": "CLAUDE.md",
    "header": "# Claude Code Guidelines"
  }
]
```

`_load_agent_shim` faithfully builds it into `AgentShim.guidance`:

```python
guidance = tuple(
    GuidanceBlock(
        path=guidance_spec["target"],
        template=guidance_spec["source"],
        header=guidance_spec["header"],
    )
    for guidance_spec in raw.get("guidance", [])
)
...
return AgentShim(
    name=raw.get("name", agent),
    skills=skills,
    files=files,
    guidance=guidance,
    settings_json=settings_json,
)
```

But nothing reads `AgentShim.guidance` anywhere in `goc/`, `tests/`, or `scripts/`. The briefing flow instead uses hardcoded module constants:

```python
AGENTS_GUIDANCE = GuidanceBlock("AGENTS.md", "AGENTS_GOC.md", "# Agent Guidelines")
CLAUDE_GUIDANCE = GuidanceBlock("CLAUDE.md", "CLAUDE_GOC.md", "# Claude Code Guidelines")
...
def _briefing_body(briefing_target: str, ...):
    agents_body = (templates / AGENTS_GUIDANCE.template).read_text().rstrip()
    if briefing_target == "CLAUDE.md":
        claude_body = (templates / CLAUDE_GUIDANCE.template).read_text().rstrip()
        return f"{agents_body}\n\n{claude_body}\n"
    return agents_body + "\n"
```

The Codex manifest's `guidance: []` is consistent with the hardcoded
behavior (only Claude gets the extra `CLAUDE_GOC.md` fragment), which
reinforces that the schema field is descriptive of *historical*
behavior — when each agent had its own duplicated briefing — that was
superseded by the single-home design without removing the now-dead
field.

## Empirical evidence

```text
$ grep -rn "shim\.guidance\|AgentShim(.*guidance" goc/ tests/ scripts/
goc/install.py:107:    guidance: tuple[GuidanceBlock, ...]
goc/install.py:355:        guidance=guidance,

$ grep -rn "AGENTS_GUIDANCE\|CLAUDE_GUIDANCE" goc/ tests/
goc/install.py:111:AGENTS_GUIDANCE = GuidanceBlock(...)
goc/install.py:112:CLAUDE_GUIDANCE = GuidanceBlock(...)
goc/install.py:136:    agents_body = (templates / AGENTS_GUIDANCE.template).read_text()...
goc/install.py:138:        claude_body = (templates / CLAUDE_GUIDANCE.template).read_text()...
```

The first grep returns only the field's declaration site and the
keyword argument at construction — no consumer reads. The second
shows the actual briefing flow reads from module-level constants.
See `reproduce.py` for the full empirical confirmation.

## Why it matters — reachability

The card [multi-agent-shim-which-agents-at-v1](../multi-agent-shim-which-agents-at-v1/)
decided the v1 agent set is Claude + Codex with a published "to add
agent X, file a PR" extension story. The Claude manifest is the
reference implementation a community contributor reads when adding a
new agent shim.

A contributor who reads `goc/templates/agents/claude/manifest.json`
will see the `guidance` array, conclude it drives the briefing write,
and copy the analogous block into their new manifest. It will silently
not take effect. They will then debug — wasting their time — and
eventually discover that the briefing flow is hardcoded against
`AGENTS_GUIDANCE` / `CLAUDE_GUIDANCE` constants.

Reachability path: `goc install` / `goc upgrade` → `_load_agent_shim`
reads `manifest.json` → builds dead `guidance` data on every install
→ `_sync_agent_harness` calls `_briefing_body` → ignores the shim's
`guidance` field, reads constants.

## Decision required

Two credible fix paths.

**Option A — Delete the dead schema.** Treat the manifest's
`guidance` field as legacy noise and remove it.

1. Remove `guidance: [...]` from `goc/templates/agents/claude/manifest.json`.
2. Remove `guidance: []` from `goc/templates/agents/codex/manifest.json`.
3. Drop `guidance` from `AgentShim` and the build loop in `_load_agent_shim`.
4. Keep `AGENTS_GUIDANCE` / `CLAUDE_GUIDANCE` constants (or inline
   them) — the briefing flow stays unchanged.
5. Add a regression test asserting `AgentShim` has no `guidance`
   attribute, so the schema doesn't silently grow back.

**Option B — Wire up the manifest.** Treat the manifest as the
source of truth and have the briefing flow derive from it.

1. Make `_briefing_body` accept the `AgentShim` (or its `guidance`
   tuple) and read per-agent fragments from there.
2. Move the shared `AGENTS_GOC.md` declaration to a top-level
   manifest field or keep it as a single shared constant.
3. Document the manifest's `guidance` field as the authoritative
   knob for "what fragment lands in this agent's briefing target."
4. Update `multi-agent-shim-which-agents-at-v1`'s extension docs
   accordingly so contributors know the field works.

**Trade-off.** Option A is a one-pass cleanup that admits the design
has converged on a single shared briefing (the `CLAUDE_GOC.md` extra
fragment is the only deviation, and it can stay as a constant). Option
B is a forward-looking knob that lets future agents declare custom
briefing fragments without a code change — but no concrete need for
that knob has materialized in v1 (Codex declares `guidance: []`).

**Recommendation: Option A.** The field models an arity (per-agent
custom fragment) the project no longer expresses. Removing it tightens
the schema against the contributor-confusion failure mode above.

## Fix

See [Decision required](#decision-required). Once chosen, apply the
steps under that option.

## Dedup

Checked against the open / done / disproved queues for
`manifest`, `guidance`, `shim`. Closest neighbors:

- [multi-agent-shim-which-agents-at-v1](../multi-agent-shim-which-agents-at-v1/)
  (done) — established the agent shim system and the manifest format.
  Does not address the dead-data inconsistency.
- [generated-agents-guidance-overstates-done-commit](../generated-agents-guidance-overstates-done-commit/)
  (done) — generated-guidance prose, unrelated to the manifest field.
- [shrink-root-guidance-files-by-moving-content-into-skills](../shrink-root-guidance-files-by-moving-content-into-skills/)
  (done) — briefing-volume concern, not schema redundancy.
- [derive-claude-hook-manifest-from-templates](../derive-claude-hook-manifest-from-templates/)
  (done) — addresses the hooks manifest, not the guidance manifest.

No prior card identifies the manifest's `guidance` field as dead data.
