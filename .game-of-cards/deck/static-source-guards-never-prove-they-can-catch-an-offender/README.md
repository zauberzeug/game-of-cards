---
title: static-source-guards-never-prove-they-can-catch-an-offender
summary: "Four prohibition guards in tests/ scan a source or doc tree and assert the offender list is empty, but none is ever run against source that DOES offend. `assertEqual([], offenders)` passes identically whether the tree is clean or the scanner has quietly stopped matching, so a guard can die silently and still read as 'convention enforced'. Killing each scanner's regex leaves all four green; the two guards in the same suite that do prove their sensitivity go red. The technique needs no invention — only a scope decision on how far to apply it."
status: open
stage: null
contribution: medium
created: "2026-07-27T01:54:03Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [test, meta-fix]
definition_of_done: |
  - [ ] (replace with real criteria once the approach in `## Decision required` is picked)
---

# Static source guards never prove they can catch an offender

## Location

Four prohibition scanners across two test files:

| Guard | Scanner | Prohibited shape |
|---|---|---|
| `tests/test_guidance_accuracy.py:20` | `_STALE_PATTERN` | the stale `close + commit` phrasing |
| `tests/test_guidance_accuracy.py:142` | `_STALE_BICONDITIONAL` | the stale `No ⏳ ⇒ pullable` claim |
| `tests/test_guidance_accuracy.py:216` | `_STALE_STUB` | the stale `reproduce.py stub` phrasing |
| `tests/test_skill_frontmatter_strict_yaml.py:21` | `NESTED_MAPPING_COLON` | a nested mapping in skill frontmatter |

Two guards in the same suite are the counter-examples that show the fix shape
already exists in-tree: `tests/test_plugin_mirror_parity.py` carries five
`*_is_detected` tests that feed synthetic drift to its checker, and
`tests/test_count_message_pluralization.py` gained four such cases when
[count-banners-outside-the-cards-sweep-print-1-boxes-instead-of-1-box](../count-banners-outside-the-cards-sweep-print-1-boxes-instead-of-1-box/)
closed.

## What's broken

A prohibition guard ends in some variant of

```python
        self.assertEqual([], offenders, "…must not appear…")
```

That assertion has two passing states and cannot tell them apart:

1. the scanned tree genuinely contains no offender, and
2. the scanner no longer matches anything at all.

State 2 arises from ordinary maintenance — the prohibited wording is rephrased,
the file the pattern anchors to is restructured, an escape is dropped, the shape
being scanned for acquires a variant the regex cannot express. Nothing in the
suite distinguishes the two, so a guard can stop guarding at any commit and the
only signal is its continued green.

This is not hypothetical. It is the exact failure the count-banner sweep just
cost two cards to repair. That sweep found its fix set with
`\{len\([^)}]*\)\}\s+cards?\b`, fixed the seven sites the regex matched, and
then installed a CI guard using **the same regex**. The guard's reach was by
construction equal to the sweep's reach, so the nine interpolations the scan
could not express — every non-card noun, plus `{len(cluster)} blocked cards`,
where an adjective sits between the count and the noun — were invisible to
both. The guard reported the convention enforced while `goc done` printed
`1 unchecked DoD boxes`, the most-read error string in the tool.

The distinguishing property is **which way the assertion fails**:

- **Fail-open** — `assertEqual([], offenders)`. A dead scanner produces an
  empty list, which is the pass condition. These are the four above.
- **Fail-closed** — `assertEqual(1, len(matches))` in
  `tests/test_engine_module_singletons.py:27`, or the `assertIn` presence
  checks in `tests/test_skill_documents_optional_fields.py`. A dead scanner
  produces zero matches, which is the *fail* condition. These need nothing;
  they are already self-proving and are deliberately excluded from the table.

## Empirical evidence

`reproduce.py` simulates scanner death: for each guard it rewrites the
prohibition pattern to `re.compile("(?!x)x")` — a regex that can never match —
and runs that guard's own tests against the real tree.

