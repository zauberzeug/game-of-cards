## 2026-08-30 — Counter-evidence resolved for the strict-YAML half

- **What changed**: `goc-writes-card-summaries-a-standard-yaml-reader-cannot-parse`
  closed by transcribing YAML 1.2 §5.3's `c-indicator` list into
  `goc.engine._YAML_INDICATORS` and having
  `scripts/check_card_frontmatter_yaml.py` import it. The seven shapes that
  broke Options A/B/C as written are now quoted at the emitter.
- **Effect on this card's decision**: the pending question shrinks to the
  *parser* half of the union — `_parser_coerces_scalar`,
  `_YAML_BLOCK_HEADER_RE` and the `s != s.strip()` clause are still
  hand-maintained twins of `yaml_lite`. Whichever of A/B/C is chosen must keep
  the spec-derived clauses beside it, not replace them: a trigger derived from
  parser behaviour alone stays silent on all seven of those shapes.
- **New precedent for Option B**: the spec-import pattern (one definition in
  the engine, imported by the second consumer, drift caught by a test that
  enumerates the external reference independently) is now live in
  `tests/test_emitter_strict_yaml_quoting.py`.
- **Still gated**: `human_gate: decision` unchanged — nobody has picked a
  factoring for the parser half.
