---
name: standup
description: "Daily-style deck read — active and impeded cards, closures within the last 24h, cards parked on a human decision gate. Read-only, never mutates state. AUTO-INVOKE on \"where do we stand\", \"what's stuck\", \"standup\", \"daily check\", or \"what happened since yesterday\"."
---

## Codex GoC Command

When this skill says `goc ...`, resolve the executable before running the
command:

- In the `game-of-cards` source checkout, use `uv run goc ...`.
- If `goc` is already on `PATH`, use `goc ...`.
- If this skill is loaded from the Game of Cards Codex plugin, use the
  bundled helper at `<plugin-root>/skills/_goc-bootstrap.sh ...`; the plugin
  root is the parent directory that contains both `skills/` and `bin/`.
- If the plugin root is not obvious from the loaded skill path, locate the
  helper with:

```bash
GOC_BOOTSTRAP=$(find "$HOME/.codex/plugins/cache" -path '*/game-of-cards/*/skills/_goc-bootstrap.sh' -type f -perm -111 -exec ls -t {} + 2>/dev/null | head -n 1)
test -n "$GOC_BOOTSTRAP" || { echo "GoC Codex plugin bootstrap not found" >&2; exit 127; }
"$GOC_BOOTSTRAP" --help
```

Use that helper path in place of bare `goc` for the rest of the skill. Do not
edit deck files directly just because `goc` is not on `PATH`.


## When to invoke

Invoke when the user says "what's up", "where do we stand", "what's blocked", "what's stuck", "daily check", "standup", "morning check", or "what happened since yesterday".

## Preflight

If any `!` block below shows `goc: command not found`, `Permission for this action has been denied`, or `no such file or directory: .game-of-cards/deck/`, **stop and invoke `Skill(kickoff)` first**. Kickoff detects which setup step is missing (CLI not installed, Bash allowance not granted, project state not scaffolded) and walks the user through it. Re-invoke this skill only after kickoff completes.

If the first Context block warns that local is **behind upstream**, say so at the top of your report and treat every section below as possibly stale — closures and status changes pushed to the remote will not appear until the user pulls.

## Context

!`git fetch --quiet 2>/dev/null; behind=$(git rev-list --count HEAD..@{u} 2>/dev/null || echo 0); [ "${behind:-0}" -gt 0 ] && echo "⚠️ Local is $behind commit(s) behind upstream — pull before trusting the deck view below; closures landed on the remote will not appear." || echo "✓ Local is current with upstream (or no upstream configured)."`

!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b --status active -v; else goc --status active -v; fi 2>&1 || true`

!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b --json --status open; else goc --json --status open; fi 2>/dev/null | python3 -c "import json,sys; cards=json.load(sys.stdin); impeded=[c for c in cards if c.get('waiting_on')]; print('\n'.join(f\"{c['title']} [waiting_on: {c['waiting_on']}{(' until ' + c['waiting_until']) if c.get('waiting_until') else ''}]: {(c.get('summary') or '(no summary)')[:80]}\" for c in impeded) or 'No impeded cards.')" 2>/dev/null || true`

!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b --status open --json; else goc --status open --json; fi 2>&1 | head -60`

# Standup

Scrum's **Daily Scrum** (Schwaber & Sutherland) condensed to three
questions: what's running, what's stuck, what's new? This skill collapses
a remote-sync check, `scan-deck`, and the deck's structured closure
record (`closed_at`) into one read.

**Read-only** — this skill never mutates card state (the `git fetch` in
Context updates only remote-tracking refs, not your working tree or any
card). It is safe to invoke at any time, as often as needed.

## Section 1 — In flight

For each `active` card (shown above): report title, summary, and who
claimed it (`worker` field). If the card has been active longer than 48h
without a `log.md` update, flag it as potentially stalled.

## Section 2 — Impeded (waiting overlay)

For each card carrying a `waiting_on` overlay (shown above): report
title, the `waiting_on` reason, the `waiting_until` date if any, and
the body's `## Waiting` section (or the most recent `log.md` entry if
no section exists). One line per card. A card may appear here even
while `status: active` — the overlay is orthogonal to the progress
status.

## Section 3 — Closed since yesterday

List cards whose engine-maintained `closed_at` falls within the last 24
hours. Read the structured record — **not** file mtime. A `find … -newer
… -mmin` scan is git-blind: a pull/merge/clone writes the deck directory
and every `log.md` at one instant, giving them identical mtimes, so a
strict `-newer` test matches nothing and standup falsely reports
"Nothing closed" right after a sync lands the day's work. `closed_at` is
the timestamp the engine sets on close, so it is immune to that and
uniformly covers `done` / `disproved` / `superseded`.

```bash
goc --json --closed-since 24h --slim 2>/dev/null | python3 -c "
import json, sys
cards = sorted(json.load(sys.stdin), key=lambda c: c.get('closed_at') or '')
for c in cards:
    print(f\"{c['title']}: {c['status']}\")
print(f\"({len(cards)} closed in last 24h)\" if cards else 'Nothing closed in the last 24h.')
" 2>/dev/null || true
```

`--closed-since 24h` does the date-window filter inside the engine
(reading the structured `closed_at` record, not file mtime — a
pull/merge/clone writes every `log.md` at one instant and a
`-newer`-mtime scan falsely reports "Nothing closed"). `--slim` strips
body/large fields so the Context block ships kilobytes instead of the
multi-hundred-KB full-deck JSON. The title-by-status output is enough
for the standup format; expand the window or drop `--slim` if you need
summaries.

If none match, report "Nothing closed in the last 24h." When the count
is large (a batch sync), summarize by theme rather than listing every
line.

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
⚠️ Behind upstream by <N> — pull first; view may be stale.   (only if the sync check warned)

## In flight
- <title> (claimed by <worker>, <N>h): <one-line summary>

## Impeded
- <title> [waiting_on: <reason>{ until <date>}]: <one-line reason>

## Closed since yesterday
- <title>: <status> — <one-line what-changed>
  (or, for a large batch: "<N> closed — <theme>: a, b, c; <theme>: d, e")

## Waiting on you
- <title> [decision]: <decision question, ≤80 chars>

## Next up
- <title> (value: <N>): <one-line summary>
```

Sections with no entries are omitted. Total output ≤ 40 lines. The sync
warning, if present, always goes first — never bury a stale-data caveat.

## Cross-references

- `Skill(decide-card)` — lower a decision/session gate so agents can resume.
- `Skill(scan-deck)` — deeper browse of the deck (filtered queues, kanban board).
- `Skill(pull-card)` — claim and work the top open card.
- `Skill(retrospective)` — backwards analysis of recently closed cards.
