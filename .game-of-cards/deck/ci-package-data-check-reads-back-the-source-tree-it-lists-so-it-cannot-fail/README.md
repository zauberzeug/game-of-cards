---
title: ci-package-data-check-reads-back-the-source-tree-it-lists-so-it-cannot-fail
summary: "ci.yml installs the package editable, then its package-data step checks that every skill listed from goc/templates/skills exists under files('goc.templates'), the same directory, so a hatch exclude that shipped a wheel with 0 of 18 skills passed the step and the whole suite (reproduce.py confirms). Fixed in the suite: tests/test_wheel_package_parity.py builds the distribution with uv build, as release.yml does, and fails when the wheel lacks any tracked goc/ file. The step itself still cannot fail; removing it needs a human commit, tracked by ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel."
status: done
stage: null
contribution: high
created: "2026-09-28T01:38:09Z"
closed_at: "2026-10-04T06:44:44Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, test]
definition_of_done: |
  - [x] TDD: a reproduce.py adds a wheel-level exclude of `goc/templates/skills` in a scratch clone, runs the `Install package`, `Run regression tests` and `Verify package data ships templates` step bodies verbatim under the editable install, then builds the wheel and counts its `SKILL.md` members — exiting 1 while no gate fails because the wheel ships none, 0 once one does, and 2 if the run disproves the hypothesis (the card would then flip to `disproved`)
  - [x] MECHANICAL: a package-data check inspects a built artifact instead of the editable source tree — `tests/test_wheel_package_parity.py` runs `uv build` and lists the wheel's members inside CI's `Run regression tests` step, so the `ci.yml` header's "Package builds cleanly with hatchling" claim is true of that step. It lands as a test because the bot's GITHUB_TOKEN cannot modify `.github/workflows/`; the `Verify package data ships templates` step still reads the source tree back, and replacing it needs a HUMAN commit, tracked by `ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel`
  - [x] MECHANICAL: drop the `unverified` tag once reproduce.py lands
worker: {who: "claude[bot]", where: main}
---

# The CI package-data check reads back the source tree it lists, so it cannot fail

## Status

Verified and fixed in the regression suite on 2026-10-04. The `ci.yml` step
itself is unchanged, because rewriting it is a `.github/workflows/` edit the bot
cannot push. That leftover work is
[ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel](../ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel/)
(`human_gate: session`).

## Location

- `.github/workflows/ci.yml:48`, `run: uv pip install -e .`. This is an
  **editable** install.
- `.github/workflows/ci.yml:58-73`, the `Verify package data ships
  templates` step:
  ```python
  root = files('goc.templates')
  source_skills = sorted(p.name for p in pathlib.Path('goc/templates/skills').iterdir() if (p / 'SKILL.md').is_file())
  for s in source_skills:
      skill_md = root / 'skills' / s / 'SKILL.md'
      assert skill_md.is_file(), f'missing {skill_md}'
  ```
- `.github/workflows/ci.yml:4` and `:7`, the header's promise: "Package
  builds cleanly with hatchling" and "skill templates ship as importable
  package data". Before this card, no CI step ran `uv build`.

## What was broken

Under an editable install, `files('goc.templates')` resolves to the same
`goc/templates/` directory that `source_skills` is listed from. So the
step asserts "every file I just listed from this directory exists in this
directory", which is true by construction. No packaging configuration can
turn it red, whether a hatch `include`/`exclude` change, a package move, or
a `MANIFEST` edit.

Nothing else in CI closed the gap. Every test imports `goc` from the source
tree, and the release path does not check what the wheel contains:

- `release.yml:343` builds the wheel, but `:346-362` only checks the
  wheel's filename version.
- The smoke job installs the built package (`release.yml:502`,
  `uv tool install --force "${{ github.workspace }}"`), then runs only
  the default plugin-mode `goc install`. That path never reads
  `templates/skills/`, and the job asserts only that the deck directory
  exists (`test -d /tmp/smoke-A/.game-of-cards/deck`).

