"""Reproduce: OpenClaw's prompt hook injects the deck-first reminder with no deck check.

Extracts the `before_prompt_build` handler from openclaw-plugin/index.ts and
reports whether it consults a deck before appending DECK_REMINDER. Exits 1
while the handler appends the reminder without any deck check (the defect
fires), 0 once it gates the reminder on a deck, 2 if the handler is gone.
"""

import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


INDEX_TS = _repo_root() / "openclaw-plugin" / "index.ts"
src = INDEX_TS.read_text(encoding="utf-8")
m = re.search(r'^( *)api\.on\("before_prompt_build".*?^\1\}\);$', src, re.MULTILINE | re.DOTALL)
if m is None:
    print(f"before_prompt_build handler not found in {INDEX_TS}")
    sys.exit(2)
handler = m.group(0)
line = src[: m.start()].count("\n") + 1
appends = "DECK_REMINDER" in handler
deck_checked = re.search(r"hasDeck\(|resolveDeckDir\(|\.game-of-cards", handler) is not None
print(f"openclaw-plugin/index.ts:{line} before_prompt_build handler")
print(f"  appends DECK_REMINDER:  {appends}")
print(f"  consults a deck first:  {deck_checked}")
if appends and not deck_checked:
    print("DEFECT FIRES: the reminder is injected in every workspace, opted in or not.")
    sys.exit(1)
print("ok: the reminder is gated on a deck.")
sys.exit(0)
