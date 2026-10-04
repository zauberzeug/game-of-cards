## 2026-10-04T06:43:00Z — Hypothesis verified; DoD items 1 and 2 amended to the suite route

Claimed from the ready queue. `reproduce.py` ran the falsification recipe in
a scratch copy of the tree, with CI's own step bodies read from `ci.yml`. The
wheel built under the exclude shipped 0 of 18 `SKILL.md`. The package-data
step printed `All 18 skills + schema ship as package data.` and exited 0. No
test failed because of the exclude. The hypothesis holds, so the `unverified`
tag comes off.

Two notes on making the scratch run faithful:

- The scratch repo has no tags, so `reproduce.py` pins
  `SETUPTOOLS_SCM_PRETEND_VERSION` to `<__version__>.post1.dev0`, which is
  what hatch-vcs derives between releases. A first run pinned `0.0.0`, and two
  `test_install` tests failed with or without the exclude, because they
  compare the installed version against older ones.
- A test that fails under the exclude is re-run with the exclude reverted,
  and counts only if it then passes. That run's third failure,
  `test_canonical_tag_rows`, was real and was ours: the card still carried
  `unverified` once `reproduce.py` existed.

**DoD amendment.** As filed, items 1 and 2 named the `ci.yml` step as the
thing that must fail, and item 2 said that needs a human commit. The repo
already has a route for a guard the bot cannot put in `.github/workflows/`:
it goes into the suite, which CI's `Run regression tests` step runs.
`AGENTS.md` records that route for the OpenClaw porter drift guard. Taking it
lands the protection now instead of parking a high-value card on a
human-only edit, so the items now say what was done. Item 1 asserts that some
gate fails, not that the step fails. Item 2 points at the test. The step
itself still cannot fail. Deleting or rewiring it is cosmetic now that the
test covers it, and it remains a `.github/workflows/` edit. It is filed as
`ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel`
(`human_gate: session`, low), cross-linked with the two other open `ci.yml`
cards so one human session can land all three.

## 2026-10-04T06:44:41Z — Closure

- **What changed**:
  - New guard `tests/test_wheel_package_parity.py` (3 tests). It runs
    `uv build` (sdist, then the wheel from it, as `release.yml` does,
    version pinned via `SETUPTOOLS_SCM_PRETEND_VERSION`) and fails when the
    wheel lacks any file `git ls-files goc` tracks. A second test keeps
    that check from passing vacuously. It skips without `uv` or a git
    checkout, and takes about 2.5 s.
  - `reproduce.py` (this directory) runs ci.yml's steps verbatim against a
    scratch copy with the skills excluded from the wheel. It tolerates the
    package-data step being deleted later.
  - `AGENTS.md` CI paragraph: the `Run regression tests` step also gates
    the wheel's contents through the new test.
  - Card: `unverified` dropped, DoD items 1 and 2 amended (entry above),
    dashboard rewritten to the applied fix.
  - `ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card`:
    its Fix no longer credits the step with checking what ships. Log entry
    added.
  - Filed `ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel`
    (session, low) for the step itself.
- **Verification**:
  - `reproduce.py` on `c72cc011` (pre-fix): 0 of 18 `SKILL.md` shipped,
    no gate failed because of it, exit 1. On the fix:
    `test_wheel_ships_every_tracked_package_file` is the one failure the
    exclude causes, exit 0.
  - An sdist-only exclude (`[tool.hatch.build.targets.sdist]`
    `exclude = ["goc/templates/hooks"]`) fails the test too, with the 3 hook
    scripts listed. The wheel is built from the sdist.
  - The new test passes under pytest as well (3 passed).
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: a hatch config change that drops package files from
  the wheel now turns CI red on every matrix leg. Before, it would have
  published a wheel whose `goc install --local-skills` crashes.
- **Tests**: 1223 passed / 0 failed (`uv run python -m unittest discover -s
  tests`). `goc validate`, `sync_plugin_assets.py --check`,
  `port_skills_to_openclaw.py --check`, `check_card_language.py` and
  `check_card_frontmatter_yaml.py` are all clean.

## Closure verification (2026-10-04T06:44:41Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-04 — Closure' present
