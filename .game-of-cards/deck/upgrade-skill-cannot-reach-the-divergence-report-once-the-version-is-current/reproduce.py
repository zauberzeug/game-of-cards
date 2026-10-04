#!/usr/bin/env python3
"""Reproduce: `goc upgrade` at the current version prints no divergence report.

`Skill(upgrade)` step 1 runs `goc upgrade` and parses the JSON report printed
after the sentinel `GoC project-state divergence report (JSON):`; every later
step of the skill reads that report. The only call that prints it is
`_sync_game_of_cards_config(..., emit_report=True)`, which sits *after*
`upgrade()`'s "already at goc X — nothing to do." early return. A diverged
evolving file (`.game-of-cards/README.md`, `config.yaml`) is `preserved`, which
is in `_NO_OP_ACTIONS`, so the very divergence the skill exists to reconcile
never makes the plan effecting and never gets the run past that return.

So once anyone has run `goc upgrade` at a version (a human in a terminal, as
the install output suggests, or an earlier skill session), the skill's own
`goc upgrade` gets no report, and its promise that upstream changes wait "until
the next time someone runs this skill" cannot be kept.

Steps, as the card's falsification recipe:
1. scratch install, sentinel rewound to 0.0.1, `goc upgrade` to the current
   version (the run a human makes in a terminal);
2. diverge `.game-of-cards/README.md` from its template;
3. `goc upgrade` again (the skill's step 1) and look for the report.

Before the fix: the second run prints only the no-op line (exit 1 here).
After the fix:  the second run still prints the report, with README.md as
`preserved` / `evolving`, and writes nothing (exit 0 here).
"""

from __future__ import annotations

import json
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

MARKER = "GoC project-state divergence report (JSON):"


def goc(cwd: Path, *args: str) -> tuple[int, str]:
    """Run the engine as a consumer would — fresh process, `cwd` as the repo.

    Returns stdout only: the skill parses stdout, so a report on stderr would
    not count.
    """
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(cwd), env=env, capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout


def report(stdout: str) -> dict | None:
    lines = stdout.splitlines()
    for idx, line in enumerate(lines):
        if line == MARKER and idx + 1 < len(lines):
            return json.loads(lines[idx + 1])
    return None


def snapshot(repo: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(repo)): p.read_bytes()
        for p in sorted(repo.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(repo).parts
    }


def main() -> int:
    from goc import __version__

    print(f"engine version: {__version__}\n")
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "consumer"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
        code, out = goc(repo, "install", "--agents", "claude", "--local-skills")
        if code != 0:
            raise SystemExit(f"setup failed (exit {code}):\n{out}")

        # 1. the upgrade a human runs in a terminal after a release bump
        (repo / ".game-of-cards" / "deck" / ".goc-version").write_text("0.0.1\n")
        code, first = goc(repo, "upgrade")
        print(f"[1] goc upgrade 0.0.1 -> {__version__}: exit {code}")
        print(f"    printed report: {report(first) is not None}")

        # 2. the consumer's own README customization
        readme = repo / ".game-of-cards" / "README.md"
        readme.write_text(readme.read_text() + "\nLocal note: our team-specific hook docs.\n")
        print("[2] appended a line to .game-of-cards/README.md")

        # 3. the skill's step 1, now at the current version
        before = snapshot(repo)
        code, second = goc(repo, "upgrade")
        wrote = snapshot(repo) != before
        payload = report(second)
        print(f"[3] goc upgrade at {__version__}: exit {code}")
        print(f"    first line: {second.splitlines()[0] if second else ''}")
        print(f"    printed report: {payload is not None}")
        readme_entry = None
        if payload is not None:
            readme_entry = next(
                (f for f in payload["files"] if f["path"] == "README.md"), None
            )
            print(f"    README.md entry: {readme_entry}")
        print(f"    wrote to disk: {wrote}")

        code, preview = goc(repo, "upgrade", "--dry-run")
        print(f"    (--dry-run at {__version__} printed report: {report(preview) is not None})")

    failures: list[str] = []
    if payload is None:
        failures.append(
            "the same-version `goc upgrade` printed no divergence report, so "
            "Skill(upgrade) has nothing to reconcile from"
        )
    elif readme_entry != {"path": "README.md", "status": "preserved", "ownership": "evolving"}:
        failures.append(f"README.md is not reported as a preserved evolving file: {readme_entry}")
    if wrote:
        failures.append("the same-version `goc upgrade` wrote to disk")

    print()
    if failures:
        print(f"DEFECT PRESENT ({len(failures)} failure(s)):")
        for failure in failures:
            print(f"  BUG: {failure}")
        print(
            "\nCause: the report is printed only by `_sync_game_of_cards_config`, "
            "below upgrade()'s 'nothing to do' return, and a diverged evolving "
            "file is a no-op (`preserved`) to the write plan that gates it."
        )
        return 1
    print("DEFECT ABSENT: the same-version upgrade still hands the skill its report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
