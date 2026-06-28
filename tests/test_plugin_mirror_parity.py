"""Regression guard: validate_plugin_mirror_parity detects claude-plugin/ and openclaw-plugin/ drift.

Patches goc.engine.REPO_ROOT directly so the test never spawns a subprocess and
never risks shadowing the real goc package via Python's cwd-first import search.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import goc.engine as eng

ROOT = Path(__file__).resolve().parents[1]


def _load_porter():
    """Import scripts/port_skills_to_openclaw.py without putting scripts/ on sys.path."""
    spec = importlib.util.spec_from_file_location(
        "_goc_openclaw_porter", ROOT / "scripts" / "port_skills_to_openclaw.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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

    def test_same_length_same_mtime_drift_is_detected(self) -> None:
        """Regression: a hand-edit that preserves length and mtime must still
        be flagged. `filecmp.dircmp`'s default `shallow=True` would report
        such a pair as identical; the engine's directory walk uses
        `_DeepDircmp` to force content comparison so the verdict matches
        `scripts/sync_plugin_assets.py --check`.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _sync_tree(cwd)

            src = cwd / "goc" / "__init__.py"
            dst = cwd / "claude-plugin" / "goc" / "__init__.py"

            # Same length, different content, same mtime — the exact
            # signature a shallow `filecmp.dircmp` walks past silently.
            replacement = "X" * len(src.read_text())
            dst.write_text(replacement)
            self.assertEqual(src.stat().st_size, dst.stat().st_size)
            stamp = 1_735_689_600  # 2025-01-01T00:00:00Z
            os.utime(src, (stamp, stamp))
            os.utime(dst, (stamp, stamp))

            errors = _check(cwd)
            self.assertTrue(
                any("claude-plugin/goc" in e and "__init__.py" in e and "differs" in e for e in errors),
                msg=f"expected same-length/same-mtime content drift to be flagged, got: {errors}",
            )

    def test_stale_hook_file_in_claude_plugin_hooks_is_drift(self) -> None:
        """A dst-only hook file (its template was renamed or retired) must
        register as drift. The hook mirror used to be per-file pairs
        enumerated from the CURRENT template set, which made stale copies
        invisible; the dir comparison closes that blind spot.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _sync_tree(cwd)
            (cwd / "claude-plugin" / "hooks" / "retired_hook.py").write_text("# stale\n")

            errors = _check(cwd)
            self.assertTrue(
                any(
                    "claude-plugin/hooks" in e
                    and "retired_hook.py" in e
                    and "only in" in e
                    for e in errors
                ),
                msg=f"expected dst-only stale hook to be flagged, got: {errors}",
            )

    def test_hand_maintained_hooks_json_is_not_drift(self) -> None:
        """`hooks.json` is plugin config with no template counterpart — its
        presence in claude-plugin/hooks/ must not be reported as drift.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _sync_tree(cwd)
            (cwd / "claude-plugin" / "hooks" / "hooks.json").write_text("{}\n")
            self.assertEqual([], _check(cwd))

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


class CodexHookMirrorTest(unittest.TestCase):
    """codex-plugin/hooks/ is the same whole-directory mirror of
    goc/templates/hooks/ as the claude one: a dst-only stale hook is drift,
    the hand-maintained hooks.json is not.
    """

    @staticmethod
    def _codex_tree(cwd: Path) -> None:
        hook_content = "# hook\n"
        # Source of truth: package shell + one skill + one hook template.
        (cwd / "goc" / "templates" / "skills" / "foo-skill").mkdir(parents=True)
        (cwd / "goc" / "templates" / "skills" / "foo-skill" / "SKILL.md").write_text("# skill\n")
        (cwd / "goc" / "templates" / "hooks").mkdir(parents=True)
        (cwd / "goc" / "templates" / "hooks" / "deck_prompt_router.py").write_text(hook_content)
        (cwd / "goc" / "__init__.py").write_text("# goc package\n")
        # Codex payload: skills (no frontmatter → ported verbatim), flat hooks,
        # deep engine mirror (templates/skills excluded from it).
        (cwd / "codex-plugin" / "skills" / "foo-skill").mkdir(parents=True)
        (cwd / "codex-plugin" / "skills" / "foo-skill" / "SKILL.md").write_text("# skill\n")
        (cwd / "codex-plugin" / "hooks").mkdir(parents=True)
        (cwd / "codex-plugin" / "hooks" / "deck_prompt_router.py").write_text(hook_content)
        (cwd / "codex-plugin" / "goc" / "templates" / "hooks").mkdir(parents=True)
        (cwd / "codex-plugin" / "goc" / "templates" / "hooks" / "deck_prompt_router.py").write_text(hook_content)
        (cwd / "codex-plugin" / "goc" / "__init__.py").write_text("# goc package\n")

    def test_in_sync_codex_tree_produces_no_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._codex_tree(cwd)
            (cwd / "codex-plugin" / "hooks" / "hooks.json").write_text("{}\n")
            self.assertEqual([], _check(cwd))

    def test_stale_hook_file_in_codex_plugin_hooks_is_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._codex_tree(cwd)
            (cwd / "codex-plugin" / "hooks" / "retired_hook.py").write_text("# stale\n")

            errors = _check(cwd)
            self.assertTrue(
                any(
                    "codex-plugin/hooks" in e
                    and "retired_hook.py" in e
                    and "only in" in e
                    for e in errors
                ),
                msg=f"expected dst-only stale hook to be flagged, got: {errors}",
            )


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


