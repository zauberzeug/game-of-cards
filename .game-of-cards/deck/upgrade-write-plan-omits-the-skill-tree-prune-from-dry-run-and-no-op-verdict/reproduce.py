#!/usr/bin/env python3
"""Reproduce: the upgrade write plan models writes but never the skill-tree prune.

`_sync_skill_tree(replace_skills=True)` (goc/install.py) `shutil.rmtree`s each
*eligible* (current-template) skill directory before recopying it, so a file
sitting inside a GoC-owned skill dir that the current templates no longer ship
is deleted by `goc upgrade`. That deletion is real work — but it is not a
`PlannedWrite`, and `_plan_upgrade_writes` enumerates writes only. Two
consequences follow from the one omission:

1. `goc upgrade --dry-run` never lists the deletion. It reports a write count
   and calls the run "N effecting", then the real run removes a file the
   preview never mentioned. `--dry-run`'s whole contract is a truthful preview.

2. `upgrade()` reads its "already at goc X — nothing to do" verdict off that
   same plan (`plan_has_effect`). With no prune in the plan, the verdict is
   `False`, so at the same version the stale file is never removed — while the
   identical damage IS repaired at any other version. The predecessor card
   `goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version` replaced a
   hand-maintained `pending_*` allowlist with this plan-derived verdict so that
   "a repair added to `upgrade()` is covered the moment it is planned"; a repair
   that deletes rather than writes is never planned, so it stayed uncovered.

Before the fix: same-version upgrade says "nothing to do" and the stale file
survives, while the older-sentinel dry-run omits the deletion it then performs
(exit 1 here).
After the fix:  the plan carries the prune, so the same-version run repairs it
and the dry-run lists it (exit 0 here).
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
sys.path.insert(0, str(ROOT))

# A GoC-owned skill dir, and a file inside it that the current templates do not
# ship — the shape a skill file removed upstream leaves behind.
SKILL_DIR = Path(".claude") / "skills" / "deck"
STALE = SKILL_DIR / "reference-v1.md"


def goc(cwd: Path, *args: str) -> tuple[int, str]:
    """Run the engine as a consumer would — fresh process, `cwd` as the repo."""
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(cwd), env=env, capture_output=True, text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def install(repo: Path) -> None:
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
    code, out = goc(repo, "install", "--agents", "claude", "--local-skills")
    if code != 0:
        raise SystemExit(f"setup failed (exit {code}):\n{out}")


def plant_stale(repo: Path) -> None:
    (repo / STALE).write_text("guidance the current templates no longer ship\n")


def sentinel(repo: Path) -> Path:
    return repo / ".game-of-cards" / "deck" / ".goc-version"


def main() -> int:
    from goc import __version__

    failures: list[str] = []
    print(f"engine version: {__version__}\n")

    with tempfile.TemporaryDirectory() as tmp:
        # ---- Part 1: same version -> "nothing to do", stale file survives ----
        repo = Path(tmp) / "same-version"
        install(repo)
        plant_stale(repo)
        print("[part 1] same-version upgrade")
        print(f"  planted {STALE} inside a GoC-owned skill dir")
        code, out = goc(repo, "upgrade")
        print(f"  goc upgrade -> exit {code}: {out.splitlines()[0] if out else ''}")
        survived = (repo / STALE).is_file()
        print(f"  stale file still present: {survived}")

        # ---- Part 2: older sentinel -> dry-run hides the deletion it performs ----
        repo2 = Path(tmp) / "older-sentinel"
        install(repo2)
        plant_stale(repo2)
        sentinel(repo2).write_text("0.0.1\n")
        print("\n[part 2] same damage, sentinel rewound to 0.0.1")
        code, plan = goc(repo2, "upgrade", "--dry-run")
        headline = next((ln for ln in plan.splitlines() if "writes planned" in ln), "")
        print(f"  goc upgrade --dry-run -> exit {code}")
        print(f"    {headline}")
        mentions = [
            ln for ln in plan.splitlines()
            if STALE.name in ln or any(w in ln.lower() for w in ("prune", "delete", "remove"))
        ]
        print(f"  plan lines naming the deletion: {len(mentions)}")
        for ln in mentions:
            print(f"    {ln.strip()}")
        code, _ = goc(repo2, "upgrade")
        deleted = not (repo2 / STALE).is_file()
        print(f"  real goc upgrade -> exit {code}; stale file deleted: {deleted}")

    if survived:
        failures.append(
            "same-version `goc upgrade` reported 'nothing to do' and left the "
            "stale skill file in place"
        )
    if deleted and not mentions:
        failures.append(
            "`goc upgrade --dry-run` listed no deletion, then the real run "
            "removed the file"
        )

    print()
    if failures:
        print(f"DEFECT PRESENT ({len(failures)} of 2 assertions failed):")
        for f in failures:
            print(f"  BUG: {f}")
        print(
            "\nOne cause: `_plan_upgrade_writes` enumerates `PlannedWrite`s only, "
            "so the `_sync_skill_tree` prune is invisible to both the dry-run "
            "plan and the `plan_has_effect` no-op verdict derived from it."
        )
        return 1
    print("DEFECT ABSENT: the plan carries the skill-tree prune on both paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
