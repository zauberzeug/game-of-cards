from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release_rewrite_versions.py"

# Files the rewriter mutates. Kept in sync with rewrite_all() in the script.
TARGETS = (
    Path("goc") / "__init__.py",
    Path("openclaw-plugin") / "package.json",
    Path("openclaw-plugin") / "package-lock.json",
    Path("claude-plugin") / ".claude-plugin" / "plugin.json",
    Path("codex-plugin") / ".codex-plugin" / "plugin.json",
    Path(".claude-plugin") / "marketplace.json",
    Path(".game-of-cards") / "deck" / ".goc-version",
    Path("AGENTS.md"),
)


def _stage_repo(dst: Path) -> None:
    """Copy just the files the rewriter touches into a sandbox repo root,
    plus the script itself. The script resolves ROOT from its own location,
    so we mirror the directory layout under `dst`.
    """
    (dst / "scripts").mkdir(parents=True)
    shutil.copy2(SCRIPT, dst / "scripts" / SCRIPT.name)
    for rel in TARGETS:
        src = ROOT / rel
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)


def _run_rewriter(cwd: Path, version: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(cwd / "scripts" / SCRIPT.name), version],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class ReleaseRewriteVersionFormatTest(unittest.TestCase):
    """`scripts/release_rewrite_versions.py` must reject malformed version
    arguments BEFORE writing any file. The script is invoked from CI with
    whatever string the release dispatcher passed as `-f version=...`; an
    input that isn't a `X.Y.Z` semver triple would otherwise leave the
    working tree half-rewritten (silent no-op surface — see card
    `release-version-rewriter-does-not-validate-input-format`).
    """

    def _assert_pristine(self, sandbox: Path) -> None:
        for rel in TARGETS:
            self.assertEqual(
                (sandbox / rel).read_bytes(),
                (ROOT / rel).read_bytes(),
                msg=f"{rel} mutated despite malformed input",
            )

    def test_malformed_version_exits_nonzero_and_writes_nothing(self) -> None:
        for bad in ("1.0", "v1.2.3", "1.2.3-rc1", "1.2.3 ", "", "1.2.3.4"):
            with self.subTest(bad=bad):
                with tempfile.TemporaryDirectory() as tmpdir:
                    sandbox = Path(tmpdir)
                    _stage_repo(sandbox)
                    result = _run_rewriter(sandbox, bad)
                    self.assertNotEqual(
                        0, result.returncode,
                        msg=f"rewriter accepted malformed {bad!r}: {result.stderr}",
                    )
                    self.assertIn(
                        "expected X.Y.Z", result.stderr,
                        msg=f"error message must name the expected format; got {result.stderr!r}",
                    )
                    self._assert_pristine(sandbox)

    def test_valid_version_still_rewrites_every_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = Path(tmpdir)
            _stage_repo(sandbox)
            result = _run_rewriter(sandbox, "99.88.77")
            self.assertEqual(
                0, result.returncode,
                msg=f"valid version rejected: {result.stderr}",
            )
            # Every target must contain the new literal.
            for rel in TARGETS:
                text = (sandbox / rel).read_text()
                self.assertIn(
                    "99.88.77", text,
                    msg=f"{rel} not rewritten to 99.88.77",
                )


if __name__ == "__main__":
    unittest.main()
