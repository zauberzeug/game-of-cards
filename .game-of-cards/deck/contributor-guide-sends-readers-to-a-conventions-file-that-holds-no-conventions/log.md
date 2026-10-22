
## 2026-09-21T05:05:00Z — Closure

- **What changed**: `CONTRIBUTING.md` — all seven tree-restating claim
  groups corrected: conventions routed to `AGENTS.md` instead of the
  eleven-byte `@AGENTS.md` shim (3 sites), 4→6 source files, the payload
  roster widened to name `codex-plugin/` in all three sections that
  discuss it, both `pre-commit run --all-files` comments replaced with
  the four registered hook ids (dropping the formatter that never
  existed), single→double quotes, `goc upgrade` replaced by the
  `sync-plugin-assets` hook as the mirror-refresh mechanism, and the
  release step expanded from "four plugin manifests" to five named
  manifests plus `goc/__init__.py` and the two dogfood surfaces.
  `tests/test_guidance_accuracy.py:ContributorGuideAccuracyTest` pins
  every one of them.
- **Verification**: `reproduce.py` 8 findings → 0 (exit 1 → exit 0); the
  same detector still reports all eight against the pre-fix copy, which
  is why it grew an optional path argument. Each of the seven guard
  checks was mutation-tested in isolation against the repaired file —
  one stale claim reintroduced, exactly one check fires — and the whole
  set fires on the pre-fix wording fed in verbatim. 1172 tests, 0
  failures.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: the contributor on-ramp GitHub links from the issue
  and pull-request forms now agrees with the tree, and is the sixteenth
  surface in the doc-accuracy family to carry a derive-from-tree guard.
- **Tests**: 1172 passed / 0 failed / 0 xfailed.

### Two things the card predicted that did not hold

The Fix section expected five mechanical groups and put the conventions
pointer and the quote rule out of a derive-from-tree guard's reach. Both
turned out reachable once restated as tree questions: "does every
document this guide links to carry prose on the page" catches the
`@`-import shim without encoding anything about it, and the quote rule
grades against the package's own 94-percent majority. So the guard
covers seven groups, not five. What is genuinely unguarded is narrower
than the card drew it: how the guide *describes* AGENTS.md once it
points there.

The card also specified AGENTS.md's prose wording ("sync plugin assets +
goc validate + card language + card YAML") for the two pre-commit
comments. Shipped the hook ids verbatim instead — they are the string
`pre-commit run <id>` takes, and a guard can derive them from
`.pre-commit-config.yaml` where the prose form has no ground truth.

### One detector defect found while flipping it

`reproduce.py`'s quote-style check asserted `double > single` against the
tree alone and never parsed what the guide claimed, so it would have
stayed red after the correction — a check that cannot flip is not a
check. It and the three other wording-pinned checks now read the claim
they grade out of the text, which is also what let the pre-fix copy be
re-run as a fixture.

## Closure verification (2026-09-21T04:47:06Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 8/8 ticked
- [x] log-md-closure-entry — '## 2026-09-21 — Closure' present
