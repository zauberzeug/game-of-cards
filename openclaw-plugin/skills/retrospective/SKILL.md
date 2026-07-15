---
name: retrospective
description: Backwards analysis of the last N closed cards — recurring failure modes, generalization candidates, rough velocity feel. Read-only; never files cards. AUTO-INVOKE on "what have we learned", "retro", "any patterns lately", "what keeps going wrong".
---

## When to invoke

Invoke when the user says "what have we learned", "review recent work", "any patterns lately", "look back", "retrospective", "retro", "what's our velocity", or "what keeps going wrong". May propose the `create-card` skill invocations for generalization candidates but never files them.

## Context

Before running the body of this skill, the agent should see current deck state. Run these via the `goc` tool (top-level filters like `--status` / `--tag` / `--worker` map to the tool's `flags` parameter; the subcommand maps to `verb`). For bare-queue listings with no subcommand, shell out via the `exec` tool:

- `goc --status done --json 2>&1 | head -100`

# Retrospective

Scrum's **Sprint Retrospective** (Schwaber & Sutherland) applied to the
full card history. This skill looks *backwards* at completed work —
something no other skill does. the `audit-deck` skill hunts NEW defects
in the codebase; this skill reads the last N `log.md` closure entries,
clusters by tag, and surfaces patterns: which failure modes recur,
which closures mention the same root cause, which clusters are candidates
for a generalization card.

**Read-only** — this skill inspects history and proposes actions. It
never files cards, flips status, or mutates the deck. Any generalization
card it identifies must be filed via a subsequent the `create-card` skill.

N = the user's argument (default 10 if not provided).

## Step 1 — Gather recent closures

```bash
# Read the last N done cards sorted by closed_at
goc --status done --json 2>/dev/null | \
  python3 -c "
import json, sys
cards = json.load(sys.stdin)
closed = [c for c in cards if c.get('closed_at')]
closed.sort(key=lambda c: c.get('closed_at', ''), reverse=True)
n = int('the user's argument'.strip() or '10')
for c in closed[:n]:
    print(json.dumps({'title': c['title'], 'closed_at': c['closed_at'],
                      'tags': c.get('tags', []), 'contribution': c.get('contribution'),
                      'summary': (c.get('summary') or '')[:80]}))
" 2>/dev/null || true
```

For each surfaced card, also read its `log.md` closure entry:

```bash
# For each title from above, show its log.md
# (run per-card; replace <title> with actual value)
cat ".game-of-cards/deck/<title>/log.md" 2>/dev/null | tail -20
```

## Step 2 — Cluster by tag

Group the N cards by their tags. For each cluster with ≥2 cards,
report:

```
[<tag>] N cards closed
  - <title> (<closed_at>): <one-line summary>
  ...
```

Tags with only 1 card get a single `[<tag>] 1 card` line, no detail.

## Step 3 — Surface failure patterns

Read the closure entries in `log.md` for each card. Look for:

- Cards closed with `disproved` or `superseded` — what was wrong?
- Cards whose `log.md` mentions rework, revert, or "fixed incidentally".
- Cards that carried a `waiting_on` overlay (check `log.md` for the wait being set/cleared) before closing — a long-running wait often signals an under-explored dependency or coordination gap.
- Cards whose DoD had many unchecked items at closure (if the log notes this).

For each pattern that appears in ≥2 cards, report it:

```
Pattern: <description>
  Seen in: <title-1>, <title-2>, ...
  Root cause hypothesis: <one line>
```

## Step 4 — Generalization candidates

A generalization card is warranted when:

- The same root cause appears in ≥3 closed cards (a recurring defect
  that was patched each time but never fixed architecturally).
- A cluster of ≥4 cards under the same tag all touched the same module
  or abstraction (signals a missing abstraction or over-busy module).
- Two or more cards were closed with "fixed incidentally" (signals the
  fix belonged in a shared utility).

For each identified candidate, output a **proposal only**:

```
Generalization candidate: <proposed-title>
  Evidence: <title-1>, <title-2>, <title-3>
  Pattern: <one-line description of the recurrence>
  → propose the `create-card` skill "<proposed-title>" to capture the meta-fix
```

Do NOT call the `create-card` skill. The human decides which proposals are
worth pursuing.

## Step 5 — Velocity feel

Count cards closed in the last 7 days, 14 days, and 30 days:

```bash
goc --status done --json 2>/dev/null | \
  python3 -c "
import json, sys
from datetime import date, timedelta
cards = json.load(sys.stdin)
today = date.today()
counts = {7: 0, 14: 0, 30: 0}
for c in cards:
    cd = c.get('closed_at', '')[:10]
    if not cd:
        continue
    delta = (today - date.fromisoformat(cd)).days
    for window in counts:
        if delta <= window:
            counts[window] += 1
print(f'7d: {counts[7]}  14d: {counts[14]}  30d: {counts[30]}')
" 2>/dev/null || true
```

Report as:

```
Velocity: <N> cards/7d · <N> cards/14d · <N> cards/30d
```

No benchmark is implied — this is a feel indicator, not a sprint
commitment. Trend matters more than absolute number.

## Output format

```
## Recent closures (last N)
[tag clusters]

## Failure patterns
[patterns or "None detected"]

## Generalization candidates
[proposals or "None identified"]

## Velocity
Velocity: N cards/7d · N cards/14d · N cards/30d
```

Total output ≤ 60 lines. Full log analysis stays in the skill's
working context; only the surfaced patterns and proposals go to chat.

## Cross-references

- the `create-card` skill — file a generalization card from a candidate proposal.
- the `audit-deck` skill — hunt for NEW defects in the codebase (forward-looking).
- the `standup` skill — daily read of in-flight and impeded work.
- the `scan-deck` skill — full queue browse including closed cards.
