# Log

## 2026-10-14T13:07:05Z — Filed from the failed v0.0.28 release (claude-code, host)

- Evidence: runs 38411041965 (Path A, CI subscription seven-day limit) and 38453406294 (Path B, deterministic). Job log of 115490011281 read: the `Skill(audit-deck)` tool result is the permission denial alone; the agent's final result names both gaps (unreachable preflight, kickoff without `Bash(goc:*)` / `permissions.allow`).
- Repo facts checked on `v0.0.28`: audit-deck's Preflight is present in the body; kickoff contains neither string; claude-kickoff contains both; `release.yml` unchanged since v0.0.27; preamble changed in f20a8920.
- Open: fix shape (decision gate) and the countercheck that attributes the abort.

## 2026-10-22T05:39:15Z: decision recorded

Fix shape (a)+(b)+(c): every goc-preamble skill pre-approves its own render-time blocks with one exact Bash(<block>) allowed-tools entry each; the Preflight and kickoff route a denied goc call to the host complement claude-kickoff; goc names a missing deck; the smoke allows the namespaced plugin skills — Countercheck on Claude Code 2.1.303: any denied render-time block aborts the whole skill load, v0.0.27's plain goc block included, so this is a Claude Code behavior change rather than f20a8920; the documented Bash(goc:*) grant does not cover f20a8920's compound block while it covers v0.0.27's, so main as-is would regress every granted user; exact allowed-tools entries load the body. Gate decision → none.

## 2026-10-22T05:41:25Z — Countercheck measured, fix (a)+(b)+(c) implemented, verified locally

Setup for every run: `claude -p` 2.1.303, `--model sonnet`, `--permission-mode dontAsk`,
`--setting-sources project,local --strict-mcp-config --no-session-persistence` (isolation checked in
each init event: only the `--plugin-dir` plugin plus builtins, no MCP servers), a fresh `git init`
directory per run, the Path B prompt from `release.yml`.

Countercheck (original Path B allowlist `Read,Write,Bash(cat:*),Bash(ls:*),Skill(kickoff),Skill(audit-deck)`):

- E0, main: `Skill(audit-deck)` → `Shell command permission check failed for pattern "!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b; else goc; fi 2>&1 || true`": Permission to use Bash has been denied because Claude Code is running in don't ask mode.`
- E1, v0.0.27 skills: identical abort on `"!`goc`"`. Kickoff (10.3k chars) carries neither `Bash(goc:*)` nor `permissions.allow` in either version.
- E4/E6, main + the documented grant `Bash(goc:*)` (CLI flag, resp. `--settings` file): same abort as E0. E5, v0.0.27 + that grant: loads (9,356-char body).
- E2 (skill frontmatter `allowed-tools`): prefix rules `Bash(goc:*)` / `Bash(sh .claude/skills/_goc-bootstrap.sh:*)` do not match the compound block; one exact `Bash(<block>)` per block loads the body. A skill that declares `allowed-tools` must be allowed by its namespaced name (`Skill(game-of-cards:audit-deck)`); `Skill(audit-deck)` then fails with "Permission to use Skill has been denied".
- E3: a kickoff hint in the skill description reaches the agent but does not make it route (4 runs).
- Probe plugin, one exact rule per block: parentheses inside quotes load; `x=$(echo …)` (and the old standup behind-check) is denied despite the exact rule; the old standup `python3 -c` filter is denied; `${GOC_WORKER:+ …}` and `|| echo "[refine-deck] …"` load.
- E7: main's `goc`, `goc --status active -v`, `goc --done` in a deckless repo printed only `No cards match (status: …).`, rc 0 — no Preflight trigger.

Implementation (branch `worktree-agent-a5b14c91dd90c4511`): 974a1400 (engine: missing-deck notice on stderr carrying `no such file or directory: .game-of-cards/deck/`; `goc new` shares the wording), 6291964e (skills: exact `allowed-tools` per block in the six goc-preamble skills, standup blocks rebuilt on `git status -sb` and `goc --waiting`, Preflight and kickoff route a denied `goc` call to the host complement, parity/size/lockstep guards, Codex and OpenClaw drop `allowed-tools`), 55dad8f7 (release smoke: namespaced skill rules, Path B checks the kickoff → claude-kickoff hand-off; local `smoke_release.sh` aligned on the same points).

Verification with this branch's `claude-plugin` (cached marketplace plugin stripped from PATH, a goc shim for the branch engine on PATH as CI pre-installs goc):

- Path A: audit-deck → Preflight → kickoff → `goc install` → deck created, `A:passed`.
- Path B: audit-deck loads (10,494 chars) and its block shows `goc: no Game of Cards deck found from … upward (no such file or directory: .game-of-cards/deck/). Run `goc install` at the intended project root first (agents: invoke Skill(kickoff)).`; kickoff → claude-kickoff; `B:passed`. Read-only commands (`which`, `ls`) run in dontAsk, so kickoff's sweep itself is not denied; the denial lands on `goc` calls, and the Path B prompt now says so.
- Granted-user run (E4 repeated, `Bash(goc:*)` + `Skill(game-of-cards:audit-deck)` only): the body loads (10,498 chars).
- `uv run python -m unittest discover -s tests`: 1349 passed. `goc validate`, `sync_plugin_assets.py --check`, `port_skills_to_openclaw.py --check` and pre-commit over the 65 changed files: green.

Remaining DoD: the CI dry-run release (TDD) and the publish (MECHANICAL). Untested: interactive default mode (the approval prompt a user sees for a skill that declares `allowed-tools`).
