"""Reproduce: SessionStart hook strips quotes asymmetrically across readers.

Builds a temp deck containing:
  - (a) bare `status: active`, bare `human_gate: none`        (control: resumable)
  - (b) quoted `status: "active"`, bare `human_gate: none`     (bug: silently dropped;
                                                                 expected: resumable)
  - (c) bare `status: active`, quoted `human_gate: "none"`     (bug: framed as parked;
                                                                 expected: resumable)

Runs the SessionStart hook against that deck. The `_card_status` and
`_card_human_gate` readers do NOT strip outer quotes (unlike
`_card_waiting_on` and `_card_waiting_until`). So (b) is filtered out
of the active set entirely and (c) is reported as parked because the
gate value `'"none"'` is not equal to `"none"`.
"""

from __future__ import annotations

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
    "a-bare-bare": """---
title: a-bare-bare
status: active
human_gate: none
---
""",
    "b-quoted-status": """---
title: b-quoted-status
status: "active"
human_gate: none
---
""",
    "c-quoted-gate": """---
title: c-quoted-gate
status: active
human_gate: "none"
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
    impeded_line = ""
    for line in out.splitlines():
        if "Active card(s):" in line:
            resumable_line = line
        elif "Parked active card(s)" in line:
            parked_line = line
        elif "Impeded active card(s)" in line:
            impeded_line = line

    fails: list[str] = []

    # Expected (after fix): all three cards in the resumable bucket.
    # Observed (current bug):
    #   - (b) silently dropped (not in any bucket) because quoted status
    #     fails the `_card_status != "active"` check.
    #   - (c) framed as parked because quoted `human_gate` value
    #     `'"none"'` does not equal "none".
    if "b-quoted-status" not in resumable_line:
        fails.append(
            "DEFECT: b-quoted-status (status: \"active\") was MISCLASSIFIED — "
            "the quoted form caused `_card_status` to return '\"active\"', "
            "which fails the bare-form equality check and silently dropped "
            "the card from the active set."
        )
    if "c-quoted-gate" not in resumable_line:
        fails.append(
            "DEFECT: c-quoted-gate (human_gate: \"none\") was MISCLASSIFIED — "
            "the quoted form caused `_card_human_gate` to return '\"none\"', "
            "which is treated as a raised gate, framing a resumable card as "
            "parked."
        )

    # Sanity: (a) must be resumable under any reading.
    sanity = []
    if "a-bare-bare" not in resumable_line:
        sanity.append("SANITY: (a) should be resumable but isn't.")

    print()
    if fails:
        print("FAIL — defect reproduced:")
        for f in fails:
            print(f"  - {f}")
    else:
        print("PASS — hook tolerates quoted-form status/human_gate symmetrically.")
    for s in sanity:
        print(f"  - {s}")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
