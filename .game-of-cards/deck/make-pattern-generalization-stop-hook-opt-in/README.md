---
title: make-pattern-generalization-stop-hook-opt-in
summary: "Flip the pattern-generalization Stop hook from default-on (opt-out via hooks.pattern_generalization_check: false) to default-off (opt-in via hooks.pattern_generalization_check: true). A blocking Stop hook fires an extra agent round-trip on every code-mutating turn while a generalization card is warranted only occasionally — a poor ratio for an out-of-box default, and blocking Stop is the most intrusive hook class. User decided default-off on 2026-06-26."
status: active
stage: null
contribution: medium
created: "2026-06-26T02:58:20Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] TDD: a new test asserts the hook is a no-op when config is absent or has no `pattern_generalization_check` key (default-off), and fires only when the key is explicitly `true` — `tests/test_pattern_generalization_hook.py`
  - [ ] MECHANICAL: `goc/templates/hooks/pattern_generalization_check.py` detection inverted (enable only on explicit `true`; absent/anything-else → no-op), docstring rewritten opt-out → opt-in
  - [ ] MECHANICAL: `goc/templates/game_of_cards/config.yaml` ships `pattern_generalization_check: false` with a "set true to enable" comment
  - [ ] MECHANICAL: OpenClaw TS port (`openclaw-plugin/index.ts`) inverted at BOTH default-on checks (`isOptedOut` regex ~L472 and the `ctx.config.pattern_generalization_check === false` guard ~L652)
  - [ ] MECHANICAL: `goc/templates/skills/claude-kickoff/SKILL.md:168` hook-catalogue row reworded opt-out → opt-in
  - [ ] PROCESS: asset mirrors synced (`python scripts/sync_plugin_assets.py`) and OpenClaw re-ported if needed (`python3 scripts/port_skills_to_openclaw.py`); parity checks green
  - [ ] PROCESS: full suite green (`uv run python -m unittest discover -s tests`) and `uv run goc validate` clean
worker: {who: Rodja Trappe, where: main}
---

# make-pattern-generalization-stop-hook-opt-in

Flip the pattern-generalization Stop hook from **default-on (opt-out)**
to **default-off (opt-in)**. Today the hook fires on every code-mutating
turn unless a repo writes `hooks.pattern_generalization_check: false`;
after this card it stays silent unless a repo writes
`hooks.pattern_generalization_check: true`.

## Decision (user-selected)

On 2026-06-26 the user chose **"Flip to default-off (opt-in)"** from four
options (default-off; keep-on-but-narrow-trigger-to-commit-turns; both;
leave-as-is). Rationale: a **blocking** `Stop` hook is the most intrusive
hook class — it prevents the agent from yielding to the user — and it pays
an extra agent round-trip (tokens + latency) on *every* code-mutating
turn, while an actual generalization card is warranted only occasionally.
Paying a per-turn cost for an occasional benefit is a poor ratio for an
out-of-box default.

The accepted trade-off is **discoverability**: an opt-in flag most
consumers never flip ≈ the feature off for the median user. The "narrow
the trigger to commit turns" middle path (which would have kept it on at
lower cost) was explicitly not chosen.

This decision lowers the gate to `none` — the implementation direction is
fully specified, so `pull-card` may implement without a human checkpoint.

## Current state (what changes)

The hook is registered on the `Stop` event in `goc/install.py`:

```python
GOC_CLAUDE_HOOKS: dict[str, str] = {
    ...
    "Stop": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/pattern_generalization_check.py",
```

Default-on is encoded as **opt-out**: the hook runs unless the config
explicitly contains `false`. From
`goc/templates/hooks/pattern_generalization_check.py`:

```python
def _opted_out(project_dir: str) -> bool:
    config = Path(project_dir) / ".game-of-cards" / "config.yaml"
    if not config.exists():
        return False                      # absent config → NOT opted out → hook runs
    ...
        m = re.search(
            r"pattern_generalization_check\s*:\s*(false|true)", config.read_text()
        )
        return bool(m and m.group(1) == "false")   # only explicit false disables
```

