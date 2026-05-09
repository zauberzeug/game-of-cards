"""Regression guard: validate_plugin_mirror_parity detects claude-plugin/ and openclaw-plugin/ drift.

Patches goc.engine.REPO_ROOT directly so the test never spawns a subprocess and
never risks shadowing the real goc package via Python's cwd-first import search.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import goc.engine as eng

ROOT = Path(__file__).resolve().parents[1]


def _check(cwd: Path) -> list[str]:
    old = eng.REPO_ROOT
    try:
        eng.REPO_ROOT = cwd
        return eng.validate_plugin_mirror_parity()
    finally:
        eng.REPO_ROOT = old


def _sync_tree(cwd: Path, skill_content: str = "# test skill\n", hook_content: str = "# hook\n") -> None:
    """Populate a minimal in-sync plugin mirror structure under cwd.

    Source-of-truth lives under `goc/templates/`. The plugin payload mirrors
    skills to the *flat* `claude-plugin/skills/`, the deck hooks to the
    flat `claude-plugin/hooks/`, and (because the bundled engine derives
    its hook list from `templates/hooks/*.py` at runtime) ALSO carries the
    hook files inside `claude-plugin/goc/templates/hooks/`. Only
    `templates/skills/` is excluded from the deep mirror — the bundled
    engine refuses `--local-skills` so it never reads skill bodies.
    """
    # pair 1: goc/templates/skills ↔ claude-plugin/skills
    for base in (
        cwd / "goc" / "templates" / "skills" / "foo-skill",
        cwd / "claude-plugin" / "skills" / "foo-skill",
    ):
        base.mkdir(parents=True, exist_ok=True)
        (base / "SKILL.md").write_text(skill_content)

    # Deck hook files mirrored to BOTH the flat claude-plugin/hooks/ (used
    # by Claude Code's hook runtime) AND the deep claude-plugin/goc/templates/hooks/
    # (used by the bundled engine to enumerate hooks). The validator derives
    # the pair list from goc/templates/hooks/*.py.
    for hook in ("deck_prompt_router.py", "deck_session_start.py"):
        for base in (
            cwd / "goc" / "templates" / "hooks",
            cwd / "claude-plugin" / "hooks",
            cwd / "claude-plugin" / "goc" / "templates" / "hooks",
        ):
            base.mkdir(parents=True, exist_ok=True)
            (base / hook).write_text(hook_content)

    # Final pair: minimal goc/ ↔ claude-plugin/goc/ shell so the directory
    # comparison has matching non-excluded structure on both sides.
    package_init = "# goc package\n"
    for base in (cwd / "goc", cwd / "claude-plugin" / "goc"):
        base.mkdir(parents=True, exist_ok=True)
        (base / "__init__.py").write_text(package_init)


class PluginMirrorParityTest(unittest.TestCase):
    def test_no_plugin_dir_skips_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([], _check(Path(tmp)))

    def test_in_sync_mirrors_produce_no_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _sync_tree(cwd)
            self.assertEqual([], _check(cwd))

    def test_drifted_skills_mirror_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _sync_tree(cwd)

            # deliberately break pair 1 (skills mirror)
            (cwd / "claude-plugin" / "skills" / "foo-skill" / "SKILL.md").write_text("# drifted\n")

            errors = _check(cwd)
            self.assertEqual(1, len(errors), msg=f"expected 1 error, got: {errors}")
            self.assertIn("plugin mirror drift", errors[0])
            self.assertIn("foo-skill", errors[0])
            self.assertIn("SKILL.md", errors[0])
            self.assertIn("differs", errors[0])

    def test_missing_plugin_skills_dir_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            # only create source, not the mirror
            (cwd / "goc" / "templates" / "skills" / "foo-skill").mkdir(parents=True)
            (cwd / "goc" / "templates" / "skills" / "foo-skill" / "SKILL.md").write_text("# skill\n")
            (cwd / "claude-plugin").mkdir(parents=True)  # plugin root exists but skills missing

            errors = _check(cwd)
            self.assertTrue(any("claude-plugin/skills" in e and "missing" in e for e in errors),
                            msg=f"expected missing-dir error, got: {errors}")

    def test_real_repo_passes(self) -> None:
        errors = _check(ROOT)
        self.assertEqual([], errors, msg=f"plugin mirror drift in the repo itself: {errors}")

    def test_drift_inside_excluded_subpaths_is_ignored(self) -> None:
        """The bundled engine's deep mirror deliberately omits
        `templates/skills/`. Drift inside that excluded path must not be
        reported — it is outside the mirror contract.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _sync_tree(cwd)

            # Re-introduce content in the excluded skills path inside the
            # bundled engine's mirror. This must not be reported.
            (cwd / "claude-plugin" / "goc" / "templates" / "skills" / "stale-skill").mkdir(parents=True)
            (cwd / "claude-plugin" / "goc" / "templates" / "skills" / "stale-skill" / "SKILL.md").write_text("# stale\n")

            self.assertEqual([], _check(cwd))


class OpenClawPluginMirrorTest(unittest.TestCase):
    """OpenClaw plugin only mirrors the goc/ engine — skills are hand-ported,
    hooks live in TypeScript inside index.ts. The parity check must cover
    the engine mirror but ignore everything else.
    """

    def test_in_sync_openclaw_engine_produces_no_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            package_init = "# goc package\n"
            for base in (cwd / "goc", cwd / "openclaw-plugin" / "goc"):
                base.mkdir(parents=True, exist_ok=True)
                (base / "__init__.py").write_text(package_init)
            self.assertEqual([], _check(cwd))

    def test_drifted_openclaw_engine_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            for base in (cwd / "goc", cwd / "openclaw-plugin" / "goc"):
                base.mkdir(parents=True, exist_ok=True)
                (base / "__init__.py").write_text("# goc package\n")
            # Drift the openclaw mirror.
            (cwd / "openclaw-plugin" / "goc" / "__init__.py").write_text("# drifted\n")
            errors = _check(cwd)
            self.assertEqual(1, len(errors), msg=f"expected 1 error, got: {errors}")
            self.assertIn("openclaw-plugin/goc", errors[0])
            self.assertIn("differs", errors[0])

    def test_pattern_generalization_hook_excluded_from_openclaw_mirror(self) -> None:
        """OpenClaw reimplements pattern_generalization_check.py in TypeScript,
        so the source-of-truth file is excluded from the openclaw-plugin/goc
        comparison. Drift inside that path must NOT be flagged.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            # Mirror a minimal templates/ tree on both sides so the directory
            # comparison has matching non-excluded structure. Then add the
            # excluded hook only on the source side.
            for base in (cwd / "goc", cwd / "openclaw-plugin" / "goc"):
                base.mkdir(parents=True, exist_ok=True)
                (base / "__init__.py").write_text("# goc package\n")
                (base / "templates").mkdir(parents=True, exist_ok=True)
                (base / "templates" / "AGENTS_GOC.md").write_text("# agents\n")
                (base / "templates" / "hooks").mkdir(parents=True, exist_ok=True)
            # Excluded path: present in source, absent from mirror — this is
            # the canonical openclaw-only exclusion case.
            (cwd / "goc" / "templates" / "hooks" / "pattern_generalization_check.py").write_text("# real hook\n")
            self.assertEqual([], _check(cwd))


if __name__ == "__main__":
    unittest.main()
