
## 2026-07-26T08:25:00Z — Connected to its generalization (not a new root)

Stop-hook pattern check on the filing turn asked whether the change touched a
pattern with broader applicability. It did. Deduped against the deck first: a
root card already exists —
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)
— so this instance was connected to it rather than duplicated into a second
umbrella. Cross-reference, no `advances` edge: the root closes on its own
deliverable, making it a governing cluster rather than an aggregation epic
(same call recorded on the sixth instance).

Both of this card's claims match shapes the root enumerates (bare count in
prose; forward-looking promise with no expiry or owner). The root's instance
table and count were updated in place, and its `log.md` records the one thing
this instance adds beyond a tally: workflow-file comments are a doc surface
its Option A sweep list does not cover.

## 2026-10-04 — Fix section no longer credits the package-data step

[ci-package-data-check-reads-back-the-source-tree-it-lists-so-it-cannot-fail](../ci-package-data-check-reads-back-the-source-tree-it-lists-so-it-cannot-fail/)
showed that the `Verify package data ships templates` step reads back the
editable source tree, so it passes on a wheel that ships no skills. The Fix
section credited that step with the invariant the header should state. It now
credits `tests/test_wheel_package_parity.py`, which builds the wheel. It also
links
[ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel](../ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel/),
which removes or rewires the step and needs the same human session. The DoD is
unchanged.

## 2026-10-22T06:00:43Z: decision recorded

No hard-coded skill count in the ci.yml header: it states the invariant and the package-data step derives the list from the filesystem — Workflow chore under the bulk rule the maintainer approved in a human session on 2026-10-22; b81ab4ab already rewrote the header this way. Gate session → none.

## 2026-10-22T06:01:12Z — Closure

- **What changed**: `.github/workflows/ci.yml` header (b81ab4ab, the C1 fix) — it now lists what the workflow confirms without a hard-coded skill count ("Every skill template under goc/templates/skills/ ships as importable package data") and cites no card.
- **Verification**: `sed -n '1,12p' .github/workflows/ci.yml` — no number, no forward-looking sentence, no card reference.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: n/a (comment-only change).

## Closure verification (2026-10-22T06:01:12Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-22 — Closure' present