`main()` runs the reminder whenever `not _opted_out(...)`. The shipped
template reinforces default-on (`goc/templates/game_of_cards/config.yaml`):

```yaml
hooks:
  # Set to false to disable the Stop hook that prompts the agent to file
  # generalization cards after code-mutating turns.
  pattern_generalization_check: true
```

## Blast radius — five surfaces

The polarity is reimplemented per host, so the flip is not a one-line edit:

1. **Claude Python hook** — `goc/templates/hooks/pattern_generalization_check.py`
   `_opted_out()` → invert to "enabled only on explicit `true`"; rewrite
   the module docstring's opt-out paragraph to opt-in. (Mirrored to
   `.claude/hooks/`, `claude-plugin/hooks/`, `codex-plugin/hooks/` by the
   asset-sync — edit the template, not the mirrors.)
2. **Template config** — `goc/templates/game_of_cards/config.yaml` →
   `pattern_generalization_check: false` + comment reworded to
   "set true to enable".
3. **OpenClaw TS port** — `openclaw-plugin/index.ts` has **two** default-on
   checks: `isOptedOut()` (regex `…:\s*false`, ~L472) and the `agent_end`
   guard `if (ctx?.config?.pattern_generalization_check === false) return;`
   (~L652). Both must invert to "run only when explicitly enabled". Note
   OpenClaw *also* gates this hook behind `allowConversationAccess` — that
   host-level opt-in is separate and stays as-is.
4. **Skill docs** — `goc/templates/skills/claude-kickoff/SKILL.md:168`
   hook-catalogue row says "Opt-out: set … false"; reword to opt-in.
5. **Tests + mirrors** — add a default-behavior test in
   `tests/test_pattern_generalization_hook.py` (current tests cover the
   mutation matcher and reminder branches, not the config default), then
   re-sync mirrors and re-port OpenClaw so `tests/test_plugin_mirror_parity.py`
   and the porter `--check` stay green.

## Why it matters

`Stop` has no non-blocking channel into the model (exit-0 stdout shows
only in the user's transcript), so the hook *must* block — exit 2 with the
reminder on stderr — to reach the agent at all. That makes it the most
aggressive interruption GoC ships, and it triggers on the single most
common turn type for a coding agent (any turn with an Edit/Write/broad-git
mutation). A fresh installer has not consented to that interruption model.
Flipping to opt-in keeps the capability for repos that want it while making
the default install quiet and cheap.

Existing repos that already wrote `pattern_generalization_check: true`
(this repo's own `.game-of-cards/config.yaml` does) keep the hook on after
the flip — the key is read literally — so the change is **non-breaking for
opted-in repos** and only changes behavior for new installs and key-absent
repos.

## Related cards

- `agent-flags-unfiled-pattern-generalization-cards-before-stop` (done) —
  the origin card that introduced the hook as default-on.
- `pattern-generalization-opt-out-regex-matches-anywhere-in-the-file`
  (open) and `pattern-generalization-opt-out-regex-misses-quoted-yaml-values`
  (open) — parsing-robustness defects in the **same** detection regex this
  card inverts. They are orthogonal to polarity (they apply equally to
  detecting `true` vs `false`) and are intentionally **not** folded in
  here. Whoever implements this should write the inverted check no less
  robustly than today's and leave a clean surface for those two; whoever
  implements those should fix both the Python hook and the OpenClaw regex.

## Fix (proposal — do not apply until pulled)

Minimal inversion, keeping the existing regex approach for parity with the
two open hardening cards:

```python
def _enabled(project_dir: str) -> bool:
    """Opt-in: hook runs only when config explicitly sets the key true."""
    config = Path(project_dir) / ".game-of-cards" / "config.yaml"
    if not config.exists():
        return False
    try:
        m = re.search(
            r"pattern_generalization_check\s*:\s*(false|true)", config.read_text()
        )
        return bool(m and m.group(1) == "true")
    except OSError:
        return False
```

and in `main()`: `if _enabled(project_dir) and _had_code_mutation(...)`.
Mirror the same inversion in `openclaw-plugin/index.ts` (run only when the
parsed/text config explicitly enables).
