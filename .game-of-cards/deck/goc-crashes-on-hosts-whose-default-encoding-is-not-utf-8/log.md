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
