"""The built wheel ships every tracked file of the `goc` package.

The suite imports `goc` from the source tree and CI installs the package
editable, so nothing in the build looks at the wheel users install. The
`Verify package data ships templates` step in `ci.yml` cannot either: under an
editable install `files('goc.templates')` is the same `goc/templates/`
directory the step lists its skills from, so it reads back its own listing.
With `exclude = ["goc/templates/skills"]` added to the hatch wheel target, the
wheel shipped none of the 18 skills while that step and the whole suite
passed, and `goc install --local-skills` from that wheel crashed on the
missing directory. See
`ci-package-data-check-reads-back-the-source-tree-it-lists-so-it-cannot-fail`.

This test builds the distribution the way `release.yml` does (`uv build`,
which builds the sdist and then the wheel from it) and checks the wheel
against `git ls-files goc`. The reference is the tracked tree rather than a
list of skills or data files, so a dropped module, hook, template or schema
copy fails the same way, including one added after this test was written.

The check lives in the suite rather than in `ci.yml` because the autonomous
bot's `GITHUB_TOKEN` cannot edit `.github/workflows/`. CI's `Run regression
tests` step runs it on every push.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _git_checkout() -> bool:
    if shutil.which("git") is None:
        return False
    probe = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return probe.returncode == 0 and probe.stdout.strip() == "true"


def _tracked_package_files() -> list[str]:
    """Tracked files under `goc/` that exist in the working tree."""
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--", "goc"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return sorted(p for p in listed.split("\0") if p and (ROOT / p).is_file())


@unittest.skipUnless(shutil.which("uv"), "uv not on PATH")
@unittest.skipUnless(_git_checkout(), "not a git checkout")
class WheelPackageParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        out_dir = tempfile.TemporaryDirectory()
        cls.addClassCleanup(out_dir.cleanup)
        # Pin the version the way release.yml does, so the build does not
        # depend on the checkout's tags or depth.
        env = {**os.environ, "SETUPTOOLS_SCM_PRETEND_VERSION": "0.0.0"}
        cls.build = subprocess.run(
            ["uv", "build", "--out-dir", out_dir.name],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
        cls.wheels = sorted(Path(out_dir.name).glob("*.whl"))
        cls.members: set[str] = set()
        if cls.build.returncode == 0 and len(cls.wheels) == 1:
            with zipfile.ZipFile(cls.wheels[0]) as wheel:
                cls.members = set(wheel.namelist())

    def test_build_produces_one_wheel(self) -> None:
        self.assertEqual(0, self.build.returncode, f"uv build failed:\n{self.build.stderr}")
        self.assertEqual(1, len(self.wheels), f"expected one wheel, got {self.wheels}")

    def test_reference_covers_the_package(self) -> None:
        """An empty or partial `git ls-files` would make the parity check vacuous."""
        tracked = _tracked_package_files()
        self.assertIn("goc/__init__.py", tracked)
        self.assertIn("goc/schema.yaml", tracked)
        self.assertTrue(
            any(p.startswith("goc/templates/skills/") and p.endswith("/SKILL.md") for p in tracked),
            "git ls-files lists no skill template",
        )

    def test_wheel_ships_every_tracked_package_file(self) -> None:
        self.assertTrue(self.members, "no wheel to inspect; see test_build_produces_one_wheel")
        missing = [p for p in _tracked_package_files() if p not in self.members]
        if missing:
            self.fail(
                f"{len(missing)} tracked goc/ file(s) missing from {self.wheels[0].name} "
                "(check the [tool.hatch.build] tables in pyproject.toml):\n  " + "\n  ".join(missing)
            )


if __name__ == "__main__":
    unittest.main()
