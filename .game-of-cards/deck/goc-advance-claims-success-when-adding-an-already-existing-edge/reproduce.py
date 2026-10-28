"""Check that `goc advance` on an edge already in place gives a signal distinct
from adding a new one.

The defect: a second `goc advance beta --by alpha`, with the edge alpha → beta
already in place, printed the same
`advance: beta.advanced_by += alpha; alpha.advances += beta` line as the first
call, exited 0 and rewrote both READMEs byte-identical — the signal a real
addition gives. Fixed, it is refused (non-zero exit, `ERROR:` on stderr, no
success line, nothing written), while the first call, which does add the
edge, still exits 0 with the success line.

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = the harness or
a precondition is broken.

Run with:  uv run python .game-of-cards/deck/goc-advance-claims-success-when-adding-an-already-existing-edge/reproduce.py
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


REPO = _repo_root()
sys.path.insert(0, str(REPO))

from goc.engine import parse_frontmatter  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        deck_root = Path(tmp) / "deck-root"
        gocdir = deck_root / ".game-of-cards"
        (gocdir / "deck").mkdir(parents=True)
        (gocdir / "config.yaml").write_text("skills_source: vendored\n")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
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

        def has_edge() -> bool:
            beta, _ = parse_frontmatter(readme("beta"))
            alpha, _ = parse_frontmatter(readme("alpha"))
            return "alpha" in (beta.get("advanced_by") or []) and "beta" in (alpha.get("advances") or [])

        def show(label: str, res: subprocess.CompletedProcess) -> None:
            print(f"$ goc advance beta --by alpha   # {label}")
            print(f"  exit {res.returncode}")
            print(f"  stdout: {res.stdout.strip() or '(empty)'}")
            print(f"  stderr: {res.stderr.strip() or '(empty)'}")

        for slug in ("alpha", "beta"):
            r = run_goc("new", slug, "--summary", f"Probe card {slug}.",
                        "--contribution", "low", "--gate", "none", "--tag", "bug")
            if r.returncode != 0:
                print(f"HARNESS: could not scaffold {slug}\n{r.stdout}{r.stderr}", file=sys.stderr)
                return 2
        if has_edge():
            print("PRECONDITION: alpha and beta already share an edge", file=sys.stderr)
            return 2

        # The control: the first call adds a new edge.
        first = run_goc("advance", "beta", "--by", "alpha", "--no-commit")
        show("edge not yet in place", first)
        if first.returncode != 0 or "advance:" not in first.stdout or not has_edge():
            print("HARNESS: adding a new edge failed — the control is broken", file=sys.stderr)
            return 2

        # The defect call: the same edge, now already in place.
        before = (readme("alpha"), readme("beta"))
        second = run_goc("advance", "beta", "--by", "alpha", "--no-commit")
        unchanged = before == (readme("alpha"), readme("beta"))
        show("edge already in place", second)

        refused = (
            second.returncode != 0
            and "ERROR:" in second.stderr
            and "advance:" not in second.stdout
            and unchanged
        )
        if refused:
            print("\nFIXED: an edge already in place is refused with nothing written; a new edge is still added.")
            return 0
        print("\nDEFECT FIRES: adding an edge already in place is not refused"
              f" (exit {second.returncode}, cards {'unchanged' if unchanged else 'REWRITTEN'}).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
