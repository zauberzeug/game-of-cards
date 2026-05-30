---
title: goc-decide-leaves-prior-decision-block-when-the-body-already-has-one
summary: "`replace_or_append_decision` only handles two body shapes — a pending `## Decision required` section (replaced in place) and no decision section at all (new block appended). It does not detect a previously-resolved `## Decision` block. When the body carries BOTH (a prior decision plus a re-raised `## Decision required`), `goc decide` substitutes the required section and silently keeps the stale resolved block — producing a README with two `## Decision` headings. Reachable via the documented re-raise-gate-and-re-decide workflow."
status: open
stage: null
contribution: medium
created: "2026-05-30T17:50:00Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `tests/test_engine_decide.py` (or equivalent) asserts that, given a body containing both a resolved `## Decision` block and a pending `## Decision required` section, `goc decide` produces a body with exactly one `## Decision` heading (the new one).
  - [ ] TDD: reproduce.py exits zero — Decision-heading count is 1 after the fix.
  - [ ] MECHANICAL: `replace_or_append_decision` (or its caller in `_cmd_decide`) detects a prior `## Decision` block and resolves it per the recorded Decision.
  - [ ] PROCESS: if Option B is chosen, `goc/templates/skills/decide-card/SKILL.md` "What this skill does to the card" subsection updates to document the prior-decision archival path. If Option A or C is chosen, the skill body and engine error text reflect the new contract.
  - [ ] PROCESS: cross-link the closed sibling [goc-decide-loses-deliberation-history-by-not-archiving-replaced-section](../goc-decide-loses-deliberation-history-by-not-archiving-replaced-section/) in log.md — the chosen fix should compose cleanly with that card's archival contract.
worker: null
---

# goc-decide-leaves-prior-decision-block-when-the-body-already-has-one

## Location

- `goc/engine.py:378-393` — `replace_or_append_decision`. The two-branch logic (`if DECISION_REQUIRED_RE.search(body): sub` else `append`) never inspects the body for a pre-existing `## Decision` heading.
- `goc/engine.py:4786-4846` — `_cmd_decide`. Calls `extract_decision_required_section` + `replace_or_append_decision` without touching any prior `## Decision` block already in the README.

## What's broken

`replace_or_append_decision` handles two body shapes:

```python
# goc/engine.py:378-393
def replace_or_append_decision(body: str, decision: str, reasoning: str, today: str) -> str:
    ...
    block = f"## Decision\n\n*Resolved {today}:* {decision}\n\n*Reasoning:* {reasoning}\n\n"
    if DECISION_REQUIRED_RE.search(body):
        return DECISION_REQUIRED_RE.sub(lambda _: block, body, count=1)
    return body.rstrip("\n") + "\n\n" + block
```

It does NOT detect or rewrite a previously-resolved `## Decision` heading. When the body carries both — a prior `## Decision` (from an earlier `goc decide` call) AND a fresh `## Decision required` (added when the gate was re-raised) — the substitution rewrites the required section but leaves the old resolved block intact. The result is a README with two `## Decision` headings:

```
## Decision

*Resolved 2026-05-30:* new-answer

*Reasoning:* new reason

## Decision

*Resolved 2026-04-01:* old-answer

*Reasoning:* old reason
```

A cold reader landing on the card cannot tell which decision is current — both look authoritative, and timestamps require date-comparison the dashboard contract is supposed to spare the reader. The README is the dashboard; it should reflect *the* decision, not a fossil layer.

## Empirical evidence

`reproduce.py` (see sibling file) calls `replace_or_append_decision` with a body containing both shapes and asserts the resulting Decision-heading count. On current code it prints:

```
Decision heading count after replace_or_append_decision: 2
expected 1, got 2 — FAIL
```

## Why it matters — and how the input reaches the function

The reachability path through shipping code:

