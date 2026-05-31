"""Reproduce: `goc validate` requires supersession + gate states no verb can produce.

Exercises the three independent failure modes against a throwaway deck:

  1. `goc status <X> superseded --by <Y>` is refused when <Y> is terminal
     (done / disproved / superseded) — so a card whose genuine successor
     is itself closed can never be recorded, and `goc validate` would
     reject the link even if hand-written.
  2. The successor of a supersession can never be closed: after
     `goc status A superseded --by B` (B live), `goc done B` is refused
     by the inbound-superseded_by close-time guard.
  3. `goc decide` refuses to lower a still-raised gate on a terminal card,
     leaving a card that is terminal AND human_gate != none permanently
     failing `goc validate` with no repair verb.

Exit code 0 means ALL THREE now behave correctly (the fix has landed):
terminal `--by` is accepted, the successor closes, and decide repairs the
gate. Non-zero means at least one defect still fires.
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


REPO_ROOT = _repo_root()


def run_goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(REPO_ROOT) if not pythonpath else f"{REPO_ROOT}{os.pathsep}{pythonpath}"
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def write_card(deck: Path, title: str, *, status: str = "open", gate: str = "none",
               closed: bool = False, dod_done: bool = False, extra: str = "") -> None:
    card_dir = deck / title
    card_dir.mkdir(parents=True, exist_ok=True)
    box = "[x]" if dod_done else "[ ]"
    closed_at = '"2026-05-15T00:00:00Z"' if closed else "null"
    (card_dir / "README.md").write_text(
        f"""---
title: {title}
summary: "Fixture for the validate-requires-impossible-state reproducer."
status: {status}
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: {closed_at}
human_gate: {gate}
advances: []
advanced_by: []
{extra}tags: [bug]
definition_of_done: |
  - {box} PROCESS: fixture
---

# {title}
"""
    )
    (card_dir / "log.md").write_text("")


def main() -> int:
    failures: list[str] = []

    # --- Mode 1: terminal --by successor must be ACCEPTED ----------------
    for term in ("done", "disproved", "superseded"):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            deck = cwd / ".game-of-cards" / "deck"
            write_card(deck, "origin", status="open")
            # A superseded successor needs its own --by to be valid; give the
            # 'superseded' fixture a live tail so validate stays clean.
            if term == "superseded":
                write_card(deck, "tail", status="open")
                write_card(
                    deck, "successor", status="superseded", closed=True, dod_done=True,
                    extra="superseded_by:\n  - tail\nsupersedes: []\n",
                )
                # wire the inverse on tail
                write_card(
                    deck, "tail", status="open",
                    extra="superseded_by: []\nsupersedes:\n  - successor\n",
                )
            else:
                write_card(deck, "successor", status=term, closed=True, dod_done=True)
            r = run_goc(cwd, "status", "origin", "superseded", "--by", "successor", "--no-commit")
            if r.returncode != 0:
                failures.append(
                    f"[mode1:{term}] `status superseded --by <{term}>` was REFUSED "
                    f"(exit {r.returncode}); expected acceptance. stderr: {r.stderr.strip()[:200]}"
                )

    # --- Mode 2: the successor of a supersession must be CLOSEABLE --------
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck = cwd / ".game-of-cards" / "deck"
        write_card(deck, "old-card", status="open")
        write_card(deck, "new-card", status="open", dod_done=True)
        r = run_goc(cwd, "status", "old-card", "superseded", "--by", "new-card", "--no-commit")
        if r.returncode != 0:
            failures.append(f"[mode2:setup] could not supersede old-card by new-card: {r.stderr.strip()[:200]}")
        else:
            r2 = run_goc(cwd, "done", "new-card")
            if r2.returncode != 0:
                failures.append(
                    f"[mode2] `goc done new-card` was REFUSED (exit {r2.returncode}) although it is "
                    f"the live successor of a supersession. stderr: {r2.stderr.strip()[:200]}"
                )

    # --- Mode 3: decide must repair a raised gate on a terminal card -----
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck = cwd / ".game-of-cards" / "deck"
        write_card(deck, "stuck-card", status="done", gate="decision", closed=True, dod_done=True)
        before = run_goc(cwd, "validate")
        if before.returncode == 0:
            failures.append("[mode3:precondition] validator unexpectedly accepted a terminal card with a raised gate")
        r = run_goc(cwd, "decide", "stuck-card", "--decision", "close out the stale gate",
                    "--because", "card already terminal; clearing dangling gate", "--no-commit")
        if r.returncode != 0:
            failures.append(
                f"[mode3] `goc decide` REFUSED to repair the raised gate on a terminal card "
                f"(exit {r.returncode}). stderr: {r.stderr.strip()[:200]}"
            )
        else:
            after = run_goc(cwd, "validate")
            if after.returncode != 0:
                failures.append(
                    f"[mode3] after `goc decide`, `goc validate` still fails: {(after.stdout + after.stderr).strip()[:200]}"
                )

    if failures:
        print("DEFECT REPRODUCED — at least one impossible state remains:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All three modes behave correctly: terminal --by accepted, successor closeable, gate repairable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