From a wheel with the skills excluded, the filing audit saw both
`goc install --local-skills` and `--agents codex` crash with
`FileNotFoundError: …/site-packages/goc/templates/skills`. The published
0.0.27 wheel is intact (18 of 18 skills). The defect was that nothing would
notice the day it is not. The closed
`prevent-skill-rename-from-breaking-ci-silently` made the skill list
self-derived, which completed the tautology.

## Empirical evidence

`reproduce.py` copies the working tree into a scratch git repo and adds
`exclude = ["goc/templates/skills"]` under
`[tool.hatch.build.targets.wheel]`. It then runs ci.yml's `Install package`,
`Run regression tests` and `Verify package data ships templates` steps
verbatim under a fresh activated venv. Finally it builds with `uv build`, as
`release.yml` does, and counts the wheel's `SKILL.md` members. A test that
fails under the exclude counts only if it passes once the exclude is
reverted.

Before the fix (run on `c72cc011`, without the new test):

```
wheel built under the exclude ships 0 of 18 SKILL.md (game_of_cards-0.0.27.post1.dev0-py3-none-any.whl)
`Run regression tests`: exit 1, 1220 tests, 1 failing
    fails without the exclude too (not counted): test_canonical_tag_rows.CanonicalTagRowsTest.test_live_cards_satisfy_every_state_row
`Verify package data ships templates`: exit 0
    All 18 skills + schema ship as package data.

The package-data step passes while the wheel ships no skills: it cannot fail.
CI IS BLIND: the wheel ships no skills and no gate fails.
```

Exit 1. The uncounted failure is an artifact of the run: that tree still
tags this card `unverified` while the copied `reproduce.py` sits in its
directory, so `test_canonical_tag_rows` fails with or without the exclude.

After the fix:

```
wheel built under the exclude ships 0 of 18 SKILL.md (game_of_cards-0.0.27.post1.dev0-py3-none-any.whl)
`Run regression tests`: exit 1, 1223 tests, 1 failing
    fails because of the exclude: test_wheel_package_parity.WheelPackageParityTest.test_wheel_ships_every_tracked_package_file
`Verify package data ships templates`: exit 0
    All 18 skills + schema ship as package data.

The package-data step passes while the wheel ships no skills: it cannot fail.
CI notices: a gate fails because the wheel ships no skills.
```

Exit 0.

## Fix

`tests/test_wheel_package_parity.py` (3 tests) runs `uv build` from the repo
root. Like `release.yml`, it pins `SETUPTOOLS_SCM_PRETEND_VERSION`. It then
checks that the wheel, built from the sdist, ships every file that
`git ls-files goc` tracks. The reference is the whole tracked package, not a
list of skills, so a dropped module, hook, template or schema copy fails the
same way, including files added later. An sdist-only exclude fails it too.
A second test keeps the check from passing vacuously: the tracked list must
include `goc/__init__.py`, `goc/schema.yaml` and a `SKILL.md`. The test
skips without `uv` on PATH or outside a git checkout, and CI has both. It
takes about 2.5 s.

It lands in the suite rather than in `ci.yml` for the reason AGENTS.md gives
for the OpenClaw porter guard: the autonomous bot's `GITHUB_TOKEN` cannot
edit `.github/workflows/`. CI's `Run regression tests` step runs it on every
matrix leg, so the header's "Package builds cleanly with hatchling" is now
true of that step. `AGENTS.md`'s CI paragraph names the test.

Related:

- [ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel](../ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel/)
  (open, `session`): delete or rewire the step itself.
- [ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card](../ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card/)
  (open, `session`) covers the same header's stale count and dead card
  citation. Its Fix now credits the test rather than the step.

Surfaced by: general-purpose audit hunter (repo scripts and CI
workflows), 2026-09-28.
