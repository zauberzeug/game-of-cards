---
title: internal-project-name-keeps-reaching-cards-because-the-rule-against-it-is-unguarded
summary: "RESOLVED. AGENTS.md called its no-internal-names rule audited clean while the internal project it names as the rule's example sat on 16 lines across 6 cards, and 62 more lines named the maintainer as decider or signer. All are rephrased ('a downstream consumer repository', 'the maintainer'), along with three verbatim discussion quotes. scripts/check_card_language.py now fails on the two example names AGENTS.md publishes, anywhere under the deck except a README's worker value, and a test holds its list to AGENTS.md both ways. AGENTS.md states the guard and that individual names and the quoting rule stay unguarded."
status: done
stage: null
contribution: medium
created: "2026-11-09T02:34:58Z"
closed_at: "2026-11-09T05:27:54Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, infra]
definition_of_done: |
  - [x] MECHANICAL: the 16 lines in § Instances are rephrased to "a downstream consumer repository" (or an equivalent that names no internal project), every technical fact kept; a case-insensitive grep of `.game-of-cards/deck/` for the example term AGENTS.md lists matches only `worker:` values
  - [x] MECHANICAL: individual attributions in card prose (§ Instances, second table) are swept against the rule; `worker:` values and slug examples, which AGENTS.md's worker docs permit, are left alone; the sweep's verdicts are recorded in log.md
  - [x] MECHANICAL: AGENTS.md § Card authoring rules no longer states "audited clean on 2026-07-27"; it states what now enforces the rule, or the date and result of the latest audit
  - [x] TDD: if a guard lands (see § Fix), a test in `tests/test_card_authoring_rules.py` plants a card body naming the example term and asserts the guard fails, and the cleaned deck passes it
  - [x] PROCESS: `uv run goc validate`, `uv run python scripts/check_card_language.py` and the regression suite pass
  - [x] MECHANICAL: the verbatim discussion quotes carried by the swept lines are paraphrased, and AGENTS.md no longer vouches for the quoting rule either (added during the work, see § Fix step 2)
worker: {who: "claude[bot]", where: main}
---

# Internal project name keeps reaching cards because the rule against it is unguarded

## Resolution

The two example names AGENTS.md publishes are now guarded, every instance the
sweep found is rephrased, and AGENTS.md says what is enforced and what is not.
`scripts/check_card_language.py` fails the `card-language` pre-commit hook and
CI on either name anywhere under `.game-of-cards/deck/`, except in a card
README's frontmatter `worker:` value. Run against the tree as filed, it
reports exactly the 16 lines in § Instances. Individual names stay unguarded
on purpose; § Fix step 4 says why.

## Location

- `AGENTS.md` § Card authoring rules, the no-internal-names bullet. As filed,
  it called this rule and the quoting rule **unguarded** but "audited clean on
  2026-07-27". It now names the guard, the `worker:` exemption, and what to
  write instead, and it says which parts stay unguarded and unaudited.
- `scripts/check_card_language.py`: `PUBLISHED_INTERNAL_NAMES`,
  `flag_internal_names`, `scan_deck_for_internal_names`, and `main`, which
  runs both checks.
- `tests/test_card_authoring_rules.py`: `PublishedInternalNamesGuardTest`.
- `.pre-commit-config.yaml`: the `card-language` hook, whose display name now
  covers both checks.
- [card-authoring-rules-in-agents-md-have-no-enforcement-path](../card-authoring-rules-in-agents-md-have-no-enforcement-path/)
  (done), § Decision: "Neither is worth a speculative guard at zero observed
  instances". That premise was false on its own date.

## What was broken

The decision not to guard the no-internal-names rule rested on there being no
instance. There were instances that day, and more by the time this card was
filed. The internal project that AGENTS.md itself names as the rule's example
appeared on 16 lines across 6 cards. Three of those cards held the name when
the audit declared the deck clean; three more were filed afterwards. Every
occurrence was the same usage: a downstream consumer repository cited as the
source of the evidence. "A downstream consumer repository" carries every
technical fact the sentence needs.

## Instances

Project name, found with a case-insensitive search for the example term,
excluding `worker:` values (machine names are permitted there). Line numbers
are as filed; every line is rephrased.

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
"*Reasoning:* `<name>`: …". The filing search found at least these:
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
log 3. The full sweep found 62 such lines in 26 cards, mostly May 2026
decision records but as late as 2026-10-25. The same first name also appears
as `worker:` values and as the slug in AGENTS.md's own worker example; those
are permitted and out of scope.

## Why it matters

The rule exists so that cards, a public and permanent record, carry no
internal project names and no attributions of work to individuals.
AGENTS.md's "audited clean" sentence told every reader the rule held, and a
reader filing a card from downstream evidence had no signal otherwise. Four of
the six cards are live, and two are at human gates where they will be read
closely. The names already sit in git history; the fix is about HEAD and about
what new cards copy.

## Fix

Applied 2026-11-09; verdicts and counts are in `log.md`.

1. **Redacted the 16 lines** in place. Each became "a downstream consumer
   repository", "a downstream card" or "that drain"; every downstream card
   slug, date and count stayed. In log entries only the name changed.
2. **Swept the attribution tier** deck-wide, not only the six listed lines.
   62 lines naming the maintainer as decider, reporter, signer or credential
   holder now say "the maintainer". Three of them also quoted a discussion
   verbatim, which the quoting rule forbids, so those quotes are paraphrased.
   Identifiers stayed: worker-slug examples and reproducer fixtures,
   home-directory paths in quoted tool output, rendered worker labels, and
   the registry handles that are one card's own subject.
3. **Corrected AGENTS.md.** The audit sentence is gone. The bullet names the
   guard and its one exemption. It says what to write instead, and that
   individual names, unpublished internal names and the quoting rule stay
   unguarded and unaudited. It also gives the date and result of this sweep.
4. **Guarded the two published example names** in the existing check. The
   2026-07-27 decision rejected a two-term denylist as false confidence and
   as needing a non-public home. Neither objection survives the evidence: all
   16 lines used the exact term AGENTS.md publishes, so listing it exposes
   nothing new, and it catches every instance. The table may hold only names
   AGENTS.md prints, and
   `test_table_holds_exactly_the_examples_agents_md_publishes` enforces that
   in both directions. Individual names stay unguarded, since no public list
   of them is acceptable. The check reads every file under the deck because
   all 16 lines sat in bodies and logs, which the language check skips.
   Matching is whole-word and folds case and diacritics. A space, hyphen,
   underscore or line break between the two words of the meeting name still
   matches. The check adds 0.25 s to the hook.
