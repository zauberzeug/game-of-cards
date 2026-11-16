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
