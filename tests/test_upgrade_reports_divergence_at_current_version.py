"""Regression: `goc upgrade` at the current version still prints the divergence report.

`Skill(upgrade)` runs `goc upgrade` and reads the sentinel-marked JSON
divergence report from stdout; every reconcile step after that reads the
report. It used to be printed only by `_sync_game_of_cards_config`, below
`upgrade()`'s "already at goc X — nothing to do." return. A diverged evolving
file is `preserved`, a no-op to the write plan that gates that return, so the
divergence the skill exists to reconcile never got a run past it: once anyone
had run `goc upgrade` at a version, the skill's own run got no report, and the
upstream changes to `.game-of-cards/README.md` / `config.yaml` went
un-reconciled until the next release.

Card: `upgrade-skill-cannot-reach-the-divergence-report-once-the-version-is-current`.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import install as goc_install  # noqa: E402


@contextlib.contextmanager
def _chdir(path: Path):
    prev = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


@contextlib.contextmanager
def _engine_config_at(repo: Path):
    """Point the engine's import-time config lookup at *repo*, as a fresh CLI
    process would (see the same helper in
    test_upgrade_repairs_damaged_install_at_same_version.py)."""

    from goc import engine

    saved = (engine.GAME_OF_CARDS_CONFIG_FILE, engine.LEGACY_DECK_CONFIG_FILE)
    engine.GAME_OF_CARDS_CONFIG_FILE = repo / ".game-of-cards" / "config.yaml"
    engine.LEGACY_DECK_CONFIG_FILE = repo / ".claude" / "config.yaml"
    try:
        yield
    finally:
        engine.GAME_OF_CARDS_CONFIG_FILE, engine.LEGACY_DECK_CONFIG_FILE = saved


def _upgrade(repo: Path, **kwargs) -> str:
    """Run `upgrade()` in *repo* and return its stdout — the stream the skill parses."""

    with _chdir(repo), _engine_config_at(repo):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            with contextlib.redirect_stderr(io.StringIO()):
                goc_install.upgrade(**kwargs)
    return out.getvalue()


def _install_current(repo: Path) -> None:
    (repo / ".git").mkdir(exist_ok=True)
    with _chdir(repo), _engine_config_at(repo):
        with contextlib.redirect_stdout(io.StringIO()):
            goc_install.install(local_skills=True)


def _diverge_readme(repo: Path) -> None:
    readme = repo / ".game-of-cards" / "README.md"
    readme.write_text(readme.read_text() + "\nLocal note: our own hook docs.\n")


def _report(stdout: str) -> dict:
    """The JSON on the line after the sentinel, located the way the skill does."""

    lines = stdout.splitlines()
    for idx, line in enumerate(lines[:-1]):
        if line == goc_install._DIVERGENCE_REPORT_MARKER:
            return json.loads(lines[idx + 1])
    raise AssertionError(f"no divergence report in upgrade output:\n{stdout}")


def _snapshot(repo: Path) -> dict[str, tuple[bytes, int]]:
    return {
        str(path.relative_to(repo)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(repo.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }


class NoOpUpgradeStillReportsTest(unittest.TestCase):
    def test_no_op_upgrade_prints_the_report_after_its_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            _diverge_readme(repo)
            before = _snapshot(repo)

            out = _upgrade(repo)

            self.assertEqual(
                f"already at goc {goc_install.__version__} — nothing to do.",
                out.splitlines()[0],
            )
            by_path = {entry["path"]: entry for entry in _report(out)["files"]}
            self.assertEqual(
                {"path": "README.md", "status": "preserved", "ownership": "evolving"},
                by_path["README.md"],
            )
            self.assertEqual(before, _snapshot(repo), msg="no-op upgrade touched files")

    def test_no_op_report_is_the_report_the_effecting_run_printed(self) -> None:
        """The skill's input does not depend on whether someone ran the engine first.

        The effecting run is the one a human makes in a terminal after a
        release bump; the no-op run is the skill's step 1 straight after it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            _diverge_readme(repo)
            (repo / ".game-of-cards" / "deck" / ".goc-version").write_text("0.0.1\n")

            effecting = _upgrade(repo)
            no_op = _upgrade(repo)

            self.assertIn("goc upgrade complete", effecting)
            self.assertIn("nothing to do", no_op)
            self.assertEqual(_report(effecting), _report(no_op))

    def test_no_op_dry_run_prints_what_the_real_no_op_prints(self) -> None:
        """The report is read-only, so the preview of a no-op is the no-op itself."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            _diverge_readme(repo)

            preview = _upgrade(repo, dry_run=True)
            real = _upgrade(repo)

            self.assertEqual(real, preview)
            self.assertIn("README.md", {entry["path"] for entry in _report(preview)["files"]})


if __name__ == "__main__":
    unittest.main()
