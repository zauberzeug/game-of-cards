"""Reproduce: retune() silently half-retunes a workflow that carries two
`- cron:` schedule lines, and --show reports only the first schedule.

Run: uv run python .game-of-cards/deck/set-cadence-silently-half-retunes-workflows-with-two-cron-schedule-lines/reproduce.py

`retune()` substitutes with count=1, so its "expected exactly one `- cron:`
line" guard can never observe a count above 1 — a two-schedule workflow is
rewritten on the first line only, the second keeps firing at the stale
cadence, and the tool reports success. Exits non-zero while the defect is
present; exits zero once retune() rejects multi-schedule workflows and
current_cadence() reports every schedule line.
"""
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root() / "scripts"))

from set_cadence import current_cadence, retune  # noqa: E402


_TWO_SCHEDULE_STUB = """\
name: Stub
on:
  schedule:
    # cadence: placeholder — managed by scripts/set_cadence.py
    - cron: '13 */2 * * *'
    - cron: '13 9 * * 6,0'
  workflow_dispatch:
jobs:
  x:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d)
        (repo / "pyproject.toml").write_text("[project]\nname = 'stub'\n")
        wf = repo / ".github" / "workflows"
        wf.mkdir(parents=True)
        for name in ("pull-card.yml", "audit-deck.yml", "refine-deck.yml"):
            (wf / name).write_text(_TWO_SCHEDULE_STUB)

        try:
            cron, changed = retune(repo, "pull", "4h")
        except ValueError as exc:
            print(f"retune() correctly raised ValueError: {exc}")
            text = (wf / "pull-card.yml").read_text()
            if "13 9 * * 6,0" not in text or "*/4" in text:
                print("FAIL: retune() raised but still mutated the file.")
                return 1
            shown = current_cadence(repo)["pull"]["cron"]
            print(f"--show reports: {shown!r}")
            if "13 9 * * 6,0" not in shown:
                print("FAIL: --show still hides schedules after the first match.")
                return 1
            print("PASS: multi-schedule workflow is rejected and fully reported.")
            return 0

        text = (wf / "pull-card.yml").read_text()
        second_untouched = "13 9 * * 6,0" in text
        print(f"retune() returned ({cron!r}, {changed}) with no error")
        print(f"  second schedule line still present at stale cadence: {second_untouched}")
        shown = current_cadence(repo)["pull"]["cron"]
        print(f"  --show reports only: {shown!r}")
        print(
            "FAIL: two-cron workflow was silently half-retuned — first line "
            "rewritten, second keeps firing at the old cadence."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
