from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import goc  # noqa: E402


def _project_version() -> str:
    match = re.search(r'^version = "([^"]+)"$', (ROOT / "pyproject.toml").read_text(), re.MULTILINE)
    if match is None:
        raise AssertionError("pyproject.toml project.version not found")
    return match.group(1)


class VersionSurfaceTest(unittest.TestCase):
    def test_package_version_matches_pyproject(self) -> None:
        self.assertEqual(_project_version(), goc.__version__)

    def test_self_hosted_generated_surfaces_match_package_version(self) -> None:
        version = _project_version()
        self.assertEqual(version, (ROOT / "deck" / ".goc-version").read_text().strip())

        for relative in ("AGENTS.md", "CLAUDE.md"):
            text = (ROOT / relative).read_text()
            markers = re.findall(r"<!-- BEGIN GOC v([0-9.]+) -->", text)
            self.assertTrue(markers, msg=f"{relative}: missing GoC marker")
            self.assertEqual([version], markers, msg=f"{relative}: stale GoC marker")


if __name__ == "__main__":
    unittest.main()
