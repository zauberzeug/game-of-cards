---
title: internal-project-name-keeps-reaching-cards-because-the-rule-against-it-is-unguarded
summary: "AGENTS.md forbids naming internal projects in cards and calls the rule unguarded but audited clean on 2026-07-27; the card that chose not to guard it did so because neither confidentiality rule had an observed instance. The internal project AGENTS.md itself gives as the rule's example is named on 16 lines across 6 cards, 3 of which already held it when the audit declared the deck clean. Redact the instances, correct the audit claim, and revisit the guard now that the zero-instance premise is false."
status: active
stage: null
contribution: medium
created: "2026-11-09T02:34:58Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation, infra]
definition_of_done: |
  - [ ] MECHANICAL: the 16 lines in § Instances are rephrased to "a downstream consumer repository" (or an equivalent that names no internal project), every technical fact kept; a case-insensitive grep of `.game-of-cards/deck/` for the example term AGENTS.md lists matches only `worker:` values
  - [ ] MECHANICAL: individual attributions in card prose (§ Instances, second table) are swept against the rule; `worker:` values and slug examples, which AGENTS.md's worker docs permit, are left alone; the sweep's verdicts are recorded in log.md
  - [ ] MECHANICAL: AGENTS.md § Card authoring rules no longer states "audited clean on 2026-07-27"; it states what now enforces the rule, or the date and result of the latest audit
  - [ ] TDD: if a guard lands (see § Fix), a test in `tests/test_card_authoring_rules.py` plants a card body naming the example term and asserts the guard fails, and the cleaned deck passes it
  - [ ] PROCESS: `uv run goc validate`, `uv run python scripts/check_card_language.py` and the regression suite pass
worker: {who: "claude[bot]", where: main}
---
# Internal project name keeps reaching cards because the rule against it is unguarded

## Location

- `AGENTS.md` § Card authoring rules: "do not name internal meetings […],
  internal projects […], or individual participants in card bodies", followed
  by "This rule and the quoting rule above are **unguarded** […] Both were
  audited clean on 2026-07-27."
- [card-authoring-rules-in-agents-md-have-no-enforcement-path](../card-authoring-rules-in-agents-md-have-no-enforcement-path/)
  (done), § Decision: "Neither is worth a speculative guard at zero observed
  instances". Only the English-only rule got a guard
  (`scripts/check_card_language.py`).

## What's broken

The decision not to guard the no-internal-names rule rested on there being no
instance. There were instances that day, and there are more now. The internal
project that AGENTS.md itself names as the rule's example appears on 16 lines
across 6 cards. Three of those cards held the name when the audit declared the
deck clean; three more were filed afterwards. Every occurrence is the same
usage: a downstream consumer repository cited as the source of the evidence.
"A downstream consumer repository" carries every technical fact the sentence
needs.

## Instances

Project name, found with a case-insensitive search for the example term,
excluding `worker:` values (machine names are permitted there):

| card | status | lines | first written |
|---|---|---|---|
| [goc-tool-files-cards-into-wrong-agents-deck-on-multi-agent-gateways](../goc-tool-files-cards-into-wrong-agents-deck-on-multi-agent-gateways/) | open | README 45 | 2026-06-12 |
| [autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish](../autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish/) | open | README 31, 76; log 3, 8 | 2026-07-26 |
| [human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property](../human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property/) | open | README 13 (summary), 48, 79; log 3, 28 | 2026-07-26 |
| [subdirectory-deck-resolution-has-no-test-pinning-it](../subdirectory-deck-resolution-has-no-test-pinning-it/) | done | README 40 | 2026-08-01 |
| [zauberzeug-claude-marketplace-pin-drifts-silently-behind-releases](../zauberzeug-claude-marketplace-pin-drifts-silently-behind-releases/) | open | log 2, 4 | 2026-08-01 |
| [draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck](../draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck/) | done | README 66, 98; log 24 | 2026-10-06 |

Individual attributions, a second and older tier: sentences such as
"`<name>` decided …", "`<name>` asked …", "Reported by `<name>` …" and
"*Reasoning:* `<name>`: …". A pattern search finds at least these:
[provide-openclaw-plugin-for-skills-and-hooks](../provide-openclaw-plugin-for-skills-and-hooks/)
log 87,
[build-game-of-cards-project-website](../build-game-of-cards-project-website/)
README 47,
[add-readme-to-claude-code-plugin](../add-readme-to-claude-code-plugin/)
README 135,
[kickoff-asks-where-goc-briefing-lives](../kickoff-asks-where-goc-briefing-lives/)
README 31,
[draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck](../draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck/)
README 98 and
[human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property](../human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property/)
log 3. Most date from May 2026 decision records. The same first name also
appears as `worker:` values and as the slug in AGENTS.md's own worker
example; those are permitted and out of scope.

## Why it matters

The rule exists so that cards, a public and permanent record, carry no
internal project names and no attributions of work to individuals.
AGENTS.md's "audited clean" sentence tells every reader the rule holds. A
reader filing a card from downstream evidence has no signal otherwise. Four of
the six cards are live, and two are at human gates where they will be read
closely. The names already sit in git history; the fix is about HEAD and about
what new cards copy.

## Fix

1. **Redact the 16 lines** in place. In the log entries, change only the
   name; the entry stays a dated record of what happened.
2. **Sweep the attribution tier** card by card. A decision record can say a
   maintainer decided without naming them.
3. **Correct AGENTS.md's audit sentence.**
4. **Guard the example term** in the existing repo-local card-language check
   (`scripts/check_card_language.py`, its pre-commit hook and
   `tests/test_card_authoring_rules.py`). It scans title, summary and DoD
   today; this guard has to scan bodies and logs too. The 2026-07-27 decision
   rejected a two-term denylist as false confidence and as needing a
   non-public home. Both objections are weaker against the evidence: all 16
   lines use the exact term AGENTS.md already publishes, so listing it
   exposes nothing new, and it would have caught every instance. Individual
   names stay unguarded, since no public list of them is acceptable.
