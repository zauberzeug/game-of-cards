## 2026-05-30T04:38:15Z — Closure

- **What changed**: `goc/engine.py:181-186, 236` — replaced the
  `_YAML_BLOCK_TOKENS` frozenset with `_YAML_BLOCK_HEADER_RE`, a regex
  shaped by reference to the vendored parser's `_BLOCK_INDICATOR_RE`,
  so the explicit-indent variants (`|2`, `|3`, `|10`, `|2-`, `|2+`)
  trigger quoting alongside the bare `|`/`>` forms.
- **Verification**: `reproduce.py` exits 0 — all five explicit-indent
  probes round-trip emit→parse unchanged; previously each silently
  collapsed to `''`.
- **Audit**: PASS — no principle touched, mechanical fix
  (field-symmetric serialization: closing the emit→parse round-trip
  the vendored parser defines, identical shape to the closed sibling
  `frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values`).
- **Project impact**: n/a
- **Tests**: 244 passed / 0 failed (full regression suite + reproduce.py);
  plugin mirrors re-synced (claude/codex/openclaw engine.py).
  `uv run goc validate` clean for this card; one unrelated pre-existing
  error (`deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers`
  has an unknown `verified` tag) is independent of this work.
- **Bundled with**: n/a

## Closure verification (2026-05-30T04:38:27Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
