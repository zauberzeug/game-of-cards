# Log

## 2026-10-14T13:07:05Z — Filed from the failed v0.0.28 release (claude-code, host)

- Evidence: runs 38411041965 (Path A, CI subscription seven-day limit) and 38453406294 (Path B, deterministic). Job log of 115490011281 read: the `Skill(audit-deck)` tool result is the permission denial alone; the agent's final result names both gaps (unreachable preflight, kickoff without `Bash(goc:*)` / `permissions.allow`).
- Repo facts checked on `v0.0.28`: audit-deck's Preflight is present in the body; kickoff contains neither string; claude-kickoff contains both; `release.yml` unchanged since v0.0.27; preamble changed in f20a8920.
- Open: fix shape (decision gate) and the countercheck that attributes the abort.
