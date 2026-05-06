---
title: state-flip-verbs-skip-log-md-entry
summary: "`goc decide` and `goc attest` write structured dated entries to a card's `log.md`, but `goc status` and `goc done` only mutate frontmatter — no log entry is written. The `Skill(advance-card)` doc table at `goc/templates/skills/advance-card/SKILL.md:47` explicitly says `* → superseded` should log replacement rationale in the old card's `log.md`, but the CLI never does this. Unverified: the design may intentionally leave prose-shaped log entries to skills/humans, since the CLI has no structured payload to record on a bare status flip. Needs a design call before promoting to a fix."
status: active
stage: null
contribution: medium
created: 2026-05-06
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, unverified, api-contract]
definition_of_done: |
  - [ ] (replace with real criteria)
---

# state-flip-verbs-skip-log-md-entry

## Hypothesis

`goc decide` (engine.py:1943-1951) and `goc attest` (engine.py:1649-1653) both append structured dated blocks to `log.md` from the CLI itself. `goc status` (engine.py:1690-1699) and `goc done` (engine.py:1354-1359) do not — they only rewrite frontmatter on README.md.

Verbatim:

```python
# decide (engine.py:1943-1951)
log_path = card_dir / "log.md"
existing = log_path.read_text() if log_path.exists() else ""
sep = "\n\n" if existing.strip() else ""
log_path.write_text(
    existing.rstrip("\n")
    + sep
    + f"## {today}: decision recorded\n\n"
    + f"{decision} — {reasoning}. Gate {prior_gate} → none.\n"
)
```

```python
# done (engine.py:1354-1359)
text = mutate_frontmatter_field(text, "status", "done")
text = mutate_frontmatter_field(text, "closed_at", today)
(card_dir / "README.md").write_text(text)
click.echo(f"{title}: {prior} → done")
# (no log.md mutation)
```

```python
# status (engine.py:1690-1699)
text = mutate_frontmatter_field(text, "status", new_status)
(card_dir / "README.md").write_text(text)
click.echo(f"{title}: {prior} → {new_status}")
# (no log.md mutation)
```

A documented contract appears to be violated:

```markdown
# goc/templates/skills/advance-card/SKILL.md:47
| `* → superseded` | `goc status <title> superseded` | log replacement rationale in old card's `log.md` |
```

The skill table tells the user the CLI logs the rationale; the CLI does not.

## Why deferred (unverified)

The design might be intentional: the CLI logs only when it has *structured payload* (decide carries a what+why; attest carries a checkbox audit table; status/done only carry old→new which is already in README frontmatter and recoverable from `git log`). Under that interpretation the skill prose is the prescriptive surface — the human/skill writes the rationale before/after invoking `goc status superseded`.

Promotion path: ask the maintainer which interpretation is canonical. If the doc is right, the CLI must append a minimal entry on every status flip. If the CLI is right, the doc table needs to drop the "log replacement rationale" promise (or move it to a `Skill(advance-card)` step the human runs).

## Falsification recipe (when this is reopened)

1. Read `Skill(advance-card)` end-to-end: does the recommended workflow already insert a manual log.md entry between status changes? If yes, the CLI's silence is not a defect — the doc table at line 47 is just describing the skill workflow.
2. Probe: `goc status x active; goc status x blocked; cat deck/x/log.md` — empirically empty. Confirms the CLI's behavior.
3. Decision: prescribe one. Either the CLI auto-logs `## YYYY-MM-DD: status <prior> → <new>` on every flip, or the skill table is rewritten to make the manual step explicit.

## Surfaced by

`extend-deck` round 2 hunt (general-purpose agent, candidate #2 of 3).
