## 2026-07-11 — Measured per-payload shipping; disproved

Per-host measurement (EMPIRICAL DoD item):

- `ls claude-plugin/skills/ | grep kickoff` → `kickoff`, `claude-kickoff` only.
- `ls codex-plugin/skills/ | grep kickoff` → `kickoff`, `codex-kickoff` only.
- `ls openclaw-plugin/skills/ | grep kickoff` → `kickoff`, `openclaw-kickoff` only.
- Vendored dogfood trees in this repo: `.claude/skills/` → `kickoff`,
  `claude-kickoff`; `.codex/skills/` → `kickoff`, `codex-kickoff`.
- Filter mechanisms: `skill_for_agent()` in `goc/install.py` (drives
  `_iter_skill_assets` / `_sync_skill_tree` for `goc install`/`upgrade`),
  the same predicate reused by `scripts/sync_plugin_assets.py` for the
  claude/codex plugin payloads, and the `HOST_PREFIXES = ("claude-",
  "codex-")` skip list in `scripts/port_skills_to_openclaw.py`.
- Description sizes (source `SKILL.md` frontmatter): kickoff 243 chars,
  claude-kickoff 225, codex-kickoff 273, openclaw-kickoff 278. Worst
  per-session total: 521 chars (~130 tokens), all under the 300-char cap.
- Live confirmation: the working agent's own session (Claude Code on this
  repo) listed only `kickoff` and `claude-kickoff` in its skill catalog.

Verdict: **disprove**. The four-descriptions-per-session premise is
false on every payload — filtering already bounds the cost at two.
Consolidation would save one ~250-char description per session against
install/upgrade removal handling, sync/porter/parity churn, and payload
relayout. README rewritten with hypothesis / verdict / source of error;
flipping to `disproved`.
