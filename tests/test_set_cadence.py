from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "set_cadence.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("set_cadence", SCRIPT)
    assert spec and spec.loader, "could not load scripts/set_cadence.py"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


setc = _load_module()


# A minimal workflow that carries the two lines the rewriter manages.
_STUB = """\
name: Stub
on:
  schedule:
    # cadence: placeholder — managed by scripts/set_cadence.py
    - cron: '0 0 * * *'
  workflow_dispatch:
jobs:
  x:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
"""


def _make_repo(tmp: Path) -> Path:
    (tmp / "pyproject.toml").write_text("[project]\nname = 'stub'\n")
    wf = tmp / ".github" / "workflows"
    wf.mkdir(parents=True)
    for name in ("pull-card.yml", "audit-deck.yml", "refine-deck.yml"):
        (wf / name).write_text(_STUB)
    return tmp


class IntervalToCronTest(unittest.TestCase):
    def test_hourly_no_offset(self) -> None:
        self.assertEqual(setc.interval_to_cron("1h", 0), "0 * * * *")

    def test_three_hourly_offsets(self) -> None:
        self.assertEqual(setc.interval_to_cron("3h", 15), "15 */3 * * *")
        self.assertEqual(setc.interval_to_cron("3h", 45), "45 */3 * * *")

    def test_all_divisors_of_24(self) -> None:
        for n, field in [(2, "*/2"), (4, "*/4"), (6, "*/6"), (8, "*/8"), (12, "*/12")]:
            self.assertEqual(setc.interval_to_cron(f"{n}h", 0), f"0 {field} * * *")

    def test_daily_forms(self) -> None:
        self.assertEqual(setc.interval_to_cron("24h", 0), "0 0 * * *")
        self.assertEqual(setc.interval_to_cron("1d", 30), "30 0 * * *")

    def test_non_divisor_hours_rejected(self) -> None:
        for bad in ("5h", "7h", "9h", "13h", "0h"):
            with self.assertRaises(ValueError):
                setc.interval_to_cron(bad, 0)

    def test_multiday_supported(self) -> None:
        # Nd (N>=2) -> day-of-month */N step (roughly every N days).
        self.assertEqual(setc.interval_to_cron("3d", 15), "15 0 */3 * *")
        self.assertEqual(setc.interval_to_cron("3d", 45), "45 0 */3 * *")
        self.assertEqual(setc.interval_to_cron("7d", 0), "0 0 */7 * *")

    def test_zero_day_rejected(self) -> None:
        with self.assertRaises(ValueError):
            setc.interval_to_cron("0d", 0)

    def test_day_interval_over_30_rejected(self) -> None:
        # cron's day-of-month field caps at 31; a */N step with N >= 31
        # matches only the 1st and cannot represent "every N days".
        for bad in ("31d", "32d", "40d", "365d"):
            with self.assertRaises(ValueError):
                setc.interval_to_cron(bad, 0)

    def test_day_interval_boundary_30_supported(self) -> None:
        # 30d (days 1 and 31) is the last day-of-month step that matches
        # more than one day; */31 would enumerate {1, 32} and collapse to
        # monthly-on-the-1st.
        self.assertEqual(setc.interval_to_cron("30d", 0), "0 0 */30 * *")

    def test_weekly_exact_via_dow(self) -> None:
        # 1w -> exact weekly via the day-of-week field (Monday), drift-free.
        self.assertEqual(setc.interval_to_cron("1w", 15), "15 0 * * 1")
        self.assertEqual(setc.interval_to_cron("1w", 45), "45 0 * * 1")

    def test_multi_week_rejected(self) -> None:
        with self.assertRaises(ValueError):
            setc.interval_to_cron("2w", 0)

    def test_garbage_rejected(self) -> None:
        for bad in ("", "h", "1m", "abc", "1.5h"):
            with self.assertRaises(ValueError):
                setc.interval_to_cron(bad, 0)

    def test_offset_out_of_range_rejected(self) -> None:
        with self.assertRaises(ValueError):
            setc.interval_to_cron("1h", 60)


