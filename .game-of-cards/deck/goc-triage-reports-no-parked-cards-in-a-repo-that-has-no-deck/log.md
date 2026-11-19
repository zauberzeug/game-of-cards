## 2026-11-16T01:30:00Z — Parked as unverified by audit-deck

A hunter candidate: the audit's general-purpose subagent reproduced it in a
deckless scratch repo. The auditing agent read `_cmd_default`'s notice
(`goc/engine.py:4854-4855`) and `_cmd_triage` (`:7856-7900`), and
reproduced it by hand. The output is in the README. Parked without a
`reproduce.py` under the audit's park-or-disprove rule.

- **Dedup**: `MISSING_DECK_PHRASE`, `_missing_deck_message`,
  `no Game of Cards deck found`, `974a1400`, and triage with "missing deck".
  The notice's origin card,
  [denied-preamble-block-aborts-skill-load-before-the-preflight-routes-to-kickoff](../denied-preamble-block-aborts-skill-load-before-the-preflight-routes-to-kickoff/),
  is active, held by another worker, and has only release items left. It was
  left untouched, and this card links to it.

## 2026-11-19T04:31:00Z — Verified: the hypothesis holds

`reproduce.py` (new, next to the README) on `476f0b2f`, the claim commit on
top of `f002ea59`, exits 1. In a scratch `git init` repo with no
`.game-of-cards/`, the control `goc` prints the notice on stderr. `goc triage`
prints `No parked cards (status: open; gate ≠ none).` and `goc triage --json`
prints `[]`, both with exit 0 and an empty stderr. The `unverified` tag is
dropped. The card now has a working reproducer, which its tag row excludes.

## 2026-11-19T04:47:34Z — Closure

- **What changed**: `goc/engine.py`. The new `_note_missing_deck()` holds the
  notice `_cmd_default` used to print inline, and its docstring states the
  contract that every read view calls it before loading the deck.
  `_cmd_default` and `_cmd_triage` both call it. Plugin mirrors are re-synced
  (`claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`).
- **Tests**: `tests/test_missing_deck_notice.py` gains
  `test_triage_names_the_missing_deck_like_the_queue_view`. Both triage forms
  must exit 0, keep their stdout, and print the default view's notice
  byte-for-byte. Before the fix both subtests fail. It also gains
  `test_triage_stays_silent_on_an_existing_deck`, for a canonical and a legacy
  deck. The module runs 8 tests OK.
- **Suite**: `uv run python -m unittest discover -s tests` ran 1514 tests
  OK. An earlier run, made before the `unverified` tag was dropped, had one
  failure: `test_live_cards_satisfy_every_state_row` flagged this card's tag
  once its reproducer existed.
- **Verification**: `reproduce.py` exits 0 after the fix, with the notice
  line identical across `goc`, `goc triage` and `goc triage --json`.
- **Survey**: every engine verb in a repo with no deck, before the fix:

  | verb | exit | says the deck is missing? |
  |---|---|---|
  | `goc` / `--ready` / `--board` / `--json` / `--waiting` / `-v` | 0 | yes, the notice |
  | `goc triage`, `goc triage --json` | 0 | **no** (this card) |
  | `goc quality-pass` (any `--status`) | 0 | **no**: "Title antipatterns: clean." |
  | `goc validate` | 0 | names the empty deck path itself (`goc-validate-reports-a-clean-pass-when-it-validated-no-cards`) |
  | `goc repair-edges` | 0 | no; "No half-edges found." stays accurate, and refine-deck runs it only after validate reports half-edges |
  | `goc migrate` | 0 | no; "No legacy deck/ found; nothing to migrate." stays accurate |
  | `goc migrate-list-style` | 1 | an error naming the missing deck path |
  | `show`, `status`, `done`, `attest`, `wait`, `advance`, `unadvance`, `move`, `decide`, `publish` on a title | 2 | an error naming the missing card path |

  `goc quality-pass` is the other read view that never called the helper.
  It is filed and fixed through as
  `goc-quality-pass-reports-a-clean-deck-in-a-repo-that-has-no-deck`.
  Fixing it through also turned up a defect outside the notice:
  `goc quality-pass --llm` still calls `claude -p` when its selection is
  empty, because the `if not live: return` guard sits inside the
  closed-cards branch. That one is filed separately.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a.
- **Other cards**: no open or active card describes this defect. The grep
  for `_cmd_triage`, `goc triage`, `missing-deck notice` and
  `_missing_deck_message` hits only cards about other triage behaviour.

## Closure verification (2026-11-19T04:49:18Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-11-19T04:47:34Z — Closure' present
