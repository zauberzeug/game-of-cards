# Log

## 2026-10-14T13:07:05Z — Filed from the failed v0.0.28 release (claude-code, host)

- Evidence: runs 38411041965 (Path A, CI subscription seven-day limit) and 38453406294 (Path B, deterministic). Job log of 115490011281 read: the `Skill(audit-deck)` tool result is the permission denial alone; the agent's final result names both gaps (unreachable preflight, kickoff without `Bash(goc:*)` / `permissions.allow`).
- Repo facts checked on `v0.0.28`: audit-deck's Preflight is present in the body; kickoff contains neither string; claude-kickoff contains both; `release.yml` unchanged since v0.0.27; preamble changed in f20a8920.
- Open: fix shape (decision gate) and the countercheck that attributes the abort.

## 2026-10-22T05:39:15Z: decision recorded

Fix shape (a)+(b)+(c): every goc-preamble skill pre-approves its own render-time blocks with one exact Bash(<block>) allowed-tools entry each; the Preflight and kickoff route a denied goc call to the host complement claude-kickoff; goc names a missing deck; the smoke allows the namespaced plugin skills — Countercheck on Claude Code 2.1.303: any denied render-time block aborts the whole skill load, v0.0.27's plain goc block included, so this is a Claude Code behavior change rather than f20a8920; the documented Bash(goc:*) grant does not cover f20a8920's compound block while it covers v0.0.27's, so main as-is would regress every granted user; exact allowed-tools entries load the body. Gate decision → none.