class OpenClawSkillPortDriftTest(unittest.TestCase):
    """OpenClaw skills are hand-ported (not byte-for-byte synced like claude/codex),
    so the engine sync tripwire does not cover them. This guard asserts the
    committed ports match a fresh re-port — a template edit that was not
    propagated by `scripts/port_skills_to_openclaw.py` turns this test red.
    """

    def test_committed_ports_match_fresh_render(self) -> None:
        porter = _load_porter()
        drifted = porter.drifted_skills()
        rel = [str(p.relative_to(ROOT)) for p in drifted]
        self.assertEqual(
            [], rel,
            msg="openclaw-plugin/skills/ drifted from goc/templates/skills/; "
                "run `python scripts/port_skills_to_openclaw.py` and commit: " + ", ".join(rel),
        )

    def test_render_detects_a_stale_skill(self) -> None:
        """The equality the guard relies on must actually discriminate: a stale
        ported copy (fresh render plus an extra line) must not compare equal.
        """
        porter = _load_porter()
        sample = porter._portable_skill_dirs()[0] / "SKILL.md"
        fresh = porter.render_skill(sample)
        stale = fresh + "\n<!-- deliberately stale -->\n"
        self.assertNotEqual(fresh, stale)

    def test_porter_is_idempotent(self) -> None:
        """Rendering is deterministic — re-rendering every portable skill yields
        byte-identical output, so `--check` after a re-port is always green.
        """
        porter = _load_porter()
        for skill_dir in porter._portable_skill_dirs():
            src = skill_dir / "SKILL.md"
            self.assertEqual(porter.render_skill(src), porter.render_skill(src))

    @staticmethod
    def _sandboxed_porter(tmp: Path):
        """Load the porter with SRC_DIR/DST_DIR/ROOT redirected into a sandbox
        copy of the real skill trees, so prune/drift tests never mutate the
        repo."""
        porter = _load_porter()
        src = tmp / "src"
        dst = tmp / "dst"
        shutil.copytree(ROOT / "goc" / "templates" / "skills", src)
        shutil.copytree(ROOT / "openclaw-plugin" / "skills", dst)
        porter.SRC_DIR = src
        porter.DST_DIR = dst
        porter.ROOT = tmp  # main()'s progress prints are ROOT-relative
        return porter, src, dst

    def test_empty_orphan_subdir_pruned_and_flagged(self) -> None:
        """A nested source sibling subdir that is removed must leave no empty
        orphan dir in the port, and `drifted_skills()` must flag such an
        orphan while it lingers. Regression for the porter's nested-subdir
        equivalent of the sync-side empty-orphan-dir fix.
        """
        with tempfile.TemporaryDirectory() as tmp:
            porter, src, dst = self._sandboxed_porter(Path(tmp))
            skill = porter._portable_skill_dirs()[0]
            dst_skill = dst / skill.name

            # Seed a nested sibling subdir and a sibling kept-dir with 2 files.
            (skill / "extra").mkdir()
            (skill / "extra" / "asset.txt").write_text("nested\n", encoding="utf-8")
            (skill / "kept").mkdir()
            (skill / "kept" / "a.txt").write_text("a\n", encoding="utf-8")
            (skill / "kept" / "b.txt").write_text("b\n", encoding="utf-8")
            porter.main([])
            self.assertTrue((dst_skill / "extra" / "asset.txt").is_file())
            self.assertTrue((dst_skill / "kept" / "a.txt").is_file())

            # Remove the nested source subdir and one file from the kept subdir.
            shutil.rmtree(skill / "extra")
            (skill / "kept" / "b.txt").unlink()
            porter.main([])

            # The emptied subdir must be gone; the still-populated one stays.
            self.assertFalse(
                (dst_skill / "extra").exists(),
                msg="empty orphan subdir lingered after re-port",
            )
            self.assertTrue((dst_skill / "kept" / "a.txt").is_file())
            self.assertFalse((dst_skill / "kept" / "b.txt").exists())

            # A bare empty dst-only subdir (no source, no file) must be flagged.
            ghost = dst_skill / "ghost"
            ghost.mkdir()
            drifted = porter.drifted_skills()
            self.assertTrue(
                any("ghost" in p.relative_to(dst).parts for p in drifted),
                msg=f"drifted_skills() missed a bare empty orphan dir: {drifted}",
            )

    def test_every_context_section_carries_host_neutral_guidance(self) -> None:
        """Every source skill with a `## Context` heading must produce a port
        whose Context section contains the host-neutral guidance paragraph.

        Catches the next "regex too narrow" variant of the parenthetical-header
        drift — if a new heading shape (e.g. `## Context — qualifier`) escapes
        `CONTEXT_BLOCK_RE`, the port falls through to bare backticks and this
        test fails.
        """
        porter = _load_porter()
        marker = "Before running the body of this skill"
        offenders: list[str] = []
        for skill_dir in porter._portable_skill_dirs():
            src = skill_dir / "SKILL.md"
            if "## Context" not in src.read_text(encoding="utf-8"):
                continue
            if marker not in porter.render_skill(src):
                offenders.append(skill_dir.name)
        self.assertEqual(
            [], offenders,
            msg=(
                "Source skills with a `## Context` heading whose ported "
                "output is missing the host-neutral guidance paragraph "
                "(CONTEXT_BLOCK_RE failed to match): " + ", ".join(offenders)
            ),
        )


