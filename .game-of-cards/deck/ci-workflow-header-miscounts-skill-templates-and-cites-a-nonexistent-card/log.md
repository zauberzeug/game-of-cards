
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
