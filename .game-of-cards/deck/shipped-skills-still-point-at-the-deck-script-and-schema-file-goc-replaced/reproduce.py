#!/usr/bin/env python3
"""Do the shipped skills name files a goc install never creates?

The deck skill's layout block lists `SCHEMA.md`, `README.md` and `deck.py`
inside the deck directory; `deck/reference.md` calls `deck.py` the engine; and
`refine-deck` schedules a new tag as "a SCHEMA.md PR". This script runs
`goc install --agents claude --local-skills` into a scratch git repo, so the
skills land in the consumer tree exactly as shipped, then checks:

1. which of `SCHEMA.md`, `deck.py` and `.game-of-cards/deck/README.md` the
   install created anywhere;
2. which lines of the installed skills name `SCHEMA.md` or `deck.py`, or list
   a `README.md` directly under the layout block's deck root.

Exits 1 while an installed skill names a file the install did not create, 0
when none does.
"""

from __future__ import annotations

import os
import re
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


ROOT = _repo_root()
NAMES = re.compile(r"\bdeck\.py\b|\bSCHEMA\.md\b")
LAYOUT_ROOT_README = re.compile(r"^  README\.md\s+#")  # a README.md one level under `deck/`


def _env() -> dict[str, str]:
    drop = {"CLAUDECODE", "CLAUDE_CODE", "CLAUDE_PROJECT_DIR", "CLAUDE_PLUGIN_ROOT", "GOC_WORKER"}
    env = {k: v for k, v in os.environ.items() if k not in drop and not k.startswith("GIT_")}
    env["PYTHONPATH"] = str(ROOT)
    return env


def install(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=_env())
    done = subprocess.run(
        [sys.executable, "-m", "goc.cli", "install", "--agents", "claude", "--local-skills"],
        cwd=repo, env=_env(), capture_output=True, text=True,
    )
    if done.returncode != 0:
        raise SystemExit(f"goc install failed (exit {done.returncode}):\n{done.stdout}{done.stderr}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="goc-phantom-files-") as tmp:
        repo = Path(tmp) / "consumer"
        install(repo)
        created = sorted(
            str(p.relative_to(repo)) for p in repo.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(repo).parts
        )
        phantom = [f for f in created if Path(f).name in {"SCHEMA.md", "deck.py"}]
        deck_readme = (repo / ".game-of-cards" / "deck" / "README.md").exists()
        print(f"goc install --agents claude --local-skills wrote {len(created)} files.")
        print(f"  files named SCHEMA.md or deck.py among them: {phantom or 'none'}")
        print(f"  .game-of-cards/deck/README.md exists: {deck_readme}")
        print(f"  .game-of-cards/deck/ holds: {sorted(p.name for p in (repo / '.game-of-cards' / 'deck').iterdir()) if (repo / '.game-of-cards' / 'deck').is_dir() else 'no such directory'}")

        mentions = []
        for rel in created:
            if not rel.startswith(".claude/skills/") or not rel.endswith(".md"):
                continue
            lines = (repo / rel).read_text(encoding="utf-8").splitlines()
            in_layout = False
            for lineno, line in enumerate(lines, 1):
                if line.strip() == "deck/":
                    in_layout = True
                elif in_layout and line.startswith("```"):
                    in_layout = False
                if NAMES.search(line) or (in_layout and LAYOUT_ROOT_README.match(line) and not deck_readme):
                    mentions.append(f"{rel}:{lineno}: {line.strip()}")

    if phantom or not mentions:
        print("\nNo installed skill names a file the install did not create.")
        return 0
    print(f"\n{len(mentions)} installed skill line(s) name a file the install did not create:")
    for item in mentions:
        print(f"  - {item}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
