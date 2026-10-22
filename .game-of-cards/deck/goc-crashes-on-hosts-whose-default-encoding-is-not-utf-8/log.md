## 2026-10-10T04:58:30Z — Card reads now reject undecodable bytes by name (cross-reference)

`card-with-non-utf-8-bytes-crashes-validate-and-every-deck-view-without-naming-it`
closed in `988a982b`. The new `engine.read_card_text` re-raises a card
README's `UnicodeDecodeError` as `FrontmatterError`. `load_card`,
`validate_deck_directories` and `migrate-list-style` read through it,
and `show` prints the card with U+FFFD and a warning. It picks no codec,
so the reads still use the host default and nothing this card asks is
answered.

What changes for the decision here: on a non-UTF-8 host, a card README
holding non-ASCII UTF-8 no longer crashes the deck commands when it is
read. The queue views skip it with `WARNING: <card>: README.md is not
decodable text: 'ascii' codec can't decode ...`, and `validate` reports
it as an `ERROR`. The bare queue still dies printing the table em-dash
(`_cmd_default`), and `install` still dies reading templates.

One trap for the regression test in this card's DoD, which asserts "no
`UnicodeDecodeError` / `UnicodeEncodeError` in stderr". The warning text
names the codec, not the exception class. So under a forced non-UTF-8
encoding, that assertion now passes even while cards are being skipped.
The test should also assert that a card with non-ASCII content is still
listed (or that no `is not decodable text` warning appears).

## 2026-10-14 — Cross-reference: the hooks now read every file as UTF-8

`pattern-generalization-stop-hook-crashes-on-a-config-or-transcript-that-does-not-decode`
(closed in e70b7f77) was this card's question on the hook side. The Stop
hook read `.game-of-cards/config.yaml` and the transcript in the host's
default encoding. Under an ASCII default it exited 1 at every turn end on
the shipped template's em dash, even with the hook off, and cp932, cp936,
cp949 and cp950 reject the template too. Both reads now pass
`encoding="utf-8"`. With
`session-start-hook-crashes-on-a-card-whose-bytes-do-not-decode`
(913ac168), every file read in `goc/templates/hooks/` names UTF-8 and
treats a decode failure as an unreadable file. Two points for the
decision:

- The hooks run as standalone scripts and never pass through
  `goc/cli.py:main`, so option (b) could not have reached them. They pin
  per site, the shape of option (a).
- This card's 67 sites are in `goc/engine.py` and `goc/install.py` only.
  The hooks were never part of that count and need nothing further here.