1. Filer scaffolds a card with `--gate decision`. The body carries a `## Decision required` section per the decision-gate contract in `Skill(card-schema)`.
2. User / agent runs `goc decide <title>` once. `_cmd_decide` archives the required section to log.md (per [goc-decide-loses-deliberation-history-by-not-archiving-replaced-section](../goc-decide-loses-deliberation-history-by-not-archiving-replaced-section/)'s fix) and replaces it with `## Decision` in the README. Gate drops to `none`.
3. New evidence surfaces. The card is still `status: open` (non-terminal) so the terminal-status guard from [goc-decide-accepts-decisions-on-already-closed-cards](../goc-decide-accepts-decisions-on-already-closed-cards/) does NOT fire. An agent runs `goc status <title> open --gate decision` (or equivalent) to re-park the card. Per the documented `pull-card` workflow ("raise the gate to `decision` or `session`, write a `## Decision required` body section"), the agent adds a fresh `## Decision required` block alongside the existing `## Decision`.
4. User re-runs `goc decide <title>`. The function substitutes the required section, leaves the prior `## Decision` block in place — two headings.

Every step uses documented surfaces. No hand-edit of the README is required.

This is also a **meta-fix candidate**: the bug is the third instance of "`goc decide` doesn't keep the README dashboard in normal form" alongside the closed [goc-decide-corrupts-decision-text-via-regex-replacement-template](../goc-decide-corrupts-decision-text-via-regex-replacement-template/) and [goc-decide-loses-deliberation-history-by-not-archiving-replaced-section](../goc-decide-loses-deliberation-history-by-not-archiving-replaced-section/). The shared root is that the section-rewrite path in `_cmd_decide` walks a hand-rolled substitution rather than a canonical "ensure README has exactly one `## Decision`" pass. If a fourth instance lands, the architectural fix (a single normalising pass) becomes the right move.

## Decision required

Three credible fix paths:

- **Option A — Strip silently.** Detect a prior `## Decision` block in `replace_or_append_decision` (or its caller) and delete it before writing the new block. The new decision overwrites; the old `## Decision` content vanishes from both README and log.md. Smallest patch, but loses history.
- **Option B — Archive to log.md, then strip.** Mirror the contract established by [goc-decide-loses-deliberation-history-by-not-archiving-replaced-section](../goc-decide-loses-deliberation-history-by-not-archiving-replaced-section/): before replacing, archive the prior `## Decision` content to log.md as a dated entry (timestamp = the prior block's `*Resolved …:*` stamp, or the card's last `decision recorded` log entry). The README dashboard reflects only the new decision; the journal preserves the chain. Composes cleanly with the existing archival behaviour. **Recommended.**
- **Option C — Refuse and require supersession.** Treat re-decide on a card whose body already has a `## Decision` block as an error, analogous to the terminal-status guard. Print the suggestion already used for closed cards: file a new card and supersede via `goc status <old> superseded --by <new>`. Most conservative; breaks any in-flight workflow that relies on re-deciding open cards.

Option B is the recommended path because it preserves the README-as-dashboard / log.md-as-journal split the engine already enforces for the `## Decision required → ## Decision` transition. Option C is a behavioural breaking change. Option A loses history.

## Fix sketch (Option B)

```python
# goc/engine.py — _cmd_decide
prior_resolved = extract_resolved_decision_section(body)  # new helper
archived = extract_decision_required_section(body)
body = strip_resolved_decision_section(body)              # new helper
body = replace_or_append_decision(body, decision, reasoning, now)
# log.md entries: prior_resolved (if any) → archived (if any) → resolution
```

The new helpers mirror the existing `extract_decision_required_section` shape. A `RESOLVED_DECISION_RE` of `^## Decision[^\n]*\n(.*?)(?=^## |\Z)` (the same lookahead pattern) parses the block.

## Cross-references

- Sibling closed card: [goc-decide-loses-deliberation-history-by-not-archiving-replaced-section](../goc-decide-loses-deliberation-history-by-not-archiving-replaced-section/) — establishes the README-as-dashboard / log.md-as-journal contract this card extends to the resolved-block case.
- Sibling closed card: [goc-decide-corrupts-decision-text-via-regex-replacement-template](../goc-decide-corrupts-decision-text-via-regex-replacement-template/) — same `_cmd_decide` codepath, different defect shape.
- Sibling closed card: [goc-decide-accepts-decisions-on-already-closed-cards](../goc-decide-accepts-decisions-on-already-closed-cards/) — terminal-status guard that does NOT fire here (the card is still open).
- Convention reference: `Skill(card-schema)` "What goes where" — README as dashboard, log.md as journal.
