"""Reproduce: shared worktree-deck mode finds no deck when the repository is a bare clone.

Builds the README's Falsification-recipe layout: a bare clone `repo.git` whose
one linked worktree `wt-feat` holds its own deck and opts into the shared deck
in its own `.game-of-cards/config.yaml`. From that worktree it runs
`goc --status all` and `goc new`, first with only the config opt-in, then with
`GOC_WORKTREE_DECK=shared` as well, and prints what each run does.

Shared mode reads the deck from the primary working tree, which a bare clone
does not have. The defect fires when a run in this layout
  - reports a missing deck: the worktree holds one, and the notice names a
    directory goc did not search;
  - fails to file the card with `goc new`; or
  - says nothing that names the bare repository and says the layout has no
    primary working tree, so the opt-in is dropped silently.

Exit 1 while the defect fires, 0 once it is fixed.
"""

from __future__ import annotations

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


ROOT = _repo_root()
LAUNCHER = ROOT / "goc" / "_launch.py"
# The phrase every skill Preflight routes to Skill(kickoff) on
# (`goc.engine.MISSING_DECK_PHRASE`), spelled out so this script does not
# import the engine it probes.
MISSING_DECK_PHRASE = "no such file or directory: .game-of-cards/deck/"
NO_PRIMARY = "no primary working tree"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def goc(cwd: Path, *args: str, **extra: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    for key in ("GOC_WORKTREE_DECK", "GOC_WORKER", "CLAUDE_PLUGIN_ROOT"):
        env.pop(key, None)
    env.update(extra)
    return subprocess.run([sys.executable, str(LAUNCHER), *args], cwd=cwd,
                          env=env, capture_output=True, text=True)


def build(tmp: Path) -> tuple[Path, Path]:
    """The recipe's layout: (bare repository, linked worktree)."""
    src = tmp / "src"
    src.mkdir()
    git(src, "init", "-q", "-b", "main")
    (src / "f").write_text("x\n")
    git(src, "add", "f")
    git(src, "-c", "user.name=probe", "-c", "user.email=probe@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-q", "-m", "init")
    bare = tmp / "repo.git"
    git(tmp, "clone", "-q", "--bare", str(src), str(bare))
    worktree = tmp / "wt-feat"
    git(tmp, f"--git-dir={bare}", "worktree", "add", "-q", "-b", "feat",
        str(worktree), "main")
    (worktree / ".game-of-cards" / "deck").mkdir(parents=True)
    (worktree / ".game-of-cards" / "config.yaml").write_text(
        "workflow:\n  worktree_deck: shared\n"
    )
    return bare, worktree


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name).resolve()
        bare, worktree = build(tmp)
        print(f"bare repository: {bare}")
        print(f"linked worktree: {worktree}")
        print(f"  git rev-parse --git-dir --git-common-dir:")
        for line in git(worktree, "rev-parse", "--git-dir", "--git-common-dir").splitlines():
            print(f"    {line}")
        own_deck = worktree / ".game-of-cards" / "deck"

        opt_ins = {
            "config opt-in only": {},
            "GOC_WORKTREE_DECK=shared": {"GOC_WORKTREE_DECK": "shared"},
        }
        for case, extra in opt_ins.items():
            card = "probe-" + ("config" if not extra else "env")
            print(f"\n== {case}")
            runs = {
                "goc new": goc(worktree, "new", card, "--summary", "Probe card.",
                               "--gate", "none", "--no-commit", **extra),
                "goc --status all": goc(worktree, "--status", "all", **extra),
            }
            for label, r in runs.items():
                print(f"$ {label}  (exit {r.returncode})")
                for stream, text in (("stdout", r.stdout), ("stderr", r.stderr)):
                    for line in text.strip().splitlines():
                        print(f"  {stream}: {line}")
                if r.returncode != 0:
                    failures.append(f"{case}: `{label}` exited {r.returncode}")
                if MISSING_DECK_PHRASE in r.stderr:
                    failures.append(
                        f"{case}: `{label}` reports a missing deck although "
                        f"{own_deck} exists"
                    )
                if str(bare) not in r.stderr or NO_PRIMARY not in r.stderr:
                    failures.append(
                        f"{case}: `{label}` never names {bare} or says the layout "
                        f"has {NO_PRIMARY}"
                    )
            if not (own_deck / card).is_dir():
                failures.append(f"{case}: `goc new` did not file {card} in {own_deck}")
            elif card not in runs["goc --status all"].stdout:
                failures.append(f"{case}: `goc --status all` does not list {card}")

    print()
    if failures:
        print("DEFECT FIRES:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("OK: shared mode says the bare clone has no primary working tree, and "
          "goc reads and writes the worktree's own deck.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
