## 2026-05-26T20:42:21Z: renamed from frontmatter-emitter-does-not-quote-integer-or-date-looking-scalars

## 2026-05-26: superseded by frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values

This card's scope (quote integer-looking string scalars the parser coerces
to `int`) is a strict subset of the broader sibling card, which was filed
~12 min later and closed 2026-05-26T21:02:38Z. That card replaced the
hand-maintained `_YAML_RESERVED` trigger with `_parser_coerces_scalar`
(goc/engine.py:177-192), deriving the quote-trigger from the parser's own
recognizers — including `yaml._INT_RE`, which covers exactly the
integer-looking strings (`"123"`, `"007"`, `"-3"`) this card targeted.
Verified empirically: those values now emit double-quoted and round-trip
back as `str`. No separate fix needed; superseded rather than independently
closed because no distinct "before the fix" reproduce.py state exists for
this narrower card.
