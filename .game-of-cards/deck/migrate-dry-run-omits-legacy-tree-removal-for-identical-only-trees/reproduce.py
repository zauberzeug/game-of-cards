"""Reproduce: `goc migrate --dry-run` hides the legacy-tree deletion when
every legacy card is identical to its canonical counterpart.

Real run reaches `shutil.rmtree(legacy)` whenever `to_copy or identical`
passes the confirm gate, but the dry-run preview only prints
"Would remove legacy tree" when `to_copy or not legacy_dirs` — omitting
the identical-only case. So the preview understates the one destructive
action the run will take, defeating the purpose of --dry-run.

Exits 0 when the bug is FIXED (dry-run announces the removal), 1 while
the bug is present.
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


REPO = _repo_root()

CARD_README = "---\ntitle: foo\nstatus: open\n---\n\n# foo\n"
CARD_LOG = ""


def _make_card(deck_dir: Path) -> None:
    card = deck_dir / "foo"
    card.mkdir(parents=True)
    (card / "README.md").write_text(CARD_README)
    (card / "log.md").write_text(CARD_LOG)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Make it look like a repo root so REPO_ROOT discovery / cwd is stable.
        (root / "pyproject.toml").write_text("[project]\nname = 'tmp'\n")

        # Identical-only situation: canonical and legacy each hold a byte-identical `foo`.
        _make_card(root / ".game-of-cards" / "deck")
        _make_card(root / "deck")

        env = {"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"}
        proc = subprocess.run(
            [sys.executable, "-m", "goc.cli", "migrate", "--dry-run"],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
        )
        out = proc.stdout

        print("--- goc migrate --dry-run output (identical-only legacy tree) ---")
        print(out, end="")
        print("--- end output ---")

        announces_removal = "Would remove legacy tree" in out
        # The legacy tree must still exist after a dry run (sanity: dry-run is non-destructive).
        legacy_intact = (root / "deck" / "foo" / "README.md").exists()

        print()
        print(f"dry-run announces 'Would remove legacy tree': {announces_removal}")
        print(f"legacy tree intact after dry-run (sanity):    {legacy_intact}")

        if not legacy_intact:
            print("\nUNEXPECTED: dry-run mutated the tree — different defect.")
            return 1

        if announces_removal:
            print("\nPASS: dry-run preview includes the legacy-tree removal it will perform.")
            return 0

        print(
            "\nFAIL: dry-run hid the legacy-tree deletion. The real `goc migrate`"
            " would rmtree the legacy tree, but --dry-run gave no warning."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
