"""Regression guard for codex-plugin-skills-cannot-find-bundled-goc-cli.

A Codex plugin-only install loads the GoC skills but does NOT put the
plugin's `bin/` directory on shell PATH, so a bare `goc` is not callable.
The bundled engine must still be reachable by absolute path, and the
Codex-specific guidance must tell agents how to reach it instead of
implying `goc` is on PATH or asking them to create a global shim.

Two contracts are enforced here:

1. EMPIRICAL — from a non-GoC working directory, the bundled
   `codex-plugin/bin/goc` wrapper AND the `PYTHONPATH=<root> python3 -m
   goc.cli` form both run the engine by absolute path (no global install,
   no PATH entry).
2. MECHANICAL — `codex-kickoff`'s guidance (template + every mirror)
   states that `goc` is not callable in a plugin-only install, points at
   the bundled-engine invocation, and forbids the `~/.local/bin/goc` shim.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "codex-plugin"

# Template source-of-truth + the two synced mirrors that ship to consumers.
_CODEX_KICKOFF_COPIES = [
    ROOT / "goc" / "templates" / "skills" / "codex-kickoff" / "SKILL.md",
    ROOT / ".codex" / "skills" / "codex-kickoff" / "SKILL.md",
    ROOT / "codex-plugin" / "skills" / "codex-kickoff" / "SKILL.md",
]


class BundledCliReachableByAbsolutePathTest(unittest.TestCase):
    """The bundled engine runs by absolute path from an unrelated cwd."""

    def test_bin_wrapper_runs_by_absolute_path(self) -> None:
        wrapper = PLUGIN_ROOT / "bin" / "goc"
        self.assertTrue(wrapper.exists(), f"missing bundled wrapper: {wrapper}")
        with tempfile.TemporaryDirectory() as outside:
            result = subprocess.run(
                [str(wrapper), "--help"],
                cwd=outside,
                capture_output=True,
                text=True,
            )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"bundled bin/goc failed by absolute path:\n{result.stderr}",
        )
        self.assertIn("usage: goc", result.stdout)

    def test_engine_module_runs_via_pythonpath(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            result = subprocess.run(
                [sys.executable, "-m", "goc.cli", "--help"],
                cwd=outside,
                capture_output=True,
                text=True,
                env={"PYTHONPATH": str(PLUGIN_ROOT), "PATH": "/usr/bin:/bin"},
            )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"PYTHONPATH=<plugin-root> python -m goc.cli failed:\n{result.stderr}",
        )
        self.assertIn("usage: goc", result.stdout)


class CodexGuidanceResolvesBundledEngineTest(unittest.TestCase):
    """codex-kickoff teaches the bundled-engine path, not a bare-`goc` lie."""

    def test_guidance_states_goc_not_on_path_and_points_at_bundled_engine(self) -> None:
        for path in _CODEX_KICKOFF_COPIES:
            self.assertTrue(path.exists(), f"missing codex-kickoff copy: {path}")
            text = path.read_text()
            self.assertIn(
                "is *not* a callable command",
                text,
                msg=(
                    f"{path.relative_to(ROOT)}: Codex guidance must state that "
                    "`goc` is not callable in a plugin-only install."
                ),
            )
            self.assertIn(
                "python3 -m goc.cli",
                text,
                msg=(
                    f"{path.relative_to(ROOT)}: Codex guidance must give the "
                    "bundled-engine invocation path."
                ),
            )
            self.assertIn(
                "bin/goc",
                text,
                msg=(
                    f"{path.relative_to(ROOT)}: Codex guidance must point at the "
                    "bundled bin/goc wrapper."
                ),
            )

    def test_guidance_forbids_global_shim(self) -> None:
        for path in _CODEX_KICKOFF_COPIES:
            # Collapse whitespace so a line-wrapped prohibition still matches.
            text = " ".join(path.read_text().split())
            self.assertIn(
                "Do **not** create a global `~/.local/bin/goc` shim",
                text,
                msg=(
                    f"{path.relative_to(ROOT)}: Codex guidance must explicitly "
                    "forbid the global ~/.local/bin/goc shim workaround."
                ),
            )


if __name__ == "__main__":
    unittest.main()
