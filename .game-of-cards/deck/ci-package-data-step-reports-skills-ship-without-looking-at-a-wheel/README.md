---
title: ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel
summary: "ci.yml's Verify package data ships templates step lists the skills under goc/templates/skills and checks each one exists under files('goc.templates'), which under CI's editable install is the same directory, so it prints that all 18 skills ship without ever looking at a wheel. The real check now runs in the suite (tests/test_wheel_package_parity.py builds the wheel with uv build), leaving the step as a pass that cannot fail beside it. Deleting or rewiring it is a .github/workflows/ edit the bot's GITHUB_TOKEN cannot push."
status: open
stage: null
contribution: low
created: "2026-10-04T06:39:54Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [bug, infra, test]
definition_of_done: |
  - [ ] MECHANICAL: `.github/workflows/ci.yml` has no step that checks package data by reading `files('goc.templates')` from the editable install. Delete the `Verify package data ships templates` step, or rewrite it to inspect a built artifact. Pushed by a human-credentialed session (the bot's GITHUB_TOKEN cannot modify `.github/workflows/`)
  - [ ] TDD: `.game-of-cards/deck/ci-package-data-check-reads-back-the-source-tree-it-lists-so-it-cannot-fail/reproduce.py` still exits 0 and no longer prints "The package-data step passes while the wheel ships no skills: it cannot fail."
---

# The CI package-data step reports that every skill ships without looking at a wheel

## Location

- `.github/workflows/ci.yml:47-48`, `Install package`: `uv pip install -e .`,
  an **editable** install.
- `.github/workflows/ci.yml:58-73`, `Verify package data ships templates`:

  ```python
  root = files('goc.templates')
  source_skills = sorted(p.name for p in pathlib.Path('goc/templates/skills').iterdir() if (p / 'SKILL.md').is_file())
  for s in source_skills:
      skill_md = root / 'skills' / s / 'SKILL.md'
      assert skill_md.is_file(), f'missing {skill_md}'
  ...
  print(f'\nAll {len(source_skills)} skills + schema ship as package data.')
  ```

## What's broken

Under an editable install, `files('goc.templates')` is the checkout's
`goc/templates/`, the same directory `source_skills` is listed from. The
step asserts that every file it just listed exists where it listed it, then
prints `All 18 skills + schema ship as package data.` No packaging change can
make it fail, because no wheel is involved.

That gap is now closed elsewhere.
[ci-package-data-check-reads-back-the-source-tree-it-lists-so-it-cannot-fail](../ci-package-data-check-reads-back-the-source-tree-it-lists-so-it-cannot-fail/)
added `tests/test_wheel_package_parity.py`. The test runs `uv build` (the
sdist, then the wheel from it, as `release.yml` does) and fails when the
wheel is missing any tracked `goc/` file. CI's `Run regression tests` step
runs it on every matrix leg. It went into the suite because the bot cannot
edit `.github/workflows/`. The step itself is unchanged, so it is what this
card is about.

## Empirical evidence

The parent card's `reproduce.py`, after the test landed. It copies the tree
to a scratch repo, excludes `goc/templates/skills` from the hatch wheel
target, and runs the CI steps verbatim:

```
wheel built under the exclude ships 0 of 18 SKILL.md (game_of_cards-0.0.27.post1.dev0-py3-none-any.whl)
`Run regression tests`: exit 1, 1223 tests, 1 failing
    fails because of the exclude: test_wheel_package_parity.WheelPackageParityTest.test_wheel_ships_every_tracked_package_file
`Verify package data ships templates`: exit 0
    All 18 skills + schema ship as package data.

The package-data step passes while the wheel ships no skills: it cannot fail.
CI notices: a gate fails because the wheel ships no skills.
```

## Why it matters

The step protects nothing, but it puts a false assurance in every CI log. A
reader auditing what CI covers finds a step named for the check, and a
success line, while the real check sits in a test file the workflow never
names. Someone tidying the suite could reasonably delete
`test_wheel_package_parity.py` as a duplicate of the step. That would reopen
the original hole: a wheel that ships no skills passes CI, and
`goc install --local-skills` from it crashes.

## Fix

Delete the step (`ci.yml:58-73`). The wheel test already covers it. The
alternative, rewriting the step to list a built wheel's members, works too,
but it duplicates the test.

Three open cards edit `ci.yml` and need the same human session, so land them
together:
[ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card](../ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card/)
rewrites the header bullet that describes this step, and
[ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory](../ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory/)
fixes the validate step's dead path guard.

**The gate is `session`, not `none`, because the file is under
`.github/workflows/`.** The autonomous bot's `GITHUB_TOKEN` cannot push there.
`AGENTS.md` records the constraint, and the rejected push is in
`ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory`'s
`log.md`. A `pull-card` session that claimed this at gate `none` would do the
work and then fail to push it.
