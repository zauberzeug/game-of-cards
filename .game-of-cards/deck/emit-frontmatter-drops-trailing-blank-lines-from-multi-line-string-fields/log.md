# Log

## 2026-06-25 — filed and fixed (fix-through during a pull-card drain)

Surfaced during a pull-card session whose ready queue was empty (all
`human_gate: none` open cards carry a `waiting_on` overlay), so the
audit fallback ran and found this emit-side round-trip gap.

**Root cause.** `emit_frontmatter` selected the block chomp indicator
from only two of YAML's three modes — `|` (clip) and `|-` (strip) — so a
multi-line string value ending in a blank line (`\n\n`) took the `|`
branch and was read back with a single trailing newline. The vendored
parser already implemented `|+` (keep) correctly; only the emit side
never selected it.

**Fix.** `goc/engine.py`:
- `emit_frontmatter` now picks the indicator three ways: `|+` when the
  value ends in `\n\n`, `|` when it ends in a single `\n`, `|-`
  otherwise.
- `_emit_block_field` is now chomp-aware: for the keep case it stops
  `rstrip("\n")`ing its input (which discarded the very blank lines keep
  exists to preserve) and emits exactly `value[:-1].split("\n")`. Clip
  and strip keep their existing `rstrip("\n").splitlines()` behavior, so
  `definition_of_done` (always `|`) is unaffected.
- Docstrings on both functions updated to describe the three-way choice.

**Scope note.** The reproduce and regression tests use values bounded by
a following field (the realistic shape — a multi-line `summary` is never
the last frontmatter field). A keep block placed flush against the
closing `---` hits a *separate* parse-boundary limitation:
`FRONTMATTER_RE`'s `\n---` delimiter plus `safe_load`'s `splitlines()`
together consume one trailing blank line. That is a distinct
parse-side concern and is intentionally out of scope for this
emit-side card.

**Verification.** `reproduce.py` exits 0; new regression test
`BlockScalarIndicatorRoundTripTest.test_value_with_trailing_blank_line_emits_keep`
plus an extended idempotency case; full suite 594 tests green;
`uv run goc validate` clean; plugin mirrors re-synced.

Project principle aligned: field-symmetric serialization — the emitter's
documented contract is a faithful emit->parse round-trip, and the parser
already honored `|+`. Mechanical fix, no decision gate.

## 2026-06-25 — Closure

All five DoD items satisfied: reproduce.py exits 0, the new keep
round-trip regression test and extended idempotency case pass, existing
clip/strip round-trips and DoD emission remain green, both function
docstrings describe the three-way chomp choice, and `goc validate` is
clean. Closed as a fix-through fix during a pull-card drain.

## 2026-06-25 — wired into the drift family

Post-close, this card was added as the 6th `advanced_by` instance of
[block-scalar-emitter-reenumerates-parser-whitespace-rules-and-keeps-drifting](../block-scalar-emitter-reenumerates-parser-whitespace-rules-and-keeps-drifting/)
— the open, decision-gated root that tracks `_emit_block_field`
re-enumerating `_parse_block_scalar`'s contract instead of sharing one.
This fix patched the chomp-indicator face of that drift in isolation; the
root's eventual unified mechanism should subsume it. (`advances` edge set
via `goc advance`.)

## Closure verification (2026-06-25T19:40:16Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-25 — Closure' present
