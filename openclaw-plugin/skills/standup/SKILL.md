---
name: standup
description: Daily-style deck read — list active and impeded cards (carrying a `waiting_on` overlay), show closures from log.md within the last 24h, surface cards waiting on a human decision gate. Read-only, never mutates state. AUTO-INVOKE when user says "what's up", "where do we stand", "what's blocked", "what's stuck", "daily check", "standup", "morning check", or "what happened since yesterday".
---

## Context

Before running the body of this skill, the agent should see current deck state. Run these via the `goc` tool (top-level filters like `--status` / `--tag` / `--worker` map to the tool's `flags` parameter; the subcommand maps to `verb`). For bare-queue listings with no subcommand, shell out via the `exec` tool:

- `git fetch --quiet 2>/dev/null; behind=$(git rev-list --count HEAD..@{u} 2>/dev/null || echo 0); [ "${behind:-0}" -gt 0 ] && echo "⚠️ Local is $behind commit(s) behind upstream — pull before trusting the deck view below; closures landed on the remote will not appear." || echo "✓ Local is current with upstream (or no upstream configured)."`
- `goc --status active -v`
- `goc --json --status open 2>/dev/null | python3 -c "import json,sys; cards=json.load(sys.stdin); impeded=[c for c in cards if c.get('waiting_on')]; print('\n'.join(f\"{c['title']} [waiting_on: {c['waiting_on']}{(' until ' + c['waiting_until']) if c.get('waiting_until') else ''}]: {(c.get('summary') or '(no summary)')[:80]}\" for c in impeded) or 'No impeded cards.')" 2>/dev/null || true`
- `goc --status open --json | head -60`

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
goc --json --status all 2>/dev/null | python3 -c "
import json, sys, datetime
cards = json.load(sys.stdin)
now = datetime.datetime.now(datetime.timezone.utc)
def parse(s):
    if not s: return None
    try: d = datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
    except Exception:
        try: d = datetime.datetime.strptime(s[:10], '%Y-%m-%d')
        except Exception: return None
    return d.replace(tzinfo=datetime.timezone.utc) if d.tzinfo is None else d
recent = [c for c in cards if (d := parse(c.get('closed_at'))) and 0 <= (now - d).total_seconds() <= 86400]
recent.sort(key=lambda c: c['closed_at'])
for c in recent:
    print(f\"{c['title']}: {c['status']} — {(c.get('summary') or '')[:70]}\")
print(f\"({len(recent)} closed in last 24h)\" if recent else 'Nothing closed in the last 24h.')
" 2>/dev/null || true
```

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
header if present. The human resolves these via the `decide-card` skill.

## Section 5 — Next up

Show the top 3 open `human_gate: none` cards by value score (the cards
the `pull-card` skill would pick next), as a forward look.

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

- the `decide-card` skill — lower a decision/session gate so agents can resume.
- the `scan-deck` skill — deeper browse of the deck (filtered queues, kanban board).
- the `pull-card` skill — claim and work the top open card.
- the `retrospective` skill — backwards analysis of recently closed cards.
