---
title: status-command-reopens-terminal-cards
summary: "The generic `goc status` command can move terminal cards (`done`, `disproved`, `superseded`) back to open. That contradicts the schema lifecycle and, for done cards, leaves a reopened card with a stale `closed_at` date that still validates."
status: open
stage: null
contribution: high
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] `uv run python deck/status-command-reopens-terminal-cards/reproduce.py` exits zero
  - [ ] `goc status <title> open` rejects or otherwise refuses cards currently in terminal states
  - [ ] Reopened/non-done cards cannot retain `closed_at` values unnoticed by `goc validate`
  - [ ] Focused regression coverage proves terminal `done`, `disproved`, and `superseded` cards cannot be moved backward by `status`
---

# status-command-reopens-terminal-cards

## Location

- `goc/templates/skills/card-schema/SKILL.md:49`
- `goc/templates/skills/card-schema/SKILL.md:50`
- `goc/templates/skills/card-schema/SKILL.md:51`
- `goc/engine.py:467`
- `goc/engine.py:1572`
- `goc/engine.py:1575`
- `goc/engine.py:1588`

## What's broken

The schema reference marks `done`, `disproved`, and `superseded` as
terminal lifecycle states:

```markdown
| `done` | DoD checklist all ticked; `goc done <title>` enforces this | terminal |
| `disproved` | hypothesis investigated and ruled out; body documents the rebuttal | terminal |
| `superseded` | replaced by another card; replacement narrative in `log.md`; preserved for forensic continuity | terminal |
```

The `status` command only constrains the *target* status:

```python
MUTABLE_STATUS_VALUES = tuple(status for status in STATUS_VALUES if status != "done")
...
@click.argument("new_status", type=click.Choice(MUTABLE_STATUS_VALUES))
def status(title, new_status, commit, no_commit):
```

It never rejects terminal *source* states, so `goc status done-card open`
is accepted. For `done` cards, this also leaves `closed_at` populated on
a non-done card, and `goc validate` accepts that stale timestamp.

## Empirical evidence

Current output from `uv run python deck/status-command-reopens-terminal-cards/reproduce.py`:

```text
done-card: exit=0; stdout=done-card: done → open; status: open; closed_at: 2026-01-02
disproved-card: exit=0; stdout=disproved-card: disproved → open; status: open; closed_at: null
superseded-card: exit=0; stdout=superseded-card: superseded → open; status: open; closed_at: null
validate_exit=0
validate_stderr=
defect present: terminal cards reopened: done-card, disproved-card, superseded-card
```

## Why it matters

Terminal cards are forensic records. Moving them backward through the
generic status command breaks the lifecycle contract and can corrupt
time-based reports: a reopened card may still carry an old `closed_at`,
while a later `goc done` rerun can overwrite it. Both behaviors make the
deck less trustworthy as an audit trail.

## Fix

In `status()`, reject cards whose current status is terminal
(`done`, `disproved`, `superseded`) unless a future explicit escape hatch
is designed. Add validator coverage so any non-done card with a non-null
`closed_at` is rejected, or clear `closed_at` only through an explicit,
audited reopen workflow if such a workflow is ever introduced.
