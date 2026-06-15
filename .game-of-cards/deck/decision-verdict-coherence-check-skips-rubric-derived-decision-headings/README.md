---
title: decision-verdict-coherence-check-skips-rubric-derived-decision-headings
status: done
stage: null
contribution: medium
created: "2026-06-15T04:48:26Z"
closed_at: "2026-06-15T04:51:39Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` asserts the post-fix invariant — BOTH `## Decision` and `## Decision (rubric-derived)` are flagged while `## Decision required` stays unflagged — and exits zero on the fixed code.
  - [x] TDD: a regression test (extended `tests/test_validate_decision_contradicts_verdict.py`) proves `validate_decision_verdict_coherence` flags a re-scoping `## Decision (rubric-derived)` block left over a stale negative-verdict summary, and still does NOT flag `## Decision required`.
  - [x] MECHANICAL: `RESOLVED_DECISION_RE` (`goc/engine.py:392`) updated so a resolved-decision heading carrying a parenthetical qualifier (`## Decision (rubric-derived)`) is recognized, while the pending `## Decision required` section is still excluded; the docstring/comment updated to name both admitted forms.
  - [x] MECHANICAL: `python scripts/sync_plugin_assets.py --check` clean (engine.py ships in the three plugin `goc/` mirrors).
  - [x] MECHANICAL: `uv run goc validate` and the full `uv run python -m unittest discover -s tests` suite pass.
worker: {who: "claude[bot]", where: main}
---

# `validate_decision_verdict_coherence` ignores `## Decision (rubric-derived)` headings

## Problem

The advisory validator `validate_decision_verdict_coherence`
(`goc/engine.py:1968`) is the safety net built by
[goc-decide-leaves-stale-verdict-content-when-recording-a-rescope](../goc-decide-leaves-stale-verdict-content-when-recording-a-rescope/):
it flags a card whose recorded decision re-scopes/reverses a prior
verdict while the summary or a `> …` banner still asserts that
(negative) verdict. It locates the recorded decision via
`extract_resolved_decision_text` → `RESOLVED_DECISION_RE`.

That regex only matches a **bare** `## Decision` heading:

```python
# goc/engine.py:392-395
RESOLVED_DECISION_RE = re.compile(
    r"^## Decision[ \t]*\n(.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)
```

The `[ \t]*\n` anchor exists to exclude the *pending* `## Decision
required` section (correct — that heading has trailing text, so it
never matches). But the same anchor also excludes the documented
`## Decision (rubric-derived)` heading.

## Reachability

`Skill(create-card)` writes `## Decision (rubric-derived)` whenever the
project rubric pre-resolves a substantive decision and the card is
filed at `--gate none`:

> If the rubric gives a clear answer with a principle citation AND
> primary-source backing, scaffold the card with `--gate none` and
> pre-write a `## Decision (rubric-derived)` body section recording: …
> — `goc/templates/skills/create-card/SKILL.md:111-117`

So this is a *first-class, shipped* form of a resolved decision, not a
hypothetical hand-edit. A rubric-derived card whose decision text
contains re-scope/reversal language (e.g. "this reverses the earlier
call") and whose summary still reads "REFUTED: …" is exactly the
self-contradiction the validator was built to surface — and it slips
through silently.

## Evidence

`reproduce.py` builds two cards that differ only in the decision
heading and runs the validator over each:

```
bare '## Decision'               flagged: True
'## Decision (rubric-derived)'   flagged: False
'## Decision required' (pending) flagged: False
```

The bare-heading card is flagged; the rubric-derived card — same
decision text, same stale summary — is not.

## Fix direction

Widen `RESOLVED_DECISION_RE` to admit an optional parenthetical
qualifier on the heading, e.g.

```python
r"^## Decision(?: \([^)\n]*\))?[ \t]*\n(.*?)(?=^## |\Z)"
```

This recognizes both documented resolved forms (`## Decision` written
by `goc decide`, and `## Decision (rubric-derived)` written by
`create-card`) while still excluding `## Decision required` (which has
a bare word, not a parenthetical, after the heading). Pin the behavior
with the TDD test above so the "required" exclusion cannot regress.
