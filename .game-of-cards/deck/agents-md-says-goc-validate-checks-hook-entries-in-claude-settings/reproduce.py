#!/usr/bin/env python3
"""Reproduce: AGENTS.md credits `goc validate` with a settings.json parity check it lacks.

AGENTS.md's `.claude/settings.json` ownership paragraph tells contributors to
change the goc-owned hook entries in `goc/install.py`, "not in
`.claude/settings.json`, and `goc validate` enforces the parity". This script
runs the card's falsification recipe in a scratch repo:

1. `goc install --agents claude --local-skills`, then `goc validate` (exit 0).
2. Hand-edit `.claude/settings.json`: drop the `Stop` registration and point
   the `SessionStart` command at a script that does not exist.
3. `goc validate` again.

If step 3 still exits 0 while AGENTS.md credits `goc validate` with that
parity, the doc promises a safety net that is not there (exit 1 here).
For context it then runs a same-version `goc upgrade` on the edited file, the
merge that does put missing goc-owned entries back.

Exit 1 while the defect is present. Exit 0 once AGENTS.md stops crediting
`goc validate` with the check, or if `goc validate` turns out to catch the
edit, which disproves the hypothesis.
"""

from __future__ import annotations

import json
import os
import re
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

# A positive claim that `goc validate` holds the entries to GOC_CLAUDE_HOOKS.
VALIDATE_CREDITED = re.compile(
    r"`goc validate` (?:enforces|checks|catches|reports|verifies|guards)"
)
REPOINTED = "deck_session_start_RENAMED.py"


def goc(cwd: Path, *args: str) -> tuple[int, str]:
    """Run the engine as a consumer would: fresh process, `cwd` as the repo."""
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(cwd), env=env, capture_output=True, text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def settings_paragraph() -> str:
    """AGENTS.md's `.claude/settings.json` ownership paragraph, unwrapped."""
    for para in re.split(r"\n\s*\n", (ROOT / "AGENTS.md").read_text()):
        flat = re.sub(r"\s+", " ", para)
        if "`.claude/settings.json` is the" in flat:
            return flat
    raise SystemExit("AGENTS.md has no `.claude/settings.json` ownership paragraph")


def commands(settings: dict) -> dict[str, list[str]]:
    return {
        event: [h.get("command") for group in groups for h in group.get("hooks", [])]
        for event, groups in settings.get("hooks", {}).items()
    }


def main() -> int:
    paragraph = settings_paragraph()
    credited = VALIDATE_CREDITED.search(paragraph)
    print("AGENTS.md `.claude/settings.json` paragraph:")
    print(f"  credits `goc validate` with the parity: {bool(credited)}"
          + (f"  ({credited.group(0)!r})" if credited else ""))

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "consumer"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
        code, out = goc(repo, "install", "--agents", "claude", "--local-skills")
        if code != 0:
            raise SystemExit(f"setup failed (exit {code}):\n{out}")
        code, _ = goc(repo, "validate")
        print(f"\n[1] fresh --local-skills install: goc validate -> exit {code}")
        if code != 0:
            raise SystemExit("setup failed: validate is red before the edit")

        path = repo / ".claude" / "settings.json"
        settings = json.loads(path.read_text())
        print("[2] hand-edit .claude/settings.json")
        print(f"    events before: {sorted(settings['hooks'])}")
        del settings["hooks"]["Stop"]
        for group in settings["hooks"]["SessionStart"]:
            for hook in group["hooks"]:
                hook["command"] = hook["command"].replace("deck_session_start.py", REPOINTED)
        path.write_text(json.dumps(settings, indent=2) + "\n")
        print(f"    events after:  {sorted(settings['hooks'])}")
        print(f"    SessionStart:  {commands(settings)['SessionStart']}")

        code, out = goc(repo, "validate")
        caught = code != 0
        print(f"[3] goc validate -> exit {code}")
        for line in out.splitlines():
            print(f"      {line}")

        code, _ = goc(repo, "upgrade")
        after = commands(json.loads(path.read_text()))
        present = {c for cmds in after.values() for c in cmds}
        missing = sorted(e for e, c in GOC_CLAUDE_HOOKS.items() if c not in present)
        repointed = [c for cmds in after.values() for c in cmds if REPOINTED in c]
        print(f"\n[context] same-version goc upgrade -> exit {code}")
        print(f"    GOC_CLAUDE_HOOKS entries still missing: {missing or 'none'}")
        print(f"    repointed entry still registered: {bool(repointed)}")

    print()
    if caught:
        print("HYPOTHESIS DISPROVED: goc validate rejects the hand edit, so the "
              "AGENTS.md claim holds.")
        return 0
    if credited:
        print("DEFECT PRESENT: goc validate exits 0 on a dropped and a repointed "
              "registration, yet AGENTS.md says it enforces the parity.")
        return 1
    print("FIXED: goc validate still passes the hand edit, and AGENTS.md no "
          "longer claims it enforces the parity.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
