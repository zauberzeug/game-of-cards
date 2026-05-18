from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _static_version() -> str:
    """Return the `__version__` literal from `goc/__init__.py` source.

    `goc.__version__` resolves dynamically at runtime via importlib.metadata
    (hatch-vcs derives it from `git describe --tags`); between releases that
    value drifts from the static literals in plugin manifests. This helper
    reads the literal directly so version-surface checks compare like-for-like
    against the value `release_rewrite_versions.py` rewrites at release time.
    """
    text = (ROOT / "goc" / "__init__.py").read_text()
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "goc/__init__.py: __version__ literal not found"
    return match.group(1)


class VersionSurfaceTest(unittest.TestCase):
    """All static version literals must agree with the literal in `goc/__init__.py`.

    `pyproject.toml` is no longer in this set — it carries `dynamic = ["version"]`
    and hatch-vcs computes the wheel version from the git tag at build time.
    The static literals below are rewritten from the same git tag by
    `scripts/release_rewrite_versions.py` during the release workflow, so
    between releases they should all match the last released literal.
    """

    def test_plugin_manifests_match_package_version(self) -> None:
        expected = _static_version()

        # (relative path, key path inside the JSON)
        manifests: list[tuple[str, tuple[str, ...]]] = [
            ("openclaw-plugin/package.json", ("version",)),
            ("openclaw-plugin/package-lock.json", ("version",)),
            ("openclaw-plugin/package-lock.json", ("packages", "", "version")),
            ("claude-plugin/.claude-plugin/plugin.json", ("version",)),
            ("codex-plugin/.codex-plugin/plugin.json", ("version",)),
            (".claude-plugin/marketplace.json", ("metadata", "version")),
        ]
        for relpath, locator in manifests:
            data = json.loads((ROOT / relpath).read_text())
            value = data
            for key in locator:
                value = value[key]
            self.assertEqual(expected, value, msg=f"{relpath} {locator}")

    def test_self_hosted_generated_surfaces_match_package_version(self) -> None:
        expected = _static_version()
        self.assertEqual(
            expected,
            (ROOT / ".game-of-cards" / "deck" / ".goc-version").read_text().strip(),
        )

        # The version marker is stamped into the briefing target (AGENTS.md
        # by default; CLAUDE.md uses the IMPORT-marker form instead).
        agents_text = (ROOT / "AGENTS.md").read_text()
        markers = re.findall(r"<!-- BEGIN GOC v([0-9.]+) -->", agents_text)
        self.assertTrue(markers, msg="AGENTS.md: missing GoC version marker")
        self.assertEqual([expected], markers, msg="AGENTS.md: stale GoC marker")


if __name__ == "__main__":
    unittest.main()
