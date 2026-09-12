"""Regression guard: the mirror sync's skip predicate is scoped to the path itself.

`_skip` excludes compiled-Python artifacts from the mirror walk. It used to
substring-match the fragments `__pycache__` / `.pyc` against `str(path)` of the
ABSOLUTE path, so any checkout living under a directory that merely contains one
of them — `.pycharm/`, a `fix-pyc-handling` worktree — made every source and
destination item "skipped". The sync then copied nothing and `--check` reported
the empty comparison as `OK — byte-for-byte`, so a template edit shipped without
its mirrors with no signal at all.

The predicate must therefore test the path's own components and suffix, the way
the three sibling implementations already do (scripts/port_skills_to_openclaw.py,
goc/install.py).

Loads scripts/sync_plugin_assets.py via importlib (the script is not a package
module) and exercises its sync/check primitives in a temp tree.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_sync():
    """Import scripts/sync_plugin_assets.py without putting scripts/ on sys.path."""
    spec = importlib.util.spec_from_file_location(
        "_goc_sync_plugin_assets", ROOT / "scripts" / "sync_plugin_assets.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SkipPredicateScopeTest(unittest.TestCase):
    """`_skip` matches `__pycache__` components and `.pyc` suffixes — nothing else."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_sync()

    def test_skips_pycache_components_and_pyc_files(self) -> None:
        for path in (
            Path("/repo/goc/__pycache__"),
            Path("/repo/goc/__pycache__/engine.cpython-311.pyc"),
            Path("/repo/goc/engine.pyc"),
            Path("__pycache__/engine.cpython-311.pyc"),
        ):
            with self.subTest(path=path):
                self.assertTrue(
                    self.mod._skip(path),
                    msg=f"{path} is a compiled-Python artifact and must be skipped",
                )

    def test_does_not_skip_benign_ancestor_containing_a_fragment(self) -> None:
        """The assertion that would have caught the substring bug."""
        for path in (
            Path("/home/dev/.pycharm/checkout/goc/engine.py"),
            Path("/home/dev/.pyc-cache/goc/templates/skills/deck/SKILL.md"),
            Path("/work/fix-pyc-handling/claude-plugin/hooks/deck_session_start.py"),
            Path("/repo/goc/__pycache__old/engine.py"),
            Path("/repo/goc/engine.pyc.bak"),
        ):
            with self.subTest(path=path):
                self.assertFalse(
                    self.mod._skip(path),
                    msg=f"{path} holds real content — skipping it silently no-ops "
                        "the whole sync and makes --check compare nothing",
                )


class SyncUnderPycContainingRootTest(unittest.TestCase):
    """The sync and its `--check` still work on a checkout under a `.pyc` path."""

    def _tmp_checkout(self, raw: str) -> Path:
        """A repo root whose ANCESTOR name contains the `.pyc` fragment."""
        root = Path(raw) / ".pycharm" / "checkout"
        root.mkdir(parents=True)
        return root

    def test_sync_dir_copies_and_prunes_under_pyc_containing_root(self) -> None:
        mod = _load_sync()
        with tempfile.TemporaryDirectory() as raw:
            root = self._tmp_checkout(raw)
            src = root / "goc" / "templates" / "hooks"
            dst = root / "claude-plugin" / "hooks"
            src.mkdir(parents=True)
            dst.mkdir(parents=True)
            (src / "current_hook.py").write_text("# current\n")
            (src / "__pycache__").mkdir()
            (src / "__pycache__" / "current_hook.cpython-311.pyc").write_bytes(b"\x00")
            (dst / "retired_hook.py").write_text("# retired\n")

            changed = mod._sync_dir(src, dst)

            self.assertTrue(
                (dst / "current_hook.py").exists(),
                msg="template must be mirrored even from a checkout under a "
                    f"'.pyc'-containing path (changed={changed})",
            )
            self.assertFalse(
                (dst / "retired_hook.py").exists(),
                msg="orphan prune must still run under such a path",
            )
            self.assertFalse(
                (dst / "__pycache__").exists(),
                msg="real compiled-Python artifacts must still be excluded",
            )

    def test_check_flags_drift_under_pyc_containing_root(self) -> None:
        mod = _load_sync()
        with tempfile.TemporaryDirectory() as raw:
            root = self._tmp_checkout(raw)
            src = root / "goc" / "templates" / "hooks"
            dst = root / "claude-plugin" / "hooks"
            src.mkdir(parents=True)
            dst.mkdir(parents=True)
            (src / "current_hook.py").write_text("# current\n")
            (dst / "current_hook.py").write_text("# DRIFTED\n")

            # _check_changes also walks the codex skill trees and bootstrap
            # rooted at the module's ROOT, so minimal stubs are scaffolded.
            (root / "goc" / "templates" / "skills").mkdir(parents=True)
            bootstrap = root / "goc" / "templates" / "bootstrap" / "_goc-bootstrap.sh"
            bootstrap.parent.mkdir(parents=True)
            bootstrap.write_text("# bootstrap\n")
            for d in (root / "codex-plugin" / "skills", root / ".codex" / "skills"):
                d.mkdir(parents=True)
                (d / "_goc-bootstrap.sh").write_text("# bootstrap\n")
            mod.ROOT = root
            mod.SYNC_PAIRS = [(src, dst, frozenset(), frozenset())]

            diffs = mod._check_changes()

            self.assertIn(
                dst / "current_hook.py", diffs,
                msg="--check must report the corrupted mirror instead of "
                    f"reporting a byte-for-byte match having compared nothing (got {diffs})",
            )


if __name__ == "__main__":
    unittest.main()
