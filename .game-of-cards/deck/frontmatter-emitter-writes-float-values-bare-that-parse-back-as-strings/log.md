# Log

## 2026-05-26 — PROCESS decision: refuse floats (option a), do not add a parser recognizer

Chose **(a) drop float handling from the emitter** over **(b) add a float
recognizer to the vendored parser**.

Rationale:

- No card frontmatter field is a float — contribution/value scores are
  computed at render time and never stored — so floats never legitimately
  reach `_yaml_inline`. Adding a float regex + `_parse_scalar` branch (option
  b) would be speculative surface for a type the schema never uses, and would
  drag in float edge cases (`inf`/`nan`/`1e20`/`1.0`) that have no schema
  consumer.
- A *bare* drop alone is insufficient: removing `float` from the
  `isinstance(value, (int, float))` branch lets a float fall through to
  `str(value)` → `"3.14"`, which the quote-triggers do not catch, so it still
  emits bare and reads back as the string `"3.14"` — the same silent
  coercion. The DoD anticipates this ("refuses/quotes them so no silent
  string-coercion occurs").
- Refusing at the serialization boundary with a `FrontmatterError` fails loud
  instead of corrupting, and is drift-proof: there is no second float
  truth-set to keep in sync with the parser (the recurring root cause behind
  the int/null/bool sibling cards).

Fix: `goc/engine.py` `_yaml_inline` now handles `int` bare and raises
`FrontmatterError` for `float`. Plugin mirrors re-synced. `reproduce.py`
asserts the refusal plus regression guards (int still round-trips bare;
float-looking *string* still round-trips as a string).

## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/engine.py` `_yaml_inline` — split the `int`/`float`
  numeric branch; `int` still emits bare, `float` now raises `FrontmatterError`
  at the emit boundary instead of silently round-tripping to a string. Plugin
  mirrors (`claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`) re-synced.
- **Verification**: `reproduce.py` exits 0 — float refused; `int` round-trips
  bare as int; float-looking string round-trips as string.
- **Audit**: PASS — no rubric configured; mechanical fix (field-symmetric
  serialization boundary).
- **Project impact**: n/a
- **Tests**: no pytest suite; `goc validate` clean (no ERROR), `reproduce.py` 0.
- **Bundled with**: n/a

## Closure verification (2026-05-26T22:13:26Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
