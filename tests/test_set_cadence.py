from __future__ import annotations

import importlib.util
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

    def test_multiday_rejected(self) -> None:
        with self.assertRaises(ValueError):
            setc.interval_to_cron("5d", 0)

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


if __name__ == "__main__":
    unittest.main()
