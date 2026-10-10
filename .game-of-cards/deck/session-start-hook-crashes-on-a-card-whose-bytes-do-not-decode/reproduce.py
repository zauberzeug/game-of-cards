"""Reproduce: the SessionStart hook crashes on a card whose bytes do not decode.

Builds a scratch deck holding one active, gate-free card and one card whose
README.md carries a single Latin-1 byte (0xE9), then runs the shipped hook
template the way Claude Code does: JSON on stdin naming the project as
`cwd`. The hook reads cards with `encoding="utf-8"`, so the premise holds on
any host.

Exits non-zero while the hook fails to exit 0 with the active card's
reminder.
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


HOOK = _repo_root() / "goc" / "templates" / "hooks" / "deck_session_start.py"

CARD = (
    "---\n"
    "title: {title}\n"
    'summary: "{summary}"\n'
    "status: {status}\n"
    "human_gate: none\n"
    "---\n\n"
    "# {title}\n"
)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        deck = project / ".game-of-cards" / "deck"
        for title, summary, status in (
            ("claimed-card", "fine", "active"),
            ("bad-bytes", "caf\xe9", "open"),
        ):
            (deck / title).mkdir(parents=True)
            text = CARD.format(title=title, summary=summary, status=status)
            (deck / title / "README.md").write_bytes(text.encode("latin-1"))

        payload = {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(project)}
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload), capture_output=True, text=True, cwd=project,
        )

    print(f"hook exit: {proc.returncode}")
    print(f"stdout: {proc.stdout.strip()!r}")
    if proc.stderr.strip():
        print(f"stderr (last line): {proc.stderr.strip().splitlines()[-1]}")
    if proc.returncode != 0 or "claimed-card" not in proc.stdout:
        print("[FAIL] one undecodable card stops the hook before it prints any reminder.")
        return 1
    print("[OK] the hook skips the undecodable card and still reminds about claimed-card.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
