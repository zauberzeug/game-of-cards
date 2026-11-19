## 2026-11-16T01:30:00Z — Parked as unverified by audit-deck

A hunter candidate: the audit's general-purpose subagent reproduced it on
scratch decks. The auditing agent read `is_placeholder_scaffold`
(`goc/engine.py:2992-3005`), the refusal text (`:6901-6902`) and the
reference's Draft contract (`:62-63`), and reproduced both half-authored
cases by hand. The output is in the README. Parked without a
`reproduce.py` under the audit's park-or-disprove rule.

- **Dedup**: `is_placeholder_scaffold`, `SCAFFOLD_DOD_PLACEHOLDER`,
  `replace with real criteria`, `pure placeholder` and `half-authored`
  turned up no decision that half-authored drafts may be published.
  [placeholder-cards-superseded-before-they-are-authored](../placeholder-cards-superseded-before-they-are-authored/)
  (done) introduced the check and got a post-close amendment pointing here.

## 2026-11-19T04:33:52Z — Verified: the hypothesis holds

`reproduce.py` runs the Falsification recipe on `main` at `f109258e`, with
`--summary` on every `goc new` so the summary-release gate cannot be what
refuses. Both half-authored drafts published with exit 0, their draft flags
were cleared and `goc --ready` listed both beside the authored control.
The script exited 1. Dropped the `unverified` tag.

## 2026-11-19T04:33:52Z — Direction: tighten publish, matching on whole lines

Took the default the card proposed: publish refuses while *either*
placeholder remains. All three surfaces (the reference's Draft contract,
the refusal text, `goc new`'s hint) already promised that rule, and no card
records a decision that a half-authored draft may be released. The other
direction would have documented a gap that lets the autonomous loop pull a
card with no closure contract or no briefing.

The predicate was renamed `is_placeholder_scaffold` → `scaffold_placeholders_left`
and returns the parts still left (`["DoD", "body"]`, one of them, or `[]`).
The old name read as "an untouched scaffold", which is the narrow meaning
that let half-authored drafts through. The list also lets the refusal name
the half that is left: `(placeholder DoD)`, `(placeholder body)`, and, for an
untouched scaffold, the unchanged `(placeholder DoD and body)`.

The match moved from a substring test to whole-line equality. With one
mention now enough to refuse, a substring test would refuse any authored
draft that quotes the placeholder inside a sentence, as
`placeholder-cards-superseded-before-they-are-authored` does.
`test_publish_releases_draft_that_quotes_a_placeholder_in_a_sentence` pins
this: swapping the line test back to a substring test fails it (checked in a
scratch worktree). The new half-authored cases fail on the pre-fix engine
(also checked in a scratch worktree).

`goc status active` and `goc done` stay out of scope. Claiming a placeholder
is deliberate (`test_status_active_auto_clears_draft` claims a pure
scaffold), and `goc done` already refuses an unchecked placeholder DoD item.

## 2026-11-19T04:33:52Z — Reproducers of closed cards that half-authored a draft

Four closed cards' `reproduce.py` scripts depended on the old rule or name.
Each now runs its setup in full and exits 0. Each card's log.md has a
pointer back here.

- `cli-reference-steers-authors-onto-deprecated-blocked-status-not-the-wait-overlay`
  authored only the DoD. With the fix its probe card stayed a hidden draft
  and the script still exited 0, now without showing the contrast it prints.
  It now authors the body too; its output is byte-identical to the pre-fix run.
- `ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card`
  filed `real-ready` without `--summary` and left the body placeholder in
  place. Its publish had been refused since the summary-release gate, so
  the script passed on an empty queue. It now passes with `real-ready` listed.
- `goc-new-scaffolds-no-summary-field-so-fresh-cards-pass-validate-without-one`
  had exited 1 since publish began refusing summary-less drafts: validate
  never saw a published card. Its setup now replaces the body placeholder,
  so only the summary is missing. When publish refuses, the script strips the
  flag by hand, the remaining route to a published summary-less card.
  Validate then rejects the card and the script exits 0.
- `engine-comments-claim-unflagged-placeholder-cards-count-as-drafts`
  called `engine.is_placeholder_scaffold`. It now checks
  `scaffold_placeholders_left(card) == ["DoD", "body"]`, which is what its
  "both placeholders present" label says.

## 2026-11-19T04:37:08Z — Closure

- **What changed**: `goc/engine.py:3072` — `is_placeholder_scaffold` →
  `scaffold_placeholders_left`, which returns the parts still holding their
  `goc new` placeholder line. `goc/engine.py:7151-7159` — `goc publish`
  refuses while either part is left and names it in the unchanged refusal
  shape (`(placeholder DoD)` / `(placeholder body)` /
  `(placeholder DoD and body)`). The `publish` help line, `_cmd_publish`
  and `card_is_draft` docstrings, and `Skill(card-schema)` reference.md
  § Draft contract state the same rule. Mirrors re-synced
  (`scripts/sync_plugin_assets.py`, `scripts/port_skills_to_openclaw.py`).
  Four closed cards' reproducers restored (entry above). The gated card
  `autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish` names the
  guard by its new name.
- **Verification**: `reproduce.py` exit 1 → 0 (both half-authored drafts now
  exit 2 and stay drafts; the authored control publishes and is the only
  card `goc --ready` lists). The two new half-authored subtests fail on the
  pre-fix engine. A substring variant of the line rule fails the
  quoted-placeholder test.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1512 passed / 0 failed (`uv run python -m unittest discover -s tests`);
  `uv run goc validate` exit 0; both mirror drift checks clean.

## Closure verification (2026-11-19T04:37:11Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-11-19T04:37:08Z — Closure' present
