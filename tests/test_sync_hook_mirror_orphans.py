"""Regression guard: flat hook mirrors prune orphans and --check flags stale files.

The flat hook mirrors (claude-plugin/hooks/, codex-plugin/hooks/,
.claude/hooks/) used to be single-file sync pairs enumerated from the CURRENT
template set, so a renamed/retired hook template left a stale copy in every
flat mirror that neither the sync nor `--check` could see. The fix makes them
directory syncs of `goc/templates/hooks/`, with the hand-maintained
`hooks.json` protected via `preserve_files`.

Loads scripts/sync_plugin_assets.py via importlib (the script is not a
package module) and exercises its sync/check primitives in a temp tree.
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


class HookMirrorPairShapeTest(unittest.TestCase):
    """The pair list itself must use whole-directory hook mirrors.

    A regression back to per-file pairs enumerated from the current template
    set would re-open the orphan blind spot even with the prune logic intact,
    so the shape of the pairs is asserted directly.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_sync()

    def _pair_for(self, dst: Path):
        matches = [p for p in self.mod.SYNC_PAIRS if p[1] == dst]
        self.assertEqual(
            1, len(matches),
            msg=f"expected exactly one sync pair targeting {dst}, got {matches}",
        )
        return matches[0]

    def test_flat_hook_mirrors_are_dir_syncs_of_templates_hooks(self) -> None:
        hooks_src = ROOT / "goc" / "templates" / "hooks"
        for dst in (
            ROOT / "claude-plugin" / "hooks",
            ROOT / "codex-plugin" / "hooks",
            ROOT / ".claude" / "hooks",
        ):
            src, _, _, _ = self._pair_for(dst)
            self.assertEqual(
                hooks_src, src,
                msg=f"{dst} must mirror the whole templates/hooks/ directory, "
                    f"not per-file pairs (got src={src})",
            )

    def test_plugin_hook_mirrors_preserve_hooks_json(self) -> None:
        for dst in (
            ROOT / "claude-plugin" / "hooks",
            ROOT / "codex-plugin" / "hooks",
        ):
            _, _, _, preserve = self._pair_for(dst)
            self.assertIn(
                "hooks.json", preserve,
                msg=f"hand-maintained hooks.json in {dst} must be protected "
                    "from the dir-sync prune via preserve_files",
            )


class HookMirrorOrphanPruneTest(unittest.TestCase):
    """_sync_dir on a hook mirror prunes stale hooks but never hooks.json."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_sync()

    def test_stale_hook_pruned_and_hooks_json_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "templates" / "hooks"
            dst = Path(tmp) / "claude-plugin" / "hooks"
            src.mkdir(parents=True)
            dst.mkdir(parents=True)
            (src / "current_hook.py").write_text("# current\n")
            (dst / "retired_hook.py").write_text("# retired template copy\n")
            (dst / "hooks.json").write_text("{}\n")

            self.mod._sync_dir(src, dst, preserve_files=frozenset({"hooks.json"}))

            self.assertTrue((dst / "current_hook.py").exists())
            self.assertFalse(
                (dst / "retired_hook.py").exists(),
                msg="stale hook whose template was removed must be pruned",
            )
            self.assertTrue(
                (dst / "hooks.json").exists(),
                msg="hand-maintained hooks.json must survive the sync (no over-eager prune)",
            )


class HookMirrorCheckTest(unittest.TestCase):
    """--check (via _check_changes) flags a dst-only stale hook, skips hooks.json."""

    def _check_with_pairs(self, tmp: Path, pairs) -> list[Path]:
        """Run _check_changes against a temp tree with patched module globals.

        _check_changes also walks the codex skill trees and bootstrap rooted
        at the module's ROOT, so minimal stubs for those are scaffolded.
        """
        mod = _load_sync()
        (tmp / "goc" / "templates" / "skills").mkdir(parents=True, exist_ok=True)
        bootstrap = tmp / "goc" / "templates" / "bootstrap" / "_goc-bootstrap.sh"
        bootstrap.parent.mkdir(parents=True, exist_ok=True)
        bootstrap.write_text("# bootstrap\n")
        for d in (tmp / "codex-plugin" / "skills", tmp / ".codex" / "skills"):
            d.mkdir(parents=True, exist_ok=True)
            (d / "_goc-bootstrap.sh").write_text("# bootstrap\n")
        mod.ROOT = tmp
        mod.SYNC_PAIRS = pairs
        return mod._check_changes()

    def test_check_flags_stale_hook_but_not_hooks_json(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            src = tmp / "goc" / "templates" / "hooks"
            dst = tmp / "claude-plugin" / "hooks"
            src.mkdir(parents=True)
            dst.mkdir(parents=True)
            (src / "current_hook.py").write_text("# current\n")
            (dst / "current_hook.py").write_text("# current\n")
            (dst / "retired_hook.py").write_text("# retired template copy\n")
            (dst / "hooks.json").write_text("{}\n")

            pairs = [(src, dst, frozenset(), frozenset({"hooks.json"}))]
            diffs = self._check_with_pairs(tmp, pairs)

            self.assertIn(
                dst / "retired_hook.py", diffs,
                msg=f"--check must flag the stale dst-only hook, got: {diffs}",
            )
            self.assertNotIn(
                dst / "hooks.json", diffs,
                msg="--check must not flag the preserved hooks.json as drift",
            )

    def test_check_clean_on_in_sync_mirror(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            src = tmp / "goc" / "templates" / "hooks"
            dst = tmp / "claude-plugin" / "hooks"
            src.mkdir(parents=True)
            dst.mkdir(parents=True)
            (src / "current_hook.py").write_text("# current\n")
            (dst / "current_hook.py").write_text("# current\n")
            (dst / "hooks.json").write_text("{}\n")

            pairs = [(src, dst, frozenset(), frozenset({"hooks.json"}))]
            self.assertEqual([], self._check_with_pairs(tmp, pairs))


if __name__ == "__main__":
    unittest.main()
