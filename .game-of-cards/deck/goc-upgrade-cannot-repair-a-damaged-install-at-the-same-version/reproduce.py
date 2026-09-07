#!/usr/bin/env python3
"""Reproduce: `goc upgrade` at the same version repairs nothing.

`upgrade()`'s "already at goc X — nothing to do" guard (goc/install.py:1802)
returns before every re-sync step in the function body, and the only work it
lets through at the same version is a hand-registered allowlist of three
`pending_*` signals. Four repair steps are NOT on that allowlist, so a repo
whose install was damaged (a deleted vendored skill dir, a deleted
`.game-of-cards/` stub, a deleted `.pre-commit-config.yaml`, a destroyed
AGENTS.md marker block) can never be re-synced with the documented command.

`goc install` in that repo exits 1 and prints "Run `goc upgrade` to re-sync
templates", so goc's own printed remedy is the command that does nothing.

Passing `--agents claude` (an *unrelated* flag, documented only as "for
scripted installs") sets `agents_explicit`, defeats the guard, and repairs
all four — which is what proves the work was available and merely skipped.

Before the fix: bare `goc upgrade` leaves all four damaged (exit 1 here).
After the fix:  bare `goc upgrade` repairs them (exit 0 here).
"""

from __future__ import annotations

import os
import re
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))


def goc(cwd: Path, *args: str) -> tuple[int, str]:
    """Run the engine as a consumer would — fresh process, `cwd` as the repo."""
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(cwd), env=env, capture_output=True, text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def damage(repo: Path) -> None:
    """Four independent kinds of install damage, one per un-allowlisted repair."""
    shutil.rmtree(repo / ".claude" / "skills" / "deck")          # vendored harness
    (repo / ".game-of-cards" / "canonical-tags.md").unlink()      # project-state stub
    (repo / ".pre-commit-config.yaml").unlink()                   # pre-commit stanza
    agents = repo / "AGENTS.md"
    agents.write_text(
        re.sub(
            r"(<!-- BEGIN GOC [^>]*-->\n).*?(<!-- END GOC -->)",
            r"\1(block destroyed)\n\2",
            agents.read_text(),
            flags=re.S,
        )
    )


def survey(repo: Path) -> dict[str, bool]:
    """True == that surface is healthy."""
    return {
        "vendored skill dir .claude/skills/deck/": (repo / ".claude/skills/deck").is_dir(),
        "project-state stub .game-of-cards/canonical-tags.md": (
            repo / ".game-of-cards/canonical-tags.md"
        ).is_file(),
        "pre-commit stanza .pre-commit-config.yaml": (repo / ".pre-commit-config.yaml").is_file(),
        "AGENTS.md goc-owned marker block": "block destroyed"
        not in (repo / "AGENTS.md").read_text(),
    }


def show(label: str, state: dict[str, bool]) -> None:
    print(f"  {label}")
    for name, ok in state.items():
        print(f"    {'OK     ' if ok else 'BROKEN '} {name}")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "consumer"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)

        code, _ = goc(repo, "install", "--agents", "claude", "--local-skills")
        print(f"[setup] goc install --agents claude --local-skills -> exit {code}")

        damage(repo)
        print("\n[damage] deleted one vendored skill dir, one project-state stub and")
        print("         .pre-commit-config.yaml; blanked the AGENTS.md marker block")
        show("after damage:", survey(repo))

        code, out = goc(repo, "install", "--agents", "claude")
        print(f"\n[step 1] goc install       -> exit {code}")
        for line in out.splitlines():
            print(f"           {line}")

        code, out = goc(repo, "upgrade")
        print(f"\n[step 2] goc upgrade       -> exit {code}")
        for line in out.splitlines():
            print(f"           {line}")
        after_bare = survey(repo)
        show("after bare upgrade:", after_bare)

        code, _ = goc(repo, "upgrade", "--agents", "claude")
        after_flag = survey(repo)
        print(f"\n[step 3] goc upgrade --agents claude -> exit {code}")
        show("after upgrade --agents claude:", after_flag)

        skipped = sorted(k for k, ok in after_bare.items() if not ok)
        repaired = sorted(k for k, ok in after_flag.items() if ok)
        print(f"\nrepairs skipped by bare `goc upgrade`: {len(skipped)}/4")
        print(f"repairs performed once the guard is defeated: {len(repaired)}/4")

        if skipped:
            print(
                "\nDEFECT PRESENT: bare `goc upgrade` exits 0 with "
                f"'nothing to do' while {len(skipped)} repair(s) it is documented "
                "to perform stay undone; the same run with an unrelated "
                "`--agents` flag performs all of them."
            )
            return 1
        print("\nDEFECT ABSENT: bare `goc upgrade` re-synced every damaged surface.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
