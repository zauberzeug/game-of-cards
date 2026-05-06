"""Demonstrate that `goc move` leaves stale references and writes no log entry.

Sets up an isolated temp deck root, scaffolds two cards (one with a body
that references the other via the documented `[<title>](../<title>/)`
form), runs `goc move` on the referenced card, and inspects:

  1. moved card's H1 heading (should be the new title)
  2. moved card's log.md (should record the rename)
  3. other card's body (relative-link reference should track the new slug)

Exits 0 once `goc move` rewrites all three surfaces; exits 1 while the
defect is live.
"""

import os
import shutil
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


def _run(cmd, cwd, env, check=True):
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True)
    if check and proc.returncode != 0:
        sys.stderr.write(f"$ {' '.join(cmd)}\nstdout: {proc.stdout}\nstderr: {proc.stderr}\n")
        proc.check_returncode()
    return proc


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="goc-move-repro-"))
    try:
        # Minimal repo: pyproject + .game-of-cards/deck/
        (tmp / "pyproject.toml").write_text("[project]\nname='probe'\nversion='0'\n")
        deck = tmp / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        env = {**os.environ, "PYTHONPATH": str(REPO)}

        # Scaffold two cards from a clean cwd.
        _run(
            [sys.executable, "-m", "goc.cli", "new", "alpha-card", "--gate", "none"],
            cwd=tmp, env=env,
        )
        _run(
            [sys.executable, "-m", "goc.cli", "new", "beta-card", "--gate", "none"],
            cwd=tmp, env=env,
        )

        # Add a body cross-link in beta → alpha (the documented form).
        beta_readme = deck / "beta-card" / "README.md"
        beta_text = beta_readme.read_text()
        beta_text += "\n\nReferences [alpha-card](../alpha-card/) for prior art.\n"
        beta_readme.write_text(beta_text)

        # Run the rename.
        _run(
            [sys.executable, "-m", "goc.cli", "move", "alpha-card", "alpha-card-renamed"],
            cwd=tmp, env=env,
        )

        moved_dir = deck / "alpha-card-renamed"
        moved_readme = moved_dir / "README.md"
        moved_log = moved_dir / "log.md"

        moved_body = moved_readme.read_text()
        h1_stale = "# alpha-card\n" in moved_body and "# alpha-card-renamed\n" not in moved_body

        log_text = moved_log.read_text() if moved_log.exists() else ""
        log_missing = "renamed from" not in log_text and "alpha-card" not in log_text

        beta_body = beta_readme.read_text()
        beta_link_stale = "../alpha-card/" in beta_body

        print("--- after `goc move alpha-card alpha-card-renamed` ---")
        print(f"  moved card H1 still says `# alpha-card` (stale)?      {h1_stale}")
        print(f"  moved card log.md has no rename entry?                  {log_missing}")
        print(f"  beta-card body still links to ../alpha-card/ (stale)?  {beta_link_stale}")
        print()
        print("--- moved README.md (head) ---")
        print("\n".join(moved_body.splitlines()[:20]))
        print()
        print("--- moved log.md ---")
        print(repr(log_text))
        print()
        print("--- beta-card body (tail) ---")
        print("\n".join(beta_body.splitlines()[-5:]))
        print()

        defects = sum([h1_stale, log_missing, beta_link_stale])
        print(f"defects observed: {defects} / 3")
        return 0 if defects == 0 else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
