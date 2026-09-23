# Log

## 2026-09-02 — Production evidence from the zoe workspace deck (1041 cards)

The hypothesis reproduces in the field; the `goc status active` path is the one that fires.

**Today's sequence** (card `wettbewerbs-unterseiten-quellenapparat-online-stellen`, deck at
`~/.openclaw/workspace/.game-of-cards`): `goc new` without `--summary` → README hand-authored
(real DoD + body, `draft: true` still set) → `goc status … active` (auto-commit
`2f44cec7 deck: … open → active`, draft flag cleared) → `goc done` (`6fc9c24b`). Every verb
exited 0. The deck was validate-red from that moment; nothing said so until the nightly full
suite ran `goc validate` 11½ hours later and failed
`tests.contracts.test_goc_contract.GocContract.test_deck_validates`.

**Frequency**: 12 of the 18 nightly suite runs between 2026-08-18 and 2026-09-02 were red on
this error, each time on a different freshly released card — `belege-aus-getmyinvoices-…`
(08-18), three cards on 08-21 (three runs that night), `nach-zeitstempel-sortierter-verlauf-…` (08-23),
`wirkt-die-tippzeit-im-prompt-…` (08-24/25), `ki-wissenshub-wird-mehrseitig-…` (08-27…08-31,
five nights), `delaval-project-gulp-angebot-…` (09-01),
`wettbewerbs-unterseiten-quellenapparat-…` (09-02). So the defect is not an edge case of one
filer: it is the normal outcome whenever a card is scaffolded as a draft and claimed before a
summary is written.

**Code sites confirmed by reading**: `goc/engine.py` clears the draft flag in three places and
checks the summary in none — `_cmd_done` (line ~4811), the bundle-close loop (~4907) and the
claim branch of `_cmd_status` (~5964). `_cmd_publish` (~6017) gates on
`is_placeholder_scaffold` only, as the card body already states.

**Not covered by this note**: no `reproduce.py` was committed, so the `unverified` tag stands.
This is field evidence that the hypothesis is real, not the falsification recipe the DoD asks
for. The decision in "Decision required" is still open.

Repaired downstream by adding the missing summary to the offending card; the workspace deck is
validate-green again (`goc validate` exit 0, warnings only).
