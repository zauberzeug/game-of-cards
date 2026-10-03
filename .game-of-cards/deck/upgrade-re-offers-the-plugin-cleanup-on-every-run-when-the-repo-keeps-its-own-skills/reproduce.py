#!/usr/bin/env python3
"""goc upgrade's plugin-mode cleanup offer, checked against what the cleanup removes.

Builds two scratch `goc install --local-skills` repos with the source engine
and switches each the documented way (`skills_source: plugin`, then
`goc upgrade` answering `y`):

A. The repo keeps a skill of its own in `.claude/skills/`. After the switch
   the cleanup has nothing left to remove, so the next routine `goc upgrade`
   must neither offer it nor announce it under `--dry-run`, and must reach
   the "already at goc X — nothing to do." verdict.
B. A partial hand cleanup removed `.claude/skills/` but left the GoC hook
   scripts and settings registrations. The switch must offer the cleanup and
   end with none of them.

Exits 0 when both hold, 1 while the offer keys on whether `.claude/skills/`
exists instead of on GoC content the cleanup would remove.
"""

from __future__ import annotations

import json
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

from goc.install import GOC_CLAUDE_HOOKS  # noqa: E402

# The y/N question is not echoed off a TTY; the intro line before it is.
OFFER = "from a prior vendored install"
GOC_COMMANDS = set(GOC_CLAUDE_HOOKS.values())
GOC_HOOK_SCRIPTS = sorted(
    m.group(1) for cmd in GOC_COMMANDS if (m := re.search(r"(\.claude/hooks/[\w.-]+\.py)", cmd))
)


def _goc(repo: Path, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=repo,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        input=stdin,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(f"goc {' '.join(args)} exited {result.returncode}:\n{result.stdout}\n{result.stderr}")
    return result


def _vendored_repo(work: Path, name: str) -> Path:
    repo = work / name
    repo.mkdir()
    _goc(repo, "install", "--local-skills", "--agents", "claude")
    return repo


def _pin_plugin(repo: Path) -> None:
    config = repo / ".game-of-cards" / "config.yaml"
    config.write_text(re.sub(r"^skills_source:.*$", "skills_source: plugin", config.read_text(), flags=re.M))


def _goc_scripts(repo: Path) -> list[str]:
    return [rel for rel in GOC_HOOK_SCRIPTS if (repo / rel).is_file()]


def _goc_entries(repo: Path) -> list[str]:
    path = repo / ".claude" / "settings.json"
    settings = json.loads(path.read_text()) if path.is_file() else {}
    return [
        h.get("command")
        for groups in settings.get("hooks", {}).values()
        for group in groups
        for h in group.get("hooks", [])
        if h.get("command") in GOC_COMMANDS
    ]


def main() -> int:
    failures: list[str] = []
    work = Path(tempfile.mkdtemp(prefix="goc-cleanup-offer-"))
    try:
        # A: the repo keeps a skill of its own.
        repo = _vendored_repo(work, "keeps-own-skill")
        (repo / ".claude" / "skills" / "my-own-skill").mkdir()
        (repo / ".claude" / "skills" / "my-own-skill" / "SKILL.md").write_text("# mine\n")
        _pin_plugin(repo)
        switch = _goc(repo, "upgrade", stdin="y\n")
        kept = sorted(p.name for p in (repo / ".claude" / "skills").iterdir())
        print(f"[A] switch upgrade: offered={OFFER in switch.stdout}; .claude/skills/ now holds {kept}")
        routine = _goc(repo, "upgrade")
        reoffered = OFFER in routine.stdout
        verdict = "nothing to do" in routine.stdout
        print(f"[A] next routine upgrade: offered again={reoffered}; no-op verdict={verdict}")
        dry = _goc(repo, "upgrade", "--dry-run")
        announced = "cleanup" in dry.stdout
        print(f"[A] --dry-run announces cleanup={announced}")
        if OFFER not in switch.stdout or kept != ["my-own-skill"]:
            failures.append("A: the switch itself no longer offers the cleanup, or lost the repo's own skill")
        if reoffered or not verdict or announced:
            failures.append("A: the cleanup is re-offered after it ran, for a layout holding only the repo's own skill")

        # B: GoC hooks and settings entries left behind without a skills dir.
        repo = _vendored_repo(work, "hooks-without-skills-dir")
        shutil.rmtree(repo / ".claude" / "skills")
        _pin_plugin(repo)
        print(f"[B] before upgrade: {len(_goc_scripts(repo))} GoC hook scripts, {len(_goc_entries(repo))} GoC settings entries")
        switch = _goc(repo, "upgrade", stdin="y\n")
        scripts, entries = _goc_scripts(repo), _goc_entries(repo)
        print(f"[B] upgrade offered the cleanup={OFFER in switch.stdout}; after: {len(scripts)} scripts, {len(entries)} entries")
        if OFFER not in switch.stdout or scripts or entries:
            failures.append("B: GoC hook scripts / settings entries survive because no .claude/skills/ dir triggers the offer")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if failures:
        print("\nFAIL:")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print("\nOK: the cleanup is offered exactly when it has GoC content to remove.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
