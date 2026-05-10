---
title: regression-tests-fail-on-stale-install-behavior-assertions
summary: "Every push and pull-request CI run since 2026-05-09 has been red on `tests/test_install.py`. Three closed cards that landed today changed install-time behavior but did not update the test suite: (a) `kickoff-asks-where-goc-briefing-lives` unified the briefing target so install appends only to one of `AGENTS.md`/`CLAUDE.md`/`CLAUDE.local.md` (default AGENTS.md), but assertions for `claude append CLAUDE.md` still expect the old per-agent guidance write; (b) the in-flight `automate-version-bumping-from-git-tag-at-release-time` work made the git tag the source of truth via a build-time literal rewrite, but `goc.__version__` is still the unrewritten static literal `0.0.12` at HEAD while `_goc_version()` test helper resolves dynamically via `importlib.metadata`, producing a mismatch; (c) Stage 4 strip-snippet contract drift after kickoff edits dropped the `python3 - <<'PY' <file>` heredoc the test reads. Ten test methods fail across the 3.10/3.11/3.12/3.13 matrix, blocking every CI signal."
status: done
stage: null
contribution: medium
created: 2026-05-10
closed_at: 2026-05-10
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] `goc.__version__` derives at runtime via `importlib.metadata.version("game-of-cards")` with the static literal as fallback (commit `c38f728`); editable installs and CI now see the same value `_goc_version()` resolves to. Side effect on `tests/test_version_surfaces.py`: switched from `goc.__version__` to a `_static_version()` helper that reads the literal directly, so the cross-manifest equality check still compares static-to-static.
  - [x] `tests/test_install.py` `claude append CLAUDE.md` assertions (lines 56, 300, 377) updated to match the new briefing-target output (`shared append AGENTS.md`).
  - [x] `tests/test_install.py` `assertTrue((cwd / "CLAUDE.md").is_file())` assertions inverted to `assertFalse` for the default-briefing-target paths; the local-skills smoke also drops the `Skill(...)` substring check that depended on CLAUDE.md briefing.
  - [x] `KickoffStage4StripSnippetTest` strip-* tests deleted (the heredoc was retired in `78db285` when the briefing-target was unified). Kept the regression-prevention tests (`test_install_no_longer_accepts_no_claude_md_flag`, `test_skill_body_no_longer_references_removed_flags`).
  - [x] `uv run python -m unittest discover -s tests` passes locally with 0 failures except `test_board_and_open_queue_surface_active_cards`, which is git-config-dependent (fails when `git config user.name` is long enough to truncate the title in board view) and was passing in CI before this card too.
  - [x] CI green on the next push to main: run `25633873149` ✓ all 4 Python matrix jobs pass (3.10, 3.11, 3.12, 3.13).
  - [x] `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# regression-tests-fail-on-stale-install-behavior-assertions

## Evidence

- Failing run example: <https://github.com/zauberzeug/game-of-cards/actions/runs/25630091398> (push event on `b26f96e`, every Python matrix job fails the same way)
- Most-recent failing run: <https://github.com/zauberzeug/game-of-cards/actions/runs/25633403183> (push of the ClawHub fix commit `0bb0709`, same failure mode — confirms the regression is not introduced by today's fix work)
- Last green CI run: not visible in the latest 6 runs — every recent push has been red

## Failure clusters

### Cluster A — version literal vs `importlib.metadata` divergence (~3 tests)

`goc/__init__.py:7` is `__version__ = "0.0.12"` — a Python literal that `release_rewrite_versions.py` rewrites at build time. In editable installs the literal stays at `0.0.12`. The test helper `_goc_version()` (line 1084) reads `importlib.metadata.version("game-of-cards")`, which hatch-vcs resolves dynamically from `git describe --tags`, returning e.g. `0.0.13.post1.dev6`. The two diverge whenever the latest tag is anything other than `v0.0.12`.

### Cluster B — briefing-target test assertions stale (~5 tests)

The closed card `kickoff-asks-where-goc-briefing-lives` (closed 2026-05-10) unified the briefing target: install now appends to ONE briefing file (default `AGENTS.md`), not to both `AGENTS.md` and `CLAUDE.md`. Tests still assert the old plan output. Specific drift:

- `test_no_flag_install_defaults_to_claude_plugin_path` (line 56): asserts `claude append CLAUDE.md` in plan; new plan has `shared append AGENTS.md`.
- `test_default_install_creates_project_state_and_guidance_but_no_harness` (line 65): asserts `(cwd / "CLAUDE.md").is_file()`; new install only creates AGENTS.md by default.
- `test_local_skills_smoke_creates_valid_deck_with_skills` (line 213), `test_mixed_claude_codex_install_vendors_codex_not_claude` (line 284): same dual-file assertion.
- `test_mixed_dry_run_shows_codex_harness_not_claude_harness` (line 300), `test_default_plugin_path_dry_run_shows_only_project_state_and_guidance` (line 377): assert `claude append CLAUDE.md` in plan.

### Cluster C — strip-snippet heredoc contract drift (~3 tests)

`KickoffStage4StripSnippetTest._strip_snippet()` searches the kickoff skill body for the marker `python3 - <<'PY' <file>\n`. After the closed card `split-claude-specific-content-out-of-generic-kickoff-skill` and related kickoff edits, the marker is no longer present.

- `test_strip_deletes_install_only_agents_md`: fails with `Stage 4 strip snippet heredoc missing from skill body`.
- `test_strip_deletes_install_only_claude_md`: `False is not true` (depends on strip running successfully).
- `test_strip_is_idempotent_on_missing_file`: same family.

## Fix path

1. **Cluster A**: edit `goc/__init__.py` to derive `__version__` from `importlib.metadata.version("game-of-cards")` with the static literal as fallback. The release-build rewrite continues to update the literal, so wheel + metadata always agree at release time. Editable-install path now resolves to the same dynamic value the test helper sees.
2. **Cluster B**: walk the failing assertions and update them to match the new briefing-target contract. Where a test asserts both `AGENTS.md` and `CLAUDE.md` exist post-install, drop the CLAUDE.md half. Where the dry-run plan check expects `claude append CLAUDE.md`, update to `shared append AGENTS.md`.
3. **Cluster C**: re-read the current kickoff skill body, locate the new strip-snippet heredoc (if it still exists), update the marker. If the heredoc was retired entirely, delete the dependent tests with a log entry explaining the contract change.

## Out of scope

- The unrelated v0.0.14 ClawHub publish failure (the reusable workflow's stale-package.json bug). Tracked separately if/when filed.
- Adding new test coverage for the new briefing-target flag (`--briefing-target`); coverage in `kickoff-asks-where-goc-briefing-lives` already satisfies that DoD.
- Refactoring the `release_rewrite_versions.py` script.
