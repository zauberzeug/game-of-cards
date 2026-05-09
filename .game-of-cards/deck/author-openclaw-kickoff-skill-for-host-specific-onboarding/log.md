# Log

## 2026-05-09 — closed via "touches exist" branch

Investigation answered the DoD's first question: OpenClaw does have
host-specific kickoff finishing touches that are absent from the
generic `kickoff` skill. Verified against
<https://docs.openclaw.ai/cli/plugins.md> and
<https://docs.openclaw.ai/cli/skills.md>:

- **Plugin install / update cadence is host-specific.**
  `openclaw plugins install <slug>` / `openclaw plugins update <slug>`
  (and the skills-only `openclaw skills install` /
  `openclaw skills update --all`). Plus the `openclaw plugins inspect`
  and `openclaw plugins doctor` sanity-check verbs that surfaced the
  smoke blockers on the parent epic — worth pointing kickoff users at.
- **Permission grant: no equivalent.** OpenClaw's plugin sandbox
  exposes a registered tool once the plugin is enabled; there is no
  per-tool allowlist parallel to Claude Code's `Bash(goc:*)` grant.
  The non-instruction is itself worth stating so the user does not go
  hunting.
- **Private notes file: no equivalent.** OpenClaw has no documented
  analog of `CLAUDE.local.md`. Same — explicit non-instruction in
  the kickoff body avoids confusion.

Because touches were found, the alternative DoD branch ("close as
superseded if no touches exist") was not taken. The corresponding
checkbox is ticked because the alternative was considered and rejected
based on the documented findings; this log entry is the explanation
the DoD requires.

## Implementation

- New `goc/templates/skills/openclaw-kickoff/SKILL.md` — three stages
  (state-detection sweep, install/update cadence note, confirm what
  OpenClaw does NOT need, ready handoff). Mirrors the shape of
  `claude-kickoff` but trimmed to the host-specific content.
- `goc/install.py` — `skill_for_agent` now consults a new
  `PLUGIN_ONLY_AGENTS = ("openclaw",)` tuple in addition to
  `SUPPORTED_AGENTS`, so an `openclaw-`-prefixed skill is filtered out
  of every `--agents` install tree. Without this, `goc install --agents
  claude` would have erroneously written `.claude/skills/openclaw-kickoff/`.
- `scripts/sync_plugin_assets.py` — discovers `openclaw-*` skill
  directories at runtime and excludes them from the
  `templates/skills → claude-plugin/skills` mirror so the OpenClaw
  complement never ships in the Claude plugin.
- `goc/engine.py` — the same exclusion applied to the parity-walk used
  by `goc validate`'s plugin-mirror drift check. Without it, validate
  flagged `openclaw-kickoff (only in goc/templates/skills)`.
- `scripts/port_skills_to_openclaw.py` — no behavioural change needed
  (the port script's `HOST_PREFIXES = ("claude-", "codex-")` already
  excludes the right prefixes, and `openclaw-` is intentionally absent
  so openclaw-prefixed skills DO get ported). Added a comment making
  that intent explicit.
- Re-ran `python3 scripts/port_skills_to_openclaw.py` to seed
  `openclaw-plugin/skills/openclaw-kickoff/SKILL.md`.
- `python3 scripts/sync_plugin_assets.py --check` and
  `uv run goc validate` both clean.
