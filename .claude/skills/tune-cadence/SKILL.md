---
name: tune-cadence
description: Query or change how often this repo's autonomous GitHub Actions run (pull-card, audit-deck, refine-deck). AUTO-INVOKE when the user asks what the current cadence is, how often pull-card/audit/refine run, to speed up or slow down the deck, to run pull-card every N hours, to change the autonomous cadence, or to retune the workflows. Repo-local dev skill that wraps scripts/set_cadence.py; not a packaged goc skill.
---

# Tune the autonomous workflow cadence

This repo drives three autonomous agents from GitHub Actions:

- **pull-card** (`.github/workflows/pull-card.yml`) — drains the queue.
- **audit-deck** (`.github/workflows/audit-deck.yml`) — files one new card per run.
- **refine-deck** (`.github/workflows/refine-deck.yml`) — one deck-hygiene pass per run.

Their schedules are GitHub Actions `cron:` literals, which can't read a
config file. `scripts/set_cadence.py` rewrites those literals (and the
managed `# cadence:` comment beside each) from a small interval spec, so
this skill is just a thin wrapper around it.

## Query the current cadence

```bash
python3 scripts/set_cadence.py --show
```

Prints each workflow's cron plus its human-readable interval.

## Change the cadence

```bash
python3 scripts/set_cadence.py --pull 1h --audit 3h --refine 3h
```

- Pass only the workflows you want to change; omit the rest to leave them.
- Interval specs: `<N>h` where N divides 24 (1, 2, 3, 4, 6, 8, 12) or
  `24h`; `<N>d` for every-N-days; and `1w` for exact weekly. Note `Nd`
  (N≥2) becomes a day-of-month `*/N` cron step that realigns each month,
  so it's "roughly every N days" — the gap across a month boundary is
  shorter. `1w` is exact (day-of-week, every Monday); there is no clean
  cron for every-N-days or every-N-weeks.
- Minute offsets are fixed (pull `:13`, audit `:15`, refine `:45`) so the
  three deck-mutating agents never launch on the same minute and race on
  `main`.

## Make it take effect

Scheduled workflows run from the **default branch**, so a cadence change
does nothing until it is committed and pushed to `main`:

```bash
git add .github/workflows/pull-card.yml \
        .github/workflows/audit-deck.yml \
        .github/workflows/refine-deck.yml
git commit -m "ci: retune autonomous cadence"
git push
```

Follow AGENTS.md "Parallel-Agent Commit Safety" — stage explicit paths,
verify `git diff --cached`, commit with a pathspec.

## Cost note

Each run of any of these workflows is a full Opus agent under
`bypassPermissions`. Faster cadence means more token spend; dial it back
toward daily when spare-token headroom is tight. The cap on pull-card's
per-tick self-trigger chain is separate — it lives in `MAX_ITERATIONS`
inside `pull-card.yml`, not here.
