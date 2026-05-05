---
title: done-rerun-rewrites-closure-date
summary: "Running `goc done <title>` on a card that is already `status: done` rewrites `closed_at` to today's date. That destroys the original closure timestamp and makes repeated close attempts non-idempotent."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] `uv run python deck/done-rerun-rewrites-closure-date/reproduce.py` exits zero
  - [x] `goc done <title>` leaves `closed_at` unchanged when the card is already done
  - [x] The command reports a no-op or otherwise avoids a misleading `done -> done` transition
  - [x] A focused regression test covers re-running `done` on an already-done card
---

# done-rerun-rewrites-closure-date

## Location

- `goc/engine.py:1286`
- `goc/engine.py:1300`
- `goc/engine.py:1303`

## What's broken

`goc done` is not idempotent. It always sets `closed_at` to today's
date, even when the card is already `status: done`.

The implementation takes the prior status for display but does not guard
the already-done case:

```python
prior = t.status
today = date.today().isoformat()
text = (card_dir / "README.md").read_text()
text = mutate_frontmatter_field(text, "status", "done")
text = mutate_frontmatter_field(text, "closed_at", today)
(card_dir / "README.md").write_text(text)
click.echo(f"{title}: {prior} -> done")
```

For an already-closed card, that changes historical metadata from the
real close date to the date of the accidental rerun.

## Empirical evidence

Current output from `uv run python deck/done-rerun-rewrites-closure-date/reproduce.py`:

```text
exit=0
stdout=already-done-card: done → done
before=closed_at: 2026-01-02
after=closed_at: 2026-05-04
defect present: rerunning goc done rewrites closed_at
```

## Why it matters

`closed_at` drives done-history queries such as `goc --done --since
YYYY-MM-DD`. Rewriting it moves old work into new time windows and erases
the original closure date from the card frontmatter. Since `done` is the
final lifecycle transition, re-running it should be harmless or clearly
rejected, not a metadata mutation.

## Fix

In `done()`, handle `t.status == "done"` before rewriting frontmatter.
The safest behavior is a no-op that preserves `closed_at` and prints a
clear message such as `already done; closed_at unchanged`. Add regression
coverage with a card whose `closed_at` is intentionally older than today.