```
baseline — every guard passes on the unmodified tree:
  PASS  tests/test_guidance_accuracy.py  (OK)
  PASS  tests/test_skill_frontmatter_strict_yaml.py  (OK)
  PASS  tests/test_count_message_pluralization.py  (OK)

scanner killed — does anything notice?
  STILL GREEN  tests/test_guidance_accuracy.py::_STALE_PATTERN
  STILL GREEN  tests/test_guidance_accuracy.py::_STALE_BICONDITIONAL
  STILL GREEN  tests/test_guidance_accuracy.py::_STALE_STUB
  STILL GREEN  tests/test_skill_frontmatter_strict_yaml.py::NESTED_MAPPING_COLON
  CAUGHT       tests/test_count_message_pluralization.py::HARDCODED_PLURAL

FAIL: 4 prohibition guard(s) keep passing with a dead scanner — they assert an
empty offender list without ever proving the list can be non-empty:
  tests/test_guidance_accuracy.py::_STALE_PATTERN
  tests/test_guidance_accuracy.py::_STALE_BICONDITIONAL
  tests/test_guidance_accuracy.py::_STALE_STUB
  tests/test_skill_frontmatter_strict_yaml.py::NESTED_MAPPING_COLON
```

The baseline line matters: all three files pass unmodified, so `STILL GREEN` is
a statement about the mutation being undetected, not about a broken harness.
The script modifies nothing in the repo — each guard is copied to a temp file
with its `ROOT` rebound to an absolute path, and the mutation is applied to the
copy.

## Why it matters

This repo leans hard on prohibition guards. The deck already carries a long run
of cards whose finding is "the guard's predicate was narrower than the class it
claimed to enforce" — `title-antipattern-guard-misses-math-symbols-and-underscores`,
`openclaw-skill-porter-context-regex-misses-parenthetical-headers`,
`pattern-generalization-opt-out-regex-misses-quoted-yaml-values`,
`auto-commit-guard-misses-paused-rebase-without-rebase-head-marker`, and the six
`pattern-generalization-mutation-detector-skips-…` cards. Every one of those was
found by a human or an audit pass, never by CI, because a guard with a blind
spot is indistinguishable from a guard with nothing to find.

The cost is worse than an unguarded defect, because it is an unguarded defect
plus a false claim of coverage. The count-banner case is the measured example:
the first sweep's closure recorded the convention as enforced, and the nine
surviving sites then needed a second full card — filing, briefing, fix,
review — to find and repair.

`tests/test_guidance_accuracy.py` is the highest-exposure file in the table.
Its own related root card,
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/),
covers a **different** failure mode in the same file — claims that never got a
guard at all. This card covers claims that *have* a guard which may no longer
work. The two are complementary, not duplicates: one is absence, the other is
false presence.

## Decision required

The technique is settled — a test that runs the scanner over synthetic source
carrying a known offender and asserts it is reported. `test_plugin_mirror_parity.py`
and `test_count_message_pluralization.py` both already do it. What needs a human
pick is **how the repo guarantees it**, and the two options differ in whether
they prevent recurrence:

- **A — per-guard sensitivity tests.** Add one `*_is_detected` case beside each
  of the four scanners, mirroring the existing precedent. Smallest diff, no new
  abstraction, matches how the two correct guards are already written. But it is
  opt-in per guard: the fifth prohibition guard someone writes next month is
  unprotected again, and this card's shape recurs — the same trap the sibling
  root cards `doc-accuracy-guards-are-opt-in-per-claim-…`,
  `draft-gating-is-opt-in-per-surface-…` and
  `query-flag-validation-is-opt-in-per-flag-…` all describe.

- **B — a shared harness that makes sensitivity structural.** Guards register
  `(scanner, known-offender-sample)` pairs with a common helper that generates
  both the prohibition assertion and its sensitivity case, plus a meta-test that
  fails when a prohibition scanner exists with no registered sample. Prevents
  recurrence rather than patching four instances; costs a new abstraction and a
  rewrite of guards that currently read as plain, obvious unittest code.

Option B is the shape this repo has reached for before when a family kept
respawning per-site fixes (see `unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes`
and `bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`,
both of which frame the same per-site-versus-at-the-source choice). It is
also the heavier one, and with only four instances the threshold argument cuts
both ways. Whether four is past the line is the call to make.

A secondary question rides along: whether `reproduce.py`'s mutation harness
should itself become a CI test — "kill each prohibition scanner, assert the
suite goes red" is a stronger and more general guarantee than any per-guard
sample, and it needs no registration, but it multiplies suite runtime by the
number of prohibition guards.

## Fix

Deferred to the decision above. Do not start with the four patches: if B is
picked, those patches are thrown away.
