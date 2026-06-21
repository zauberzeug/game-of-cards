---
title: frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting
summary: "`emit_frontmatter`'s inline-scalar emitter (`_yaml_inline`, engine.py:248-253) decides whether to quote a scalar by re-enumerating, in independent hand-maintained predicates, the value shapes the vendored parser (`_vendor/yaml_lite.py`) would coerce or reject. Because the emitter's quoting knowledge is a copy of the parser's rather than derived from it, the two drift — 8+ separate bug cards have patched this one predicate family one shape at a time. Decision-gated on a factoring that derives the emitter's quote decision from parser behaviour (one source of truth)."
status: open
stage: null
contribution: medium
created: "2026-06-18T05:08:40Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - frontmatter-emitter-does-not-quote-empty-string-scalar-that-parses-as-null
  - frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values
  - frontmatter-emitter-does-not-quote-integer-looking-string-scalars
  - frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values
  - frontmatter-emitter-leaves-explicit-indent-block-scalar-headers-unquoted
  - frontmatter-emitter-leaves-folded-block-scalar-headers-unquoted
  - frontmatter-emitter-writes-float-values-bare-that-parse-back-as-strings
  - inline-emitter-writes-multi-line-strings-bare-destroying-subsequent-frontmatter
tags: [meta-fix, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: pick a factoring (see `## Decision required`) and record it in log.md with rationale.
  - [ ] MECHANICAL: the emitter's quote decision is derived from the parser's behaviour (one source of truth), not re-enumerated by independent hand-maintained predicates that can omit a shape the parser reinterprets.
  - [ ] TDD: every existing emitter round-trip regression test still passes unchanged (the family below is the contract the unified mechanism must preserve).
  - [ ] TDD: a single property-style test asserts the round-trip invariant directly — for a representative scalar corpus, `parse(emit(s)) == s` — so a future parser change that reinterprets a new shape is caught by construction rather than by a fresh per-shape bug.
  - [ ] PROCESS: `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` green (vendored parser/emitter mirrored into plugin payloads).
---

# frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting

## Summary

`emit_frontmatter`'s inline-scalar emitter (`_yaml_inline` in
`goc/engine.py`) decides whether to quote a scalar by re-enumerating, in
several independent hand-maintained predicates, the exact set of value
shapes the vendored parser (`goc/_vendor/yaml_lite.py`) would coerce to a
non-string or reject. Because the emitter's "needs quoting" knowledge is a
*copy* of the parser's "reinterprets this shape" knowledge rather than
*derived* from it, the two keep drifting: every time the parser is hardened
or a new reinterpreted shape is noticed, a fresh per-shape emitter bug lands.
**Eight-plus separate bug cards have now patched this one predicate family
one shape at a time.** That is the missing-abstraction signal — unify the
emitter's quote decision with the parser's behaviour so a new reinterpreted
shape cannot silently round-trip-corrupt or crash.

## What's broken (the recurring shape)

The emitter gates quoting on a disjunction of independent predicates at
`goc/engine.py:248-253`:

```python
if (
    _YAML_NEEDS_QUOTE.search(s)
    or _parser_coerces_scalar(s)              # mirrors parser int/null/bool coercion
    or bool(_YAML_BLOCK_HEADER_RE.match(s))   # mirrors parser block/folded indicators
    or (s and s[0] in _YAML_INDICATOR_FIRST)  # mirrors parser anchor/alias indicators
    or s != s.strip()
):
```

Each clause is a hand-maintained restatement of one parser rule. The parser's
authoritative recognizers live elsewhere (`yaml_lite.py`: `_BLOCK_INDICATOR_RE`,
`_FOLDED_INDICATOR_RE`, the scalar coercion in `_coerce_scalar`, etc.). When
the two restatements disagree, the emitter writes a value bare that the parser
then reinterprets — silent data loss on round-trip, or (once the parser was
hardened to *raise*) a hard `FrontmatterError` crash.

## The family (record axis — instances of this one shape)

All closed (or superseded) `frontmatter-emitter` / `inline-emitter` bugs are
instances of "emitter quote-trigger missed a shape the parser reinterprets":

- [frontmatter-emitter-does-not-quote-empty-string-scalar-that-parses-as-null](../frontmatter-emitter-does-not-quote-empty-string-scalar-that-parses-as-null/)
- [frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values](../frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values/)
- [frontmatter-emitter-does-not-quote-integer-looking-string-scalars](../frontmatter-emitter-does-not-quote-integer-looking-string-scalars/) (superseded)
- [frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values](../frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values/)
- [frontmatter-emitter-leaves-explicit-indent-block-scalar-headers-unquoted](../frontmatter-emitter-leaves-explicit-indent-block-scalar-headers-unquoted/) (pipe forms)
- [frontmatter-emitter-leaves-folded-block-scalar-headers-unquoted](../frontmatter-emitter-leaves-folded-block-scalar-headers-unquoted/) (folded forms — the most recent; the pipe fix shipped the regex with the gap)
- [frontmatter-emitter-writes-float-values-bare-that-parse-back-as-strings](../frontmatter-emitter-writes-float-values-bare-that-parse-back-as-strings/)
- [inline-emitter-writes-multi-line-strings-bare-destroying-subsequent-frontmatter](../inline-emitter-writes-multi-line-strings-bare-destroying-subsequent-frontmatter/)

The pipe→folded pair is the clearest proof of drift: the pipe fix added `\d*`
to one branch of `_YAML_BLOCK_HEADER_RE` and its DoD round-trip test
enumerated only pipe forms, so the folded branch shipped with the same gap and
had to be patched as a *separate* card weeks later.

This is the emitter↔parser axis. It is distinct from
[yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/),
which is about three scanners drifting *within* the parser — same disease
(copied logic instead of one source of truth), different organ.

## Why it matters

`emit_frontmatter` rewrites the whole card on every mutating verb (`status`,
`done`, `wait`, `move`, `decide`, `quality-pass`, …). Any value shape the
emitter forgets to quote but the parser reinterprets is a latent round-trip
bug reachable by any one-shot-authored or pasted card frontmatter. The
per-shape whack-a-mole has a predictable tail: each parser hardening (e.g. the
folded-scalar raise) can convert a previously-silent emitter gap into a hard
crash. A round-trip-derived quote decision closes the whole tail at once.

## Decision required

What factoring makes the emitter's quote decision a function of the parser's
behaviour rather than a hand-maintained twin?

- **Option A — round-trip probe.** Quote `s` iff `parse_scalar(s) != s` (the
  emitter tentatively emits bare, re-parses the single scalar, and quotes when
  the value does not survive). One rule, automatically correct for every
  current and future reinterpreted shape; cost is a per-scalar parse on emit.
- **Option B — shared recognizer module.** Extract the parser's
  reinterpret-this-shape recognizers (`_BLOCK_INDICATOR_RE`,
  `_FOLDED_INDICATOR_RE`, scalar-coercion predicate, indicator-first set) into
  one module the emitter imports for its quote trigger, so there is a single
  definition both sides consume. Cheaper at runtime; still requires the shared
  module to be complete.
- **Option C — keep the per-predicate emitter but add a property test only.**
  A `parse(emit(s)) == s` property test over a broad scalar corpus turns the
  next drift into a red build instead of a shipped bug, without restructuring
  the emitter. Lowest effort; does not remove the duplication, only its
  silence.

Pick one (or a hybrid: C as a guard now, A/B as the structural fix). Record
the choice and rationale in `log.md`, then the card becomes mechanical.
