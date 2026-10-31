"""Reproduce: `goc attest` fails its closure-entry check on a closure heading
dated any UTC day other than the one attest runs on.

The `log-md-closure-entry` check (`_run_derived_check` in `goc/engine.py`)
accepted only a `## <date>[T<time>Z] — Closure` heading dated attest's own UTC
day. A closure entry written before UTC midnight and attested after it — or
re-attested on any later day, say once an `advanced_by` prerequisite closes —
then reads as missing, and since log.md is append-only the only way back to a
pass is a second closure entry.

Two probes:

1. Predicate. A log.md holding `## 2026-05-26T23:59:00Z — Closure`, checked
   with attest's `today` one day later (`2026-05-27T00:01:00Z`), as the card's
   DoD names it. The same question is asked of a legacy date-only heading from
   that day and of a heading three days old. A log.md without any closure
   heading is the control: the check must still fail it, or a pass on the
   other cases proves nothing.

2. Shipped path. The real `goc attest --non-interactive`, run in a subprocess
   against a throwaway deck whose card log holds a closure heading stamped
   23:59:00Z yesterday by the real UTC clock. That is exactly the log a
   closure entry written before midnight leaves for an attest run after it,
   so no clock is faked: the engine reads its own wall clock, as it does in
   production.

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = harness or
precondition broken.

Run via `uv run python .game-of-cards/deck/closure-log-attestation-misfires-across-utc-midnight/reproduce.py`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


REPO_ROOT = _repo_root()
sys.path.insert(0, str(REPO_ROOT))

from goc import engine  # noqa: E402

TITLE = "dummy-closing-card"
CHECK = "log-md-closure-entry"
ATTEST_TODAY = "2026-05-27T00:01:00Z"

CARD_README = f"""\
---
title: {TITLE}
summary: "An active card about to close, used to reproduce the closure-entry misfire."
status: active
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: the work is done
---

# {TITLE}

Ready to close.
"""

CONFIG = """\
layer_2_project_dod: []
layer_3_goc_dod:
  - name: advanced-by-closed
    kind: derived
  - name: dod-100-percent
    kind: derived
  - name: log-md-closure-entry
    kind: derived
workflow:
  auto_commit: false
"""


def _closure_log(stamp: str) -> str:
    return f"## {stamp} — Closure\n\n- **What changed**: the fix landed.\n"


# (label, log.md text, the verdict a correct check returns)
PREDICATE_CASES = (
    ("heading written 23:59:00Z the day before", _closure_log("2026-05-26T23:59:00Z"), True),
    ("legacy date-only heading from the day before", _closure_log("2026-05-26"), True),
    ("heading written three days before", _closure_log("2026-05-24T10:00:00Z"), True),
)
CONTROL_LOG = "## 2026-05-26T23:50:00Z: decision recorded\n\nNo closure entry yet.\n"


def _run_predicate(log_text: str) -> tuple[bool, str]:
    """Ask `_run_derived_check` about `log_text`, with attest's `today` injected."""
    deck = Path(tempfile.mkdtemp(prefix="goc-closure-predicate-"))
    previous = engine.DECK_DIR
    try:
        card_dir = deck / TITLE
        card_dir.mkdir()
        (card_dir / "log.md").write_text(log_text)
        card = engine.Card(
            title=TITLE,
            path=card_dir,
            frontmatter={"title": TITLE, "status": "active", "advanced_by": [], "advances": []},
            body="",
            dod_open=0,
            dod_done=1,
        )
        engine.DECK_DIR = deck
        return engine._run_derived_check({"name": CHECK}, card, [card], ATTEST_TODAY)
    finally:
        engine.DECK_DIR = previous
        shutil.rmtree(deck, ignore_errors=True)


def _probe_predicate() -> int:
    print("=" * 72)
    print(f"Probe 1 — predicate, attest `today` = {ATTEST_TODAY}")
    print("=" * 72)

    control_ok, control_summary = _run_predicate(CONTROL_LOG)
    print(f"  control (no closure heading)  -> {control_ok}: {control_summary}")
    if control_ok:
        print(
            "PRECONDITION BROKEN: the check passes a log.md with no closure heading, "
            "so its verdict on the cases below proves nothing."
        )
        return 2

    misfires = 0
    for label, log_text, expected in PREDICATE_CASES:
        ok, summary = _run_predicate(log_text)
        verdict = "ok" if ok == expected else "MISFIRE"
        print(f"  {label:<45} -> {ok}: {summary}   [{verdict}]")
        if ok != expected:
            misfires += 1
    print()
    return 1 if misfires else 0


def _probe_attest_path() -> int:
    now = datetime.now(tz=timezone.utc)
    yesterday = (now - timedelta(days=1)).date().isoformat()
    stamp = f"{yesterday}T23:59:00Z"
    print("=" * 72)
    print("Probe 2 — shipped path: `goc attest --non-interactive`, real UTC clock")
    print("=" * 72)
    print(f"real UTC now:          {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"closure heading stamp: {stamp}  (written one minute before last midnight)")

    workdir = Path(tempfile.mkdtemp(prefix="goc-closure-attest-"))
    try:
        subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
        subprocess.run(["git", "config", "user.email", "x@y"], cwd=workdir, check=True)
        subprocess.run(["git", "config", "user.name", "x"], cwd=workdir, check=True)
        (workdir / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
        (workdir / ".game-of-cards").mkdir()
        (workdir / ".game-of-cards" / "config.yaml").write_text(CONFIG)
        card_dir = workdir / ".game-of-cards" / "deck" / TITLE
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(CARD_README)
        (card_dir / "log.md").write_text(_closure_log(stamp))

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        env.pop("GOC_WORKTREE_DECK", None)
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "attest", TITLE, "--non-interactive"],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"HARNESS BROKEN: {exc}")
        return 2
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print("exit code:", result.returncode)
    print("--- stdout ---")
    print(result.stdout.rstrip())
    print("--- stderr ---")
    print(result.stderr.rstrip())
    print()

    if f"[ ] {CHECK}" in result.stdout:
        return 1
    if f"[x] {CHECK}" in result.stdout and result.returncode == 0:
        return 0
    print(
        f"HARNESS BROKEN: attest neither passed nor failed `{CHECK}` cleanly "
        "(or another check failed); inspect the output above."
    )
    return 2


def main() -> int:
    verdicts = [_probe_predicate(), _probe_attest_path()]
    if 2 in verdicts:
        return 2
    if 1 in verdicts:
        print(
            "DEFECT REPRODUCED: the closure-entry check rejects a well-formed "
            "`## <stamp> — Closure` heading because it is dated a UTC day other "
            "than attest's own — the state every closure entry written before "
            "midnight and attested after it is in."
        )
        return 1
    print(
        "No defect — the closure-entry check accepts a well-formed closure "
        "heading whatever UTC day it names, and still fails a log without one."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
