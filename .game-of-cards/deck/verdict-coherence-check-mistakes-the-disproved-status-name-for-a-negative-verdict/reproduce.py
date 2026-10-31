"""Reproduce: DECISION_CONTRADICTS_VERDICT fires on a card that merely names the
`disproved` status, under a decision that uses everyday words.

The advisory `validate_decision_verdict_coherence` warns when a resolved
`## Decision` matches `RESCOPE_MARKERS_RE` while the card's summary (or a `>`
banner) matches `NEGATIVE_VERDICT_RE`. Both lists matched ordinary prose: the
verdict list matched `disproved` wherever a summary *names the status* ("the
card flips to `disproved`", "(`done`/`disproved`/`superseded`)"), and the
marker list matched the everyday words "no longer" and "instead of". On
2026-10-22 that pair fired on five cards at once — the
terminal-status-guard-missing-across-mutation-verbs hub and its four children,
each summary listing `done`/`disproved`/`superseded`, each decision saying
"_cmd_decide no longer refuses terminal cards" — and commit 413a2026 reworded
the decisions ("has stopped refusing") only to quiet the check.

Builds a scratch deck in a temporary directory through the real CLI: `goc new`
at a decision gate, a summary written into the frontmatter, `goc decide
--decision …`, then `goc validate`. Five cards:

  must stay silent (the false positives)
    status-name-x-everyday     summary only names the status; the decision
                               says "instead of" / "no longer" — the
                               2026-10-22 shape
    status-name-x-rescope      the same status-name summary under a genuine
                               re-scope decision — isolates the verdict side
    verdict-x-everyday         a genuine "REFUTED … do not pursue" summary
                               under a decision that only says "instead of" /
                               "no longer" — isolates the marker side
  must keep warning (the check's real target)
    verdict-x-reversal         "REFUTED … do not pursue" summary; the decision
                               reverses it ("Reverse: … now viable")
    verdict-x-no-longer-holds  "REFUTED" summary; the decision says the
                               refutation "no longer holds"

Exits 0 when every false positive is silent and every true positive still
warns (the defect no longer fires); exits 1 otherwise, naming each card that
broke its expectation.
"""

from __future__ import annotations

import os
import subprocess
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


REPO = _repo_root()

STATUS_NAME_SUMMARY = (
    "Probe whether the cache survives a restart; the card flips to `disproved` "
    "if the probe fails, or the card is disproved by the next release."
)
VERDICT_SUMMARY = "REFUTED: approach X never converges. Do not pursue it."
EVERYDAY_DECISION = (
    "Use the shared helper instead of the inline check; _cmd_decide no longer "
    "refuses terminal cards, so there is no message left to mirror."
)

# title -> (summary, decision, expected_warning)
CASES: dict[str, tuple[str, str, bool]] = {
    "status-name-x-everyday": (STATUS_NAME_SUMMARY, EVERYDAY_DECISION, False),
    "status-name-x-rescope": (
        STATUS_NAME_SUMMARY,
        "Re-scope: probe the cache on warm restarts only.",
        False,
    ),
    "verdict-x-everyday": (VERDICT_SUMMARY, EVERYDAY_DECISION, False),
    "verdict-x-reversal": (
        VERDICT_SUMMARY,
        "Reverse the verdict: approach X is now viable under condition Y.",
        True,
    ),
    "verdict-x-no-longer-holds": (
        VERDICT_SUMMARY,
        "Pursue approach X: the refutation no longer holds under condition Y.",
        True,
    ),
}


def _goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(REPO), env.get("PYTHONPATH")]))
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _must(result: subprocess.CompletedProcess[str], what: str) -> None:
    if result.returncode != 0:
        raise SystemExit(f"{what} failed:\n{result.stdout}\n{result.stderr}")


def _file_and_decide(cwd: Path, title: str, summary: str, decision: str) -> None:
    _must(_goc(cwd, "new", title, "--gate", "decision", "--tag", "story"), f"goc new {title}")
    readme = cwd / ".game-of-cards" / "deck" / title / "README.md"
    escaped = summary.replace("\\", "\\\\").replace('"', '\\"')
    readme.write_text(
        readme.read_text().replace(
            f"title: {title}\n", f'title: {title}\nsummary: "{escaped}"\n', 1
        )
    )
    _must(
        _goc(cwd, "decide", title, "--decision", decision, "--because", "Scratch-deck reproducer."),
        f"goc decide {title}",
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / ".game-of-cards" / "deck").mkdir(parents=True)
        for title, (summary, decision, _) in CASES.items():
            _file_and_decide(cwd, title, summary, decision)
        stderr = _goc(cwd, "validate").stderr

    broken: list[str] = []
    for title, (_, _, expected) in CASES.items():
        warned = f"WARN DECISION_CONTRADICTS_VERDICT {title}" in stderr
        verdict = "ok" if warned == expected else "BROKEN"
        print(f"{verdict:6} {title:27} warned={warned} expected={expected}")
        if warned != expected:
            broken.append(title)

    if broken:
        print(f"\nBUG: {len(broken)} card(s) broke their expectation: {', '.join(broken)}")
        return 1
    print("\nOK: status-name mentions and everyday words stay silent; "
          "genuine verdict reversals still warn.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
