"""Check that `goc unadvance` on a non-existent edge gives a signal distinct
from removing a real one.

The defect: `goc unadvance alpha --by beta` with no edge between the two cards
printed `unadvance: alpha.advanced_by -= beta; beta.advances -= alpha`, exited
0 and rewrote both READMEs byte-identical — the same signal a real removal
gives. Fixed, it is refused (non-zero exit, `ERROR:` on stderr, no success
line, nothing written), while removing a real edge still exits 0 with the
success line.

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = the harness or
a precondition is broken.

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

    with tempfile.TemporaryDirectory() as tmp:
        deck_root = Path(tmp) / "deck-root"
        gocdir = deck_root / ".game-of-cards"
        (gocdir / "deck").mkdir(parents=True)
        (gocdir / "config.yaml").write_text("skills_source: vendored\n")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo) + os.pathsep + env.get("PYTHONPATH", "")
        env.pop("GOC_WORKTREE_DECK", None)

        def run_goc(*argv: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, "-m", "goc.cli", *argv],
                cwd=deck_root,
                env=env,
                capture_output=True,
                text=True,
            )

        def readme(slug: str) -> str:
            return (gocdir / "deck" / slug / "README.md").read_text()

        # alpha and beta stay unrelated; gamma advances delta (the control).
        for slug in ("alpha", "beta", "gamma", "delta"):
            r = run_goc("new", slug, "--summary", f"Probe card {slug}.",
                        "--contribution", "low", "--gate", "none", "--tag", "bug")
            if r.returncode != 0:
                print(f"HARNESS: could not scaffold {slug}\n{r.stdout}{r.stderr}", file=sys.stderr)
                return 2
        r = run_goc("advance", "delta", "--by", "gamma", "--no-commit")
        if r.returncode != 0:
            print(f"HARNESS: could not wire gamma → delta\n{r.stdout}{r.stderr}", file=sys.stderr)
            return 2
        if "advanced_by: []" not in readme("alpha") or "advances: []" not in readme("beta"):
            print("PRECONDITION: alpha and beta already share an edge", file=sys.stderr)
            return 2

        # The defect call: unadvance an edge that does not exist.
        before = (readme("alpha"), readme("beta"))
        missing = run_goc("unadvance", "alpha", "--by", "beta", "--no-commit")
        unchanged = before == (readme("alpha"), readme("beta"))
        print("$ goc unadvance alpha --by beta   # no such edge")
        print(f"  exit {missing.returncode}")
        print(f"  stdout: {missing.stdout.strip() or '(empty)'}")
        print(f"  stderr: {missing.stderr.strip() or '(empty)'}")

        # The control: unadvance an edge that does exist.
        real = run_goc("unadvance", "delta", "--by", "gamma", "--no-commit")
        print("$ goc unadvance delta --by gamma  # real edge")
        print(f"  exit {real.returncode}")
        print(f"  stdout: {real.stdout.strip() or '(empty)'}")
        removed = "gamma" not in readme("delta") and "delta" not in readme("gamma")
        if real.returncode != 0 or not removed:
            print("HARNESS: removing a real edge failed — the control is broken", file=sys.stderr)
            return 2

        refused = (
            missing.returncode != 0
            and "ERROR:" in missing.stderr
            and "unadvance:" not in missing.stdout
            and unchanged
        )
        if refused:
            print("\nFIXED: a non-existent edge is refused with nothing written; a real edge is still removed.")
            return 0
        print("\nDEFECT FIRES: removing a non-existent edge is not refused"
              f" (exit {missing.returncode}, cards {'unchanged' if unchanged else 'REWRITTEN'}).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
