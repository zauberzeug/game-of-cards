"""Reproduce: SessionStart hook misreads frontmatter fields with inline YAML comments.

Constructs a temp deck with one card whose four frontmatter fields each carry
a trailing ` # comment`. Invokes the four hook readers and asserts the raw
return value still contains the comment text — the defect signature.

Exits 0 once the fix lands (all four readers return the comment-free value);
exits 1 while the defect is live.
"""

from __future__ import annotations

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


sys.path.insert(0, str(_repo_root()))

from goc.templates.hooks import deck_session_start  # noqa: E402


CARD = """\
---
title: test-card
status: active # resumable note
human_gate: decision # parked
waiting_on: external # see GH-123
waiting_until: 2026-06-05 # deferred
---
body
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        readme = Path(tmp) / "README.md"
        readme.write_text(CARD)
        status = deck_session_start._card_status(readme)
        gate = deck_session_start._card_human_gate(readme)
        waiting_on = deck_session_start._card_waiting_on(readme)
        waiting_until = deck_session_start._card_waiting_until(readme)

    rows = [
        ("status raw   ", repr(status),        "'active'"),
        ("human_gate   ", repr(gate),          "'decision'"),
        ("waiting_on   ", repr(waiting_on),    "'external'"),
        ("waiting_until", repr(waiting_until), "'2026-06-05'"),
    ]
    for label, got, expected in rows:
        print(f"{label}= {got:<35} expected {expected}")

    leaked = (
        "#" in (status or "")
        or "#" in (gate or "")
        or "#" in (waiting_on or "")
        or "#" in (waiting_until or "")
    )
    if leaked:
        print("DEFECT: all four readers leak the inline YAML comment into the value")
        return 1
    print("OK: all four readers strip the inline YAML comment")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
