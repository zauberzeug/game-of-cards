"""Regression guard: every auto-synced mirror tree is marked linguist-generated.

`.gitattributes` collapses machine-written trees in GitHub PR review so
reviewers see each authored change once, not N times across the mirrors.
The tree list is derived from `scripts/sync_plugin_assets.py`'s SYNC_PAIRS
(plus the codex skill trees it syncs via specialized functions and the
committed esbuild bundle), so a future sync destination cannot land without
a `.gitattributes` rule. Authored files that merely live inside synced or
marked trees must NOT carry the marker, or their real diffs get collapsed.
"""

from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Authored files inside synced/marked trees — must stay reviewable.
AUTHORED = {
    "claude-plugin/hooks/hooks.json",
    "codex-plugin/hooks/hooks.json",
    ".claude/skills/tune-cadence/SKILL.md",
}


def _load_sync_module():
    spec = importlib.util.spec_from_file_location(
        "_goc_sync_assets", ROOT / "scripts" / "sync_plugin_assets.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _generated_dirs() -> list[Path]:
    sync = _load_sync_module()
    dirs = {dst for _, dst, _, _ in sync.SYNC_PAIRS if dst.is_dir()}
    # Codex skill trees are synced by specialized tree functions, not pairs;
    # openclaw-plugin/dist/ is committed esbuild output (`npm run build`).
    dirs |= {
        ROOT / "codex-plugin" / "skills",
        ROOT / ".codex" / "skills",
        ROOT / "openclaw-plugin" / "dist",
    }
    return sorted(dirs)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


class GitattributesGeneratedMarkerTest(unittest.TestCase):
    def setUp(self) -> None:
        if not (ROOT / ".git").exists():
            self.skipTest("not a git checkout (sdist/wheel test run)")

    def _attrs(self, rels: list[str]) -> dict[str, str]:
        out = _git("check-attr", "linguist-generated", "--", *rels)
        result: dict[str, str] = {}
        for line in out.splitlines():
            path, _, value = (part.strip() for part in line.rsplit(":", 2))
            result[path] = value
        return result

    def test_every_synced_tree_is_marked_generated(self) -> None:
        for d in _generated_dirs():
            rels = _git("ls-files", "--", str(d)).splitlines()
            if not rels:
                continue
            values = self._attrs(rels)
            unmarked = sorted(
                rel for rel, v in values.items() if rel not in AUTHORED and v != "true"
            )
            self.assertEqual(
                unmarked,
                [],
                f"auto-synced files in {d.relative_to(ROOT)} lack "
                f"`linguist-generated=true` in .gitattributes: {unmarked}",
            )

    def test_authored_files_inside_marked_trees_stay_reviewable(self) -> None:
        values = self._attrs(sorted(AUTHORED))
        collapsed = sorted(rel for rel, v in values.items() if v == "true")
        self.assertEqual(
            collapsed,
            [],
            f"authored files must not be collapsed as generated: {collapsed}",
        )


if __name__ == "__main__":
    unittest.main()