class RetuneTest(unittest.TestCase):
    def test_rewrites_cron_and_comment(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = _make_repo(Path(d))
            cron, changed = setc.retune(repo, "audit", "3h")
            self.assertEqual(cron, "15 */3 * * *")
            self.assertTrue(changed)
            text = (repo / ".github/workflows/audit-deck.yml").read_text()
            self.assertIn("- cron: '15 */3 * * *'", text)
            self.assertIn("# cadence: audit-deck every 3h (minute offset :15)", text)

    def test_idempotent_second_run(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = _make_repo(Path(d))
            _, first = setc.retune(repo, "pull", "1h")
            _, second = setc.retune(repo, "pull", "1h")
            self.assertTrue(first)
            self.assertFalse(second)

    def test_current_cadence_reads_back(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = _make_repo(Path(d))
            setc.retune(repo, "refine", "3h")
            cadence = setc.current_cadence(repo)
            self.assertEqual(cadence["refine"]["cron"], "45 */3 * * *")
            self.assertIn("every 3h", cadence["refine"]["comment"])

    def test_two_cron_lines_rejected_and_file_untouched(self) -> None:
        # A workflow with two schedule entries must be refused, not
        # half-retuned (first line rewritten, second left at the stale
        # cadence).
        with tempfile.TemporaryDirectory() as d:
            repo = _make_repo(Path(d))
            p = repo / ".github/workflows/pull-card.yml"
            before = p.read_text().replace(
                "    - cron: '0 0 * * *'\n",
                "    - cron: '0 0 * * *'\n    - cron: '13 9 * * 6,0'\n",
            )
            p.write_text(before)
            with self.assertRaisesRegex(ValueError, "found 2"):
                setc.retune(repo, "pull", "4h")
            self.assertEqual(p.read_text(), before)

    def test_duplicate_cadence_marker_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = _make_repo(Path(d))
            p = repo / ".github/workflows/pull-card.yml"
            marker = "    # cadence: placeholder — managed by scripts/set_cadence.py\n"
            p.write_text(p.read_text().replace(marker, marker * 2))
            with self.assertRaisesRegex(ValueError, "found 2"):
                setc.retune(repo, "pull", "1h")

    def test_show_reports_every_schedule_line(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = _make_repo(Path(d))
            p = repo / ".github/workflows/pull-card.yml"
            p.write_text(
                p.read_text().replace(
                    "    - cron: '0 0 * * *'\n",
                    "    - cron: '0 0 * * *'\n    - cron: '13 9 * * 6,0'\n",
                )
            )
            cadence = setc.current_cadence(repo)
            self.assertEqual(cadence["pull"]["cron"], "0 0 * * *, 13 9 * * 6,0")

    def test_dry_run_validates_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = _make_repo(Path(d))
            p = repo / ".github/workflows/pull-card.yml"
            before = p.read_text()
            cron, changed = setc.retune(repo, "pull", "3h", write=False)
            self.assertEqual(cron, "13 */3 * * *")
            self.assertTrue(changed)
            self.assertEqual(p.read_text(), before)

    def test_missing_cadence_marker_errors(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = _make_repo(Path(d))
            p = repo / ".github/workflows/pull-card.yml"
            p.write_text(
                p.read_text().replace(
                    "    # cadence: placeholder — managed by scripts/set_cadence.py\n",
                    "",
                )
            )
            with self.assertRaises(ValueError):
                setc.retune(repo, "pull", "1h")


class MainAllOrNothingTest(unittest.TestCase):
    """`main` must not mutate any workflow file when any requested retune
    would fail — a nonzero exit means nothing changed on disk."""

    def _run_main(self, repo: Path, argv: list[str]) -> tuple[int, str]:
        original = setc._repo_root
        setc._repo_root = lambda: repo
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
                rc = setc.main(argv)
        finally:
            setc._repo_root = original
        return rc, stderr.getvalue()

    def _snapshot(self, repo: Path) -> dict[str, str]:
        wf = repo / ".github" / "workflows"
        return {p.name: p.read_text() for p in wf.iterdir()}

    def test_invalid_later_spec_leaves_all_files_untouched(self) -> None:
        # `--pull 2h --audit 5h`: 5 does not divide 24, so the audit spec is
        # invalid — pull-card.yml must NOT have been retuned when main exits 2.
        with tempfile.TemporaryDirectory() as d:
            repo = _make_repo(Path(d))
            before = self._snapshot(repo)
            rc, stderr = self._run_main(repo, ["--pull", "2h", "--audit", "5h"])
            self.assertEqual(rc, 2)
            self.assertIn("5h", stderr)
            self.assertEqual(self._snapshot(repo), before)

    def test_guard_failure_in_later_workflow_leaves_all_files_untouched(self) -> None:
        # A later workflow that fails retune's managed-line guards (two cron
        # lines) must also abort before the earlier workflow is rewritten.
        with tempfile.TemporaryDirectory() as d:
            repo = _make_repo(Path(d))
            p = repo / ".github/workflows/audit-deck.yml"
            p.write_text(
                p.read_text().replace(
                    "    - cron: '0 0 * * *'\n",
                    "    - cron: '0 0 * * *'\n    - cron: '13 9 * * 6,0'\n",
                )
            )
            before = self._snapshot(repo)
            rc, stderr = self._run_main(repo, ["--pull", "2h", "--audit", "3h"])
            self.assertEqual(rc, 2)
            self.assertIn("found 2", stderr)
            self.assertEqual(self._snapshot(repo), before)

    def test_all_valid_specs_apply(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = _make_repo(Path(d))
            rc, _ = self._run_main(repo, ["--pull", "2h", "--audit", "3h"])
            self.assertEqual(rc, 0)
            self.assertIn(
                "- cron: '13 */2 * * *'",
                (repo / ".github/workflows/pull-card.yml").read_text(),
            )
            self.assertIn(
                "- cron: '15 */3 * * *'",
                (repo / ".github/workflows/audit-deck.yml").read_text(),
            )


if __name__ == "__main__":
    unittest.main()
