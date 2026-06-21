---
title: add-set-cadence-tooling-to-retune-autonomous-workflows
status: done
stage: null
contribution: medium
created: "2026-06-21T05:08:07Z"
closed_at: "2026-06-21T05:23:55Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra, story]
definition_of_done: |
  - [x] MECHANICAL: `scripts/set_cadence.py` exists, stdlib-only, and rewrites both the `- cron:` line and the adjacent `# cadence:` comment in `pull-card.yml` / `audit-deck.yml` / `refine-deck.yml` from interval flags (`--pull` / `--audit` / `--refine`); `--show` prints the current cadence; a second identical run is a no-op (idempotent).
  - [x] TDD: `tests/test_set_cadence.py` covers the interval→cron mapping (including divisor-of-24 rejection and `1d`/`24h` → daily), idempotent rewrite, and `--show`; `uv run python -m unittest tests.test_set_cadence` is green.
  - [x] MECHANICAL: `.github/workflows/refine-deck.yml` exists (modeled on `audit-deck.yml`), invokes `Skill(refine-deck)` under `bypassPermissions` / `--model opus`, with its cron carried by the managed `# cadence:` marker.
  - [x] MECHANICAL: applied cadence is pull-card `0 * * * *`, audit-deck `15 */3 * * *`, refine-deck `45 */3 * * *`; each file's `# cadence:` comment matches its cron and the stale frequency prose ("once a week" / "once a day" / "daily pull-card") is removed.
  - [x] MECHANICAL: `.claude/skills/tune-cadence/SKILL.md` exists (repo-local Claude Code skill) and is listed in `preserve_files` for the `.claude/skills` pair in `scripts/sync_plugin_assets.py`; `uv run python scripts/sync_plugin_assets.py --check` is clean.
  - [x] PROCESS: the closed sibling `run-pull-card-daily-and-audit-deck-weekly` is amended (a `log.md` forward pointer plus a `> Later` note atop its README) recording that this card reverses its cadence; `uv run goc validate` passes and the regression suite is green except the pre-existing `test_git_auto_commit_rebase_guard` interactive-rebase test the sandbox cannot set up (it shells out to `git rebase -i`; passes in CI).
worker: {who: Rodja Trappe, where: main}
---

# add-set-cadence-tooling-to-retune-autonomous-workflows

Make the autonomous GitHub Actions cadence cheap to retune, and apply a
faster first setting. The intervals change every few days as spare-token
headroom rises and falls, so hand-editing three cron strings each time
is the wrong primitive — ship a setter script and a repo-local skill
that wrap it, then drive the current values through them.

## Why now

We currently have ample spare-token headroom, so the deliberate
slowdown recorded in
[run-pull-card-daily-and-audit-deck-weekly](../run-pull-card-daily-and-audit-deck-weekly/)
(and the iteration cap in
[cap-daily-autonomous-pull-queue-at-four-cards-to-cut-token-spend](../cap-daily-autonomous-pull-queue-at-four-cards-to-cut-token-spend/))
is worth reversing for now. This card **reverses the cadence** that
sibling set — deliberately, with eyes open on the cost. The
`MAX_ITERATIONS=4` cap is left untouched (out of scope); only the cron
cadence moves.

## Applied cadence (the first setting)

| Workflow | Before | After | Cron |
|---|---|---|---|
| `pull-card.yml` | `0 3 * * *` (daily) | every hour | `0 * * * *` |
| `audit-deck.yml` | `0 2 * * 1` (weekly) | every 3 hours | `15 */3 * * *` |
| `refine-deck.yml` | *(did not exist)* | every 3 hours | `45 */3 * * *` |

`refine-deck.yml` is **new** — `refine-deck` had a skill but no
scheduled workflow. It is modeled on `audit-deck.yml`: one
`Skill(refine-deck)` hygiene pass per run under `bypassPermissions` /
`--model opus`.

### Minute offsets are deliberate

GitHub Actions runs scheduled workflows from the default branch with no
cross-workflow ordering. Three deck-mutating agents launching at `:00`
would race on `main` every three hours. Staggering to `:00` / `:15` /
`:45` keeps each launch on its own minute; the repo's
"Parallel-Agent Commit Safety" rules in AGENTS.md remain the real guard
for any residual overlap (GitHub's scheduler is imprecise). The hourly
pull-card at the top of each hour drains whatever audit/refine filed in
the previous one.

## The tooling

GitHub Actions `cron:` must be a **literal** string in the workflow
file — `schedule:` cannot read a config value. So "configurable
cadence" is a *rewriter*, not runtime config:

- **`scripts/set_cadence.py`** (stdlib-only) — `--show` queries the
  current cadence; `--pull` / `--audit` / `--refine` take interval
  specs (`1h`, `3h`, `1d`, …) and rewrite the `- cron:` line plus the
  adjacent managed `# cadence:` comment in each workflow. Per-workflow
  minute offsets are baked in (pull `:00`, audit `:15`, refine `:45`).
  Hour intervals must divide 24 (1,2,3,4,6,8,12) or be `24h`/`1d`;
  others are rejected with a clear message (cron can't express e.g.
  "every 5 days" cleanly).
- **`.claude/skills/tune-cadence/SKILL.md`** — a **repo-local Claude
  Code skill** (development-only; *not* a packaged goc skill — the
  script targets this repo's own workflow files, which `goc install`
  does not ship). It wraps the script for query + change and reminds
  the operator that cron changes only take effect once committed and
  pushed to the default branch. It is kept out of the
  template→`.claude/skills` sync's delete sweep via `preserve_files`.

## Out of scope

- `MAX_ITERATIONS` / the self-trigger drain logic — unchanged.
- Model selection (`--model opus`) and `--max-turns` — unchanged.
- A *general* goc feature to manage any consumer's autonomous cadence —
  this tooling is repo-local by design; generalizing it is a separate
  card if ever wanted.
- `claude.yml` / `claude-code-review.yml` / `ci.yml` / `release.yml` —
  event-driven, no cron, untouched.
