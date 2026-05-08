---
name: standup
description: "Daily-style deck read — list active and blocked cards with blocker reasons, show closures from log.md within the last 24h, surface cards waiting on a human decision gate. Read-only, never mutates state. AUTO-INVOKE when user says \"what's up\", \"where do we stand\", \"what's blocked\", \"daily check\", \"standup\", \"morning check\", or \"what happened since yesterday\"."
---

## Preflight

If any `!` block below shows `goc: command not found`, `Permission for this action has been denied`, or `no such file or directory: .game-of-cards/deck/`, **stop and invoke `Skill(kickoff)` first**. Kickoff detects which setup step is missing (CLI not installed, Bash allowance not granted, project state not scaffolded) and walks the user through it. Re-invoke this skill only after kickoff completes.

## Context

!`goc --status active -v`

!`goc --status blocked -v`

!`goc --status open --json | head -60`

# Standup

Scrum's **Daily Scrum** (Schwaber & Sutherland) condensed to three
questions: what's running, what's stuck, what's new? This skill collapses
`scan-deck` + `git log` + manual `log.md` reading into one read.

**Read-only** — this skill never mutates card state. It is safe to invoke
at any time, as often as needed.

## Section 1 — In flight

For each `active` card (shown above): report title, summary, and who
claimed it (`worker` field). If the card has been active longer than 48h
without a `log.md` update, flag it as potentially stalled.

## Section 2 — Blocked

For each `blocked` card (shown above): report title and the blocker
reason from the body's `## Blocked` section (or the most recent
`log.md` entry if no section exists). One line per card.

## Section 3 — Closed since yesterday

Show closures from `log.md` files within the last 24 hours:

```bash
# Find log.md files modified in the last 24h, grep for closure entries
find .game-of-cards/deck -name "log.md" -newer .game-of-cards/deck -mmin -1440 2>/dev/null | \
  while read f; do
    title=$(basename "$(dirname "$f")")
    grep -E "^(closed|done|disproved|superseded)" "$f" | tail -1 | \
      sed "s/^/$title: /"
  done
```

If none: "Nothing closed in the last 24h."

## Section 4 — Waiting on you

Surface all cards with `human_gate: decision` or `human_gate: session`,
oldest first. These are parked cards where the agent hit the Andon cord
and a human must lower the gate to unblock autonomous work.

```bash
goc --json --status open 2>/dev/null | \
  python3 -c "
import json, sys
cards = json.load(sys.stdin)
waiting = [c for c in cards if c.get('human_gate') in ('decision', 'session')]
waiting.sort(key=lambda c: c.get('created', ''))
for c in waiting:
    print(f\"{c['title']} [{c['human_gate']}]: {c.get('summary', '(no summary)')[:80]}\")
" 2>/dev/null || true
```

For each: show title, gate type, and the `## Decision required` section
header if present. The human resolves these via `Skill(decide-card)`.

## Section 5 — Next up

Show the top 3 open `human_gate: none` cards by value score (the cards
`Skill(pull-card)` would pick next), as a forward look.

```bash
goc 2>/dev/null | head -5 || true
```

## Output format

```
## In flight
- <title> (claimed by <worker>, <N>h): <one-line summary>

## Blocked
- <title>: <blocker reason>

## Closed since yesterday
- <title>: closed — <one-line what-changed>

## Waiting on you
- <title> [decision]: <decision question, ≤80 chars>

## Next up
- <title> (value: <N>): <one-line summary>
```

Sections with no entries are omitted. Total output ≤ 40 lines.

## Cross-references

- `Skill(decide-card)` — lower a decision/session gate so agents can resume.
- `Skill(scan-deck)` — deeper browse of the deck (filtered queues, kanban board).
- `Skill(pull-card)` — claim and work the top open card.
- `Skill(retrospective)` — backwards analysis of recently closed cards.
