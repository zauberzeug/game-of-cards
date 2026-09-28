---
title: ci-package-data-check-reads-back-the-source-tree-it-lists-so-it-cannot-fail
summary: "UNVERIFIED. ci.yml installs the package editable, then checks that every skill listed from goc/templates/skills exists under files('goc.templates'), which under an editable install is that same directory, so no packaging change can turn the step red; ci.yml never builds the wheel its header says builds cleanly. A hatch exclude that ships a wheel with zero skills passes CI and the whole suite, while goc install --local-skills from that wheel crashes."
status: open
stage: null
contribution: high
created: "2026-09-28T01:38:09Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, test, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py adds a wheel-level exclude of `goc/templates/skills` in a scratch clone, runs the `Verify package data ships templates` step body verbatim under the editable install, then builds the wheel and counts its `SKILL.md` members — asserting the step fails when the wheel ships none, or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] MECHANICAL: the package-data check inspects a built artifact (e.g. `uv build --wheel` then list the wheel's members, or install the wheel into a clean venv and resolve `files('goc.templates')` there) instead of the editable source tree; the `ci.yml` header's "Package builds cleanly with hatchling" claim is true of some step (requires a HUMAN commit — the bot's GITHUB_TOKEN cannot modify `.github/workflows/`)
  - [ ] MECHANICAL: drop the `unverified` tag once reproduce.py lands
---

# The CI package-data check reads back the source tree it lists, so it cannot fail

> **UNVERIFIED.** Surfaced by an audit hunter on the repo-scripts-and-CI
> seam on 2026-09-28. The filing agent re-read and confirmed the
> citations. No `reproduce.py` was written this round; the falsification
> recipe is below.

## Location

- `.github/workflows/ci.yml:48`, `run: uv pip install -e .`. This is an
  **editable** install.
- `.github/workflows/ci.yml:58-72`, the `Verify package data ships
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
  package data". `AGENTS.md:38` calls `ci.yml` "a build + console-script
  + regression-test + `goc validate` matrix". `ci.yml` never runs
  `uv build`.

## Hypothesis

Under an editable install, `files('goc.templates')` resolves to the same
`goc/templates/` directory that `source_skills` is listed from. So the
step asserts "every file I just listed from this directory exists in this
directory", which is true by construction. No packaging configuration can
turn it red. That includes a hatch `include`/`exclude` change, a package
move, or a `MANIFEST` edit.

The release path does not close the gap:

- `release.yml:343` builds the wheel, but `:346-362` only checks the
  wheel's filename version.
- The smoke job installs the built package (`release.yml:502`,
  `uv tool install --force "${{ github.workspace }}"`), then runs only
  the default plugin-mode `goc install`. That path never reads
  `templates/skills/`, and the job asserts only that the deck directory
  exists (`test -d /tmp/smoke-A/.game-of-cards/deck`).

The hunter's scratch clone added `exclude = ["goc/templates/skills"]`
under `[tool.hatch.build.targets.wheel]`:

- The CI step body printed `All 18 skills + schema ship as package data.`
  and exited 0.
- The full suite passed: `Ran 1197 tests … OK`.
- `uv build --wheel` produced a wheel with 0 `SKILL.md` files.
- From that wheel, `goc install --local-skills` and `--agents codex` both
  crashed with `FileNotFoundError: …/site-packages/goc/templates/skills`.

The published 0.0.27 wheel is intact (18 of 18 skills). The defect is
that nothing would notice the day it is not.

## Why deferred

The citations are confirmed. No `reproduce.py` is committed this round.
The fix edits `.github/workflows/`, which the autonomous bot cannot
commit, so it needs a human commit.

Related:
[ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card](../ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card/)
(open) covers the same header's stale count and dead card citation, not
whether the step can fail. The closed
`prevent-skill-rename-from-breaking-ci-silently` made the skill list
self-derived, which completed the tautology.

## Falsification recipe

In a scratch clone, add the hatch exclude above, run
`uv pip install -e .`, then paste the step body. If it fails, the
hypothesis is disproved.

Surfaced by: general-purpose audit hunter (repo scripts and CI
workflows), 2026-09-28.
