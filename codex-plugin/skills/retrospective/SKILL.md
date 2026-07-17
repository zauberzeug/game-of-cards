---
name: retrospective
description: "Backwards analysis of the last N closed cards — recurring failure modes, generalization candidates, rough velocity feel. Read-only; never files cards. AUTO-INVOKE on \"what have we learned\", \"retro\", \"any patterns lately\", \"what keeps going wrong\"."
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

Invoke when the user says "what have we learned", "review recent work", "any patterns lately", "look back", "retrospective", "retro", "what's our velocity", or "what keeps going wrong". May propose Skill(create-card) invocations for generalization candidates but never files them.

## Preflight

If any `!` block below shows `goc: command not found`, `Permission for this action has been denied`, or `no such file or directory: .game-of-cards/deck/`, **stop and invoke `Skill(kickoff)` first**. Kickoff detects which setup step is missing (CLI not installed, Bash allowance not granted, project state not scaffolded) and walks the user through it. Re-invoke this skill only after kickoff completes.

## Context

!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b --status done --json; else goc --status done --json; fi 2>&1 | head -100`

# Retrospective

Scrum's **Sprint Retrospective** (Schwaber & Sutherland) applied to the
full card history. This skill looks *backwards* at completed work —
something no other skill does. `Skill(audit-deck)` hunts NEW defects
in the codebase; this skill reads the last N `log.md` closure entries,
clusters by tag, and surfaces patterns: which failure modes recur,
which closures mention the same root cause, which clusters are candidates
for a generalization card.

**Read-only** — this skill inspects history and proposes actions. It
never files cards, flips status, or mutates the deck. Any generalization
card it identifies must be filed via a subsequent `Skill(create-card)`.

N = $ARGUMENTS (default 10 if not provided).

## Step 1 — Gather recent closures

```bash
# Read the last N done cards sorted by closed_at
goc --status done --json 2>/dev/null | \
  python3 -c "
import json, sys
cards = json.load(sys.stdin)
closed = [c for c in cards if c.get('closed_at')]
closed.sort(key=lambda c: c.get('closed_at', ''), reverse=True)
n = int('$ARGUMENTS'.strip() or '10')
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
  → propose Skill(create-card) "<proposed-title>" to capture the meta-fix
```

Do NOT call `Skill(create-card)`. The human decides which proposals are
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

- `Skill(create-card)` — file a generalization card from a candidate proposal.
- `Skill(audit-deck)` — hunt for NEW defects in the codebase (forward-looking).
- `Skill(standup)` — daily read of in-flight and impeded work.
- `Skill(scan-deck)` — full queue browse including closed cards.
