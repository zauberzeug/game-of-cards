"""Prove _resolve_deck_dir misidentifies any top-level deck/ dir as a card deck,
and that the suggested remediation (`goc migrate --yes`) deletes it.

Sets up a consumer repo with an installed GoC deck (.game-of-cards/deck/)
plus an unrelated `deck/` folder (a slide deck: deck/slides/index.html,
deck/notes.txt). Shows:

  (a) every goc verb exits 1 with the dual-tree refusal (bare exists()
      check at engine.py — no card-shape or .goc-version sentinel gating,
      unlike install.py's _find_installed_deck_dir);
  (b) `goc migrate --yes` ingests deck/slides/ into the card deck, then
      shutil.rmtree's deck/ — destroying deck/notes.txt (top-level files
      are never copied; the migration loop only walks directories).

Defect proven when (a) exits nonzero with the dual-tree error and (b)
exits 0, deck/ is gone, and notes.txt's content exists nowhere.
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
NOTES = "presentation speaker notes — NOT a goc card\n"


def goc(consumer: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=consumer,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )


def main() -> int:
    consumer = Path(tempfile.mkdtemp(prefix="goc-deck-collision-")) / "repo"
    (consumer / ".game-of-cards" / "deck").mkdir(parents=True)
    slides = consumer / "deck" / "slides"
    slides.mkdir(parents=True)
    (slides / "index.html").write_text("<html>slide deck</html>\n")
    (consumer / "deck" / "notes.txt").write_text(NOTES)

    listing = goc(consumer)
    print(f"[goc (list)] exit={listing.returncode}")
    err = (listing.stderr or listing.stdout).strip().splitlines()
    print(f"  stderr: {err[0] if err else '<empty>'}")
    blocked = listing.returncode != 0 and "deck tree" in (listing.stderr + listing.stdout)

    migrate = goc(consumer, "migrate", "--yes")
    print(f"[goc migrate --yes] exit={migrate.returncode}")
    for line in migrate.stdout.strip().splitlines():
        print(f"  {line}")

    legacy_gone = not (consumer / "deck").exists()
    notes_survives = any(
        p.is_file() and p.read_text() == NOTES for p in consumer.rglob("*")
    )
    junk_in_deck = (consumer / ".game-of-cards" / "deck" / "slides").exists()
    print(f"\nlegacy deck/ removed:              {legacy_gone}")
    print(f"notes.txt content survives anywhere: {notes_survives}")
    print(f"slides/ ingested as a 'card':        {junk_in_deck}")

    if blocked and migrate.returncode == 0 and legacy_gone and not notes_survives:
        print(
            "\nDEFECT CONFIRMED: an unrelated deck/ folder hard-blocks every verb,"
            " and the suggested `goc migrate` destroys its top-level files and"
            " ingests its subdirectories as cards."
        )
        return 0
    print("\nDefect no longer fires (or output shape changed) — inspect manually.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
