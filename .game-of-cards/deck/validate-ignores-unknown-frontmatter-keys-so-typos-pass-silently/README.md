---
title: validate-ignores-unknown-frontmatter-keys-so-typos-pass-silently
status: open
stage: null
contribution: medium
created: "2026-06-20T04:41:15Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] (replace with real criteria once the decision below is recorded)
---

# validate-ignores-unknown-frontmatter-keys-so-typos-pass-silently

`goc validate` never checks that a card's frontmatter keys are drawn
from the known set (`required_fields ∪ optional_fields`). The schema
declares `optional_fields` as a closed list, but the engine loads it
into the `Schema` dataclass and never reads it again — so a misspelled
or invented key is silently accepted.

## Location

- `goc/schema.yaml:9-20` declares the closed `optional_fields` set
  (`summary`, `stage`, `closed_at`, the four relation fields, `tags`,
  `worker`, `waiting_on`, `waiting_until`).
- `goc/engine.py:469` (`optional_fields: list[str]` dataclass field)
  and `goc/engine.py:490` (`optional_fields=fm["optional_fields"]`) are
  the ONLY references. `grep -rn "optional_fields" goc/` returns no read
  site. `validate_card` checks `required_fields` and per-field value
  enums but has no "key present in card but not in the known set" check.

## Empirical evidence

A card with `wating_on: external` (typo of `waiting_on`) and
`totally_made_up_field: 7` validates clean:

```
$ uv run goc validate     # in a temp deck holding the card above
OK  typo-field-card
exit=0
```

The most damaging instance is the `wating_on` typo: the impediment
overlay that hides deferred cards from queues and drives SLE escalation
is silently inert, with no warning — the card stays in the pull queue
when the author intended it parked.

## Why it matters

`goc validate` is the deck's integrity gate (CI runs it). It already
guards value-level drift (non-string DoD, whitespace-only worker,
calendar-impossible dates, non-string list elements). A whole class of
*key*-level drift — typos of real fields, leftover keys from a renamed
schema, hand-authored junk — passes through untouched. The closed
`optional_fields` set in the schema signals the intent to constrain
keys; the validator just never honors it.

Reachability: hand-edited cards and one-shot-authored cards routinely
introduce stray keys; a typo of `waiting_on`/`waiting_until`/`human_gate`
is the realistic failure that silently changes scheduling behavior.

## Decision required

The fix is not purely mechanical because it interacts with the open
feature card
[support-custom-frontmatter-fields-with-enum-and-required-when-rules](../support-custom-frontmatter-fields-with-enum-and-required-when-rules/),
which would let consumers declare *additional* allowed fields. Pick the
enforcement model before implementing:

1. **Hard error on unknown keys.** `validate` exits non-zero on any key
   outside `required ∪ optional`. Strictest; would need the custom-fields
   card to extend the allowed set, or it breaks consumers who add their
   own keys today.
2. **Warn only (advisory).** Emit a `WARN UNKNOWN_FIELD` line, exit 0.
   Non-breaking, surfaces typos, but CI stays green so drift can persist.
3. **Near-miss typo detection only.** Error/warn only when an unknown
   key is within edit-distance 1-2 of a known field (catches `wating_on`,
   ignores deliberate custom keys). Best UX, most code.

The choice also determines whether `optional_fields` should stay a
closed set or become an extensible base. Note: `goc/schema.yaml` and
`goc/templates/skills/card-schema/schema.yaml` both carry the dead
`optional_fields` block; a fix must keep them consistent (the template
is source-of-truth per the sync rules).

Surfaced by an audit-deck hunter during a queue-empty pull-card run on
2026-06-20; parked here as the unfollowed candidate (see log.md).
