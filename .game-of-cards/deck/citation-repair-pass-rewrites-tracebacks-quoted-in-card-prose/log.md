## 2026-11-23T02:40:00Z — Filed from the refine-deck hygiene pass

Surfaced by the 2026-11-23 citation anchor check. Its scope classifier
implements the marker test, and it proposed moving the quoted traceback frame
on `repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field`
in both its first round and its committed re-run. The pass held the frame by
reading the line. The 2026-11-16 pass had restored the same frame the same
way. Recognising the line by hand on every pass is the gap this card closes.

Dedup: no open or gated card names records in prose. The nearest card,
`citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks`
(done 2026-09-01), wrote the scope rule and scoped it to fences. A forward
pointer is in its log. `file-line-citations-drift-again-within-days-of-every-repair-pass`
asks which citation form cards should use. Under any form it picks, a
quoted record still needs a scope test, so it is a separate question.

Gate `none` and contribution `low`: one live instance, and the fix extends a
test that already works to the one place it does not reach. The rejected
keyword alternative is recorded in `## Fix`.
