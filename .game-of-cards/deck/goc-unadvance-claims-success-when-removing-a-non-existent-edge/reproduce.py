"""Demonstrate that `goc unadvance` prints a confident success message and
exits 0 even when no edge exists between the two cards.

Run with:  uv run python .game-of-cards/deck/goc-unadvance-claims-success-when-removing-a-non-existent-edge/reproduce.py
"""

import os
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


def main() -> int:
    repo = _repo_root()
    sys.path.insert(0, str(repo))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        deck_root = tmp_path / "deck-root"
        deck_root.mkdir()

        # Minimal scaffolding so the engine recognises tmp_path as a deck.
        gocdir = deck_root / ".game-of-cards"
        (gocdir / "deck").mkdir(parents=True)
        (gocdir / "config.yaml").write_text("skills_source: vendored\n")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo) + os.pathsep + env.get("PYTHONPATH", "")

        def run_goc(*argv: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, "-m", "goc.cli", *argv],
                cwd=deck_root,
                env=env,
                capture_output=True,
                text=True,
            )

        # Create two unrelated cards (no edge between them).
        for slug in ("alpha", "beta"):
            r = run_goc("new", slug, "--contribution", "low", "--gate", "none", "--tag", "bug")
            if r.returncode != 0:
                print("FAILED to scaffold card:", slug, file=sys.stderr)
                print(r.stdout, r.stderr, file=sys.stderr)
                return 2

        # Sanity: alpha has no advanced_by and beta has no advances.
        alpha_readme = (gocdir / "deck" / "alpha" / "README.md").read_text()
        beta_readme = (gocdir / "deck" / "beta" / "README.md").read_text()
        assert "advanced_by: []" in alpha_readme, "precondition failed: alpha already has an advanced_by edge"
        assert "advances: []" in beta_readme, "precondition failed: beta already has an advances edge"

        # The defect call: unadvance an edge that does not exist.
        result = run_goc("unadvance", "alpha", "--by", "beta", "--no-commit")

        print("--- stdout ---")
        print(result.stdout, end="")
        print("--- stderr ---")
        print(result.stderr, end="")
        print(f"--- exit code: {result.returncode} ---")

        # Re-read both cards and confirm zero change on disk.
        alpha_after = (gocdir / "deck" / "alpha" / "README.md").read_text()
        beta_after = (gocdir / "deck" / "beta" / "README.md").read_text()
        unchanged = (alpha_after == alpha_readme) and (beta_after == beta_readme)

        # The defect predicates: success message printed, exit 0, files unchanged.
        defect = (
            "unadvance: alpha.advanced_by -= beta; beta.advances -= alpha" in result.stdout
            and result.returncode == 0
            and unchanged
        )

        if defect:
            print()
            print("DEFECT CONFIRMED:")
            print("  - exit code 0 (no error signalled)")
            print("  - stdout asserts the edge was removed")
            print("  - both README files are byte-identical to their pre-call contents")
            print("  - no warning on stderr that the edge did not exist")
            return 0

        print("DEFECT NOT REPRODUCED — fix may have landed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