class OpenClawManifestSkillRegistrationTest(unittest.TestCase):
    """OpenClaw activates skills from the explicit `skills` array in
    `openclaw.plugin.json`, which is hand-maintained (NOT auto-synced). A
    ported skill dir that is absent from that array ships as dead files the
    host never activates; a stale array entry points at a missing dir. The
    porter drift guard and `--check` only compare SKILL.md *content*, so
    they cannot see this registration gap. This guard closes it.

    Lives in a test (not a `ci.yml` step) for the same reason the porter
    drift guard does — the autonomous bot's `GITHUB_TOKEN` cannot edit
    files under `.github/workflows/`.
    """

    @staticmethod
    def _manifest_skills() -> set[str]:
        manifest = json.loads(
            (ROOT / "openclaw-plugin" / "openclaw.plugin.json").read_text(encoding="utf-8")
        )
        return {entry.split("/", 1)[-1] for entry in manifest.get("skills", [])}

    @staticmethod
    def _ported_skill_dirs() -> set[str]:
        skills_root = ROOT / "openclaw-plugin" / "skills"
        return {
            d.name
            for d in skills_root.iterdir()
            if d.is_dir() and d.name != "__pycache__"
        }

    def test_manifest_skills_match_ported_dirs(self) -> None:
        registered = self._manifest_skills()
        ported = self._ported_skill_dirs()
        missing = ported - registered
        extra = registered - ported
        self.assertEqual(
            set(), missing,
            msg=(
                "ported openclaw-plugin/skills/ dirs absent from the "
                "openclaw.plugin.json `skills` array (they ship as dead "
                "files the host never activates): " + ", ".join(sorted(missing))
            ),
        )
        self.assertEqual(
            set(), extra,
            msg=(
                "openclaw.plugin.json `skills` entries with no corresponding "
                "ported skill dir (stale registration): " + ", ".join(sorted(extra))
            ),
        )

    def test_manifest_description_skill_count_matches(self) -> None:
        manifest = json.loads(
            (ROOT / "openclaw-plugin" / "openclaw.plugin.json").read_text(encoding="utf-8")
        )
        m = re.search(r"(\d+)\s+deck skills", manifest.get("description", ""))
        self.assertIsNotNone(
            m, msg="manifest description no longer states an '<N> deck skills' count"
        )
        self.assertEqual(
            len(self._ported_skill_dirs()), int(m.group(1)),
            msg="manifest description skill count drifted from the ported skill-dir count",
        )


class OpenClawToolVerbSurfaceTest(unittest.TestCase):
    """OpenClaw exposes `goc` as a registered tool whose `verb` parameter is a
    typed literal-union built from `GOC_VERBS` in `openclaw-plugin/index.ts`.
    A verb that exists in the engine but is absent from that list is
    unreachable from the OpenClaw integration. Catch the drift here so the
    next added subparser does not silently bypass the plugin surface.
    """

    GOC_VERBS_RE = re.compile(
        r"const\s+GOC_VERBS\s*=\s*\[([^\]]*)\]\s*as\s+const",
        re.MULTILINE,
    )

    @staticmethod
    def _engine_verbs() -> list[str]:
        parser = eng._build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                return list(action.choices.keys())
        raise RuntimeError("could not locate subparsers on the goc parser")

    @classmethod
    def _ts_verbs(cls) -> list[str]:
        text = (ROOT / "openclaw-plugin" / "index.ts").read_text(encoding="utf-8")
        m = cls.GOC_VERBS_RE.search(text)
        if not m:
            raise RuntimeError("GOC_VERBS literal not found in openclaw-plugin/index.ts")
        return [
            token.strip().strip('"').strip("'")
            for token in m.group(1).split(",")
            if token.strip()
        ]

    def test_ts_verbs_match_engine_subparsers(self) -> None:
        engine_verbs = self._engine_verbs()
        ts_verbs = self._ts_verbs()
        self.assertEqual(
            engine_verbs, ts_verbs,
            msg=(
                "openclaw-plugin/index.ts:GOC_VERBS drifted from goc/engine.py "
                "subparsers. Update the TS literal-union (and re-run "
                "`npm run build` inside openclaw-plugin/) so the tool surface "
                "matches every verb registered by _build_parser."
            ),
        )


if __name__ == "__main__":
    unittest.main()
