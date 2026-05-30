"""Reproduce: `goc new --tag X --tag X` writes duplicate tags to disk.

Runs `goc new` in a fresh temp dir (so this repo's deck is untouched),
passes `--tag bug --tag bug --tag documentation --tag bug`, then prints
the `tags:` line from the produced README.

Expected behavior (after the fix): `tags: [bug, documentation]`.
Current behavior:                  `tags: [bug, bug, documentation, bug]`.

Exit code 0 when the defect FIRES (duplicates present); 1 when the fix has
landed (no duplicates).  Inverted from the usual TDD convention so DoD can
read "reproduce.py exits zero (defect no longer fires)" once the fix lands
by inverting the expected-vs-actual comparison at that time; the boolean
flips, the script stays a one-line reproducer.
"""

from __future__ import annotations

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


sys.path.insert(0, str(_repo_root()))


def main() -> int:
    repo = _repo_root()
    goc = repo / ".venv" / "bin" / "goc"
    if not goc.exists():
        # Fallback: install path used by `uv run goc` is the same venv;
        # try the system PATH as a last resort so the script is portable.
        goc = Path("goc")

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        subprocess.run(["git", "init", "-q"], cwd=td_path, check=True)
        subprocess.run([str(goc), "install"], cwd=td_path, check=True,
                       capture_output=True)
        subprocess.run(
            [
                str(goc), "new", "test-dedup-card",
                "--tag", "bug",
                "--tag", "bug",
                "--tag", "documentation",
                "--tag", "bug",
                "--contribution", "low",
            ],
            cwd=td_path,
            check=True,
        )
        readme = td_path / ".game-of-cards" / "deck" / "test-dedup-card" / "README.md"
        text = readme.read_text()
        tags_line = next(
            (line for line in text.splitlines() if line.startswith("tags:")),
            "(no tags: line found)",
        )
        print(f"tags written to disk: {tags_line.removeprefix('tags: ').strip()}")
        duplicates_present = tags_line.count("bug") > 1
        if duplicates_present:
            print("DUPLICATES PRESENT — defect fires.")
            return 0
        print("No duplicates — defect appears fixed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
