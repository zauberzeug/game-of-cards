"""Reproduce: SessionStart hook frames `waiting_on` active cards as resumable.

Builds a temp deck containing:
  - (a) status: active, human_gate: none, no waiting_on   (truly resumable)
  - (b) status: active, human_gate: none, waiting_on: external
  - (c) status: active, human_gate: none, waiting_on: deferred, waiting_until: 2099-01-01
  - (d) status: active, human_gate: decision               (control: already correctly parked)

Runs the SessionStart hook against that deck. The current code bucks (b) and
(c) into the resumable line — the defect. (d) is reported in the parked line
thanks to the prior fix.
"""

from __future__ import annotations

import io
import json
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
HOOK = REPO / "goc" / "templates" / "hooks" / "deck_session_start.py"


CARDS = {
    "a-resumable-no-overlay": """---
title: a-resumable-no-overlay
status: active
human_gate: none
---
""",
    "b-impeded-external": """---
title: b-impeded-external
status: active
human_gate: none
waiting_on: external
---
""",
    "c-impeded-deferred-future": """---
title: c-impeded-deferred-future
status: active
human_gate: none
waiting_on: deferred
waiting_until: 2099-01-01
---
""",
    "d-control-gated": """---
title: d-control-gated
status: active
human_gate: decision
---
""",
}


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        deck = project / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        for name, body in CARDS.items():
            cdir = deck / name
            cdir.mkdir()
            (cdir / "README.md").write_text(body, encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"cwd": str(project)}),
            text=True,
            capture_output=True,
            check=False,
        )
        out = proc.stdout

    print("Hook stdout:")
    print(out)

    resumable_line = ""
    parked_line = ""
    for line in out.splitlines():
        if "Active card(s):" in line:
            resumable_line = line
        elif "Parked active card(s)" in line:
            parked_line = line

    fails: list[str] = []

    # Expected (after fix): only (a) is in the resumable bucket; (b), (c), (d) are parked/impeded.
    # Observed (current bug): (a), (b), (c) all in resumable; only (d) parked.

    if "b-impeded-external" in resumable_line:
        fails.append(
            "DEFECT: b-impeded-external (waiting_on: external) is framed as RESUMABLE."
        )
    if "c-impeded-deferred-future" in resumable_line:
        fails.append(
            "DEFECT: c-impeded-deferred-future (waiting_until=2099-01-01) is framed as RESUMABLE."
        )

    # Sanity: (a) should be resumable and (d) parked under the existing (correct) partition.
    sanity = []
    if "a-resumable-no-overlay" not in resumable_line:
        sanity.append("SANITY: (a) should be resumable but isn't.")
    if "d-control-gated" not in parked_line:
        sanity.append("SANITY: (d) should be parked but isn't.")

    print()
    if fails:
        print("FAIL — defect reproduced:")
        for f in fails:
            print(f"  - {f}")
    else:
        print("PASS — hook correctly partitions waiting_on impediments.")
    for s in sanity:
        print(f"  - {s}")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
