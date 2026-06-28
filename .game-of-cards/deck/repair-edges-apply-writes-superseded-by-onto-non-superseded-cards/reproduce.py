"""Demonstrate that `goc repair-edges --apply` completes a `supersedes`
half-edge by writing `superseded_by` onto a card whose status is NOT
`superseded`, reporting success (exit 0) while leaving the deck in a state
`goc validate` rejects with a NEW error the repair itself introduced.
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


def _goc(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(_repo_root()), "PATH": "/usr/bin:/bin"},
    )


def main() -> int:
    root = _repo_root()
    sys.path.insert(0, str(root))
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        for title in ("card-a", "card-b"):
            proc = _goc(["new", title, "--contribution", "low", "--gate", "none"], repo)
            if proc.returncode != 0:
                print(proc.stdout, proc.stderr)
                raise RuntimeError(f"goc new {title} failed")

        # Author the half-edge: B claims to supersede A, but A is open (not
        # superseded) and carries no inverse superseded_by.
        readme_b = repo / ".game-of-cards" / "deck" / "card-b" / "README.md"
        text = readme_b.read_text()
        assert "advanced_by: []" in text
        readme_b.write_text(
            text.replace(
                "advanced_by: []", "advanced_by: []\nsupersedes:\n  - card-a", 1
            )
        )

        repair = _goc(["repair-edges", "--apply"], repo)
        print(f"repair-edges --apply exit code: {repair.returncode}")
        print("  " + "\n  ".join(repair.stdout.strip().splitlines()))
        if repair.returncode == 0 and "repaired" in repair.stdout:
            failures += 1
            print(
                "FAIL repair-edges claimed success on a supersedes edge whose "
                "target is not status: superseded"
            )

        readme_a = (repo / ".game-of-cards" / "deck" / "card-a" / "README.md").read_text()
        if "superseded_by:\n  - card-b" in readme_a or "- card-b" in readme_a:
            failures += 1
            print("FAIL card-a (status: open) now carries superseded_by: [card-b]")

        validate = _goc(["validate"], repo)
        print(f"goc validate exit code after repair: {validate.returncode}")
        new_error = "superseded_by: non-empty requires status: superseded"
        for line in (validate.stdout + validate.stderr).splitlines():
            if "card-a" in line or "card-b" in line:
                print("  " + line.strip())
        if new_error in validate.stdout + validate.stderr:
            failures += 1
            print(
                "FAIL the repair INTRODUCED a validator error the verb cannot "
                f"fix: '{new_error}'"
            )

    if failures:
        print(f"\n{failures} defect signal(s) — repair traded a half-edge for a validator-rejected state and reported success.")
        return 1
    print("\nDefect no longer fires: invalid supersession half-edges are routed to structural review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
