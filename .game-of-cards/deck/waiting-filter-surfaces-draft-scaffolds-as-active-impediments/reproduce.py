"""Proof that `goc --waiting` surfaces a `draft: true` scaffold that carries a
`waiting_on` overlay, while the board renders the same card with the `✎` draft
glyph and never the `⏳` impediment glyph — the two human-facing views disagree.

Exercises the REAL shipping code path: builds a temp deck with `goc new` +
`goc wait`, then runs `goc --waiting` and `goc --board` and inspects the output.

Run: uv run python .game-of-cards/deck/waiting-filter-surfaces-draft-scaffolds-as-active-impediments/reproduce.py

Exits 0 once the defect is fixed (draft no longer appears in `--waiting`);
exits 1 while the defect is present.
"""
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


def _goc(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    return proc.stdout + proc.stderr


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / ".game-of-cards" / "deck").mkdir(parents=True)
        (repo / ".game-of-cards" / "config.yaml").write_text("skills_source: vendored\n")

        _goc(repo, "new", "freshdraft", "--contribution", "medium")
        _goc(repo, "wait", "freshdraft", "--reason", "external")

        waiting_out = _goc(repo, "--waiting", "--no-color")
        board_out = _goc(repo, "--board", "--no-color")

        in_waiting = "freshdraft" in waiting_out
        board_line = next(
            (ln for ln in board_out.splitlines() if "freshdraft" in ln), ""
        )
        board_impediment = "⏳" in board_line
        board_draft = "✎" in board_line

        print("=== goc --waiting ===")
        print(waiting_out.strip() or "(empty)")
        print("\n=== board line ===")
        print(board_line or "(card absent from board)")
        print()
        print(f"draft appears in --waiting : {in_waiting}")
        print(f"board shows ⏳ impediment   : {board_impediment}")
        print(f"board shows ✎ draft        : {board_draft}")

        if in_waiting and not board_impediment:
            print(
                "\nFAIL: --waiting surfaces the draft as an impediment while the "
                "board suppresses it (shows ✎, not ⏳) — the two views disagree."
            )
            return 1

        print("\nOK: --waiting and the board agree (draft excluded from --waiting).")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
