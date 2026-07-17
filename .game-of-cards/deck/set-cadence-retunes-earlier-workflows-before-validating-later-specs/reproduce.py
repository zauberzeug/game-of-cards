"""Prove scripts/set_cadence.py mutates earlier workflows before validating
later specs.

Copies the script and the real workflow files into a scratch tree, then runs
`--pull 2h --audit 5h` (5 does not divide 24, so the audit spec is invalid).

Exits 0 when the command is all-or-nothing (failure exit AND no file
mutated); exits 1 while the defect is present (failure exit but
pull-card.yml already rewritten).
"""

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


def main() -> int:
    root = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        (scratch / "pyproject.toml").write_text("")  # repo-root marker
        (scratch / "scripts").mkdir()
        shutil.copy2(root / "scripts" / "set_cadence.py", scratch / "scripts")
        wf = scratch / ".github" / "workflows"
        wf.mkdir(parents=True)
        for name in ("pull-card.yml", "audit-deck.yml", "refine-deck.yml"):
            shutil.copy2(root / ".github" / "workflows" / name, wf / name)

        before = (wf / "pull-card.yml").read_text()
        proc = subprocess.run(
            [sys.executable, str(scratch / "scripts" / "set_cadence.py"),
             "--pull", "2h", "--audit", "5h"],
            capture_output=True,
            text=True,
        )
        after = (wf / "pull-card.yml").read_text()

    mutated = before != after
    print(f"exit code: {proc.returncode} (stderr: {proc.stderr.strip()})")
    print(f"pull-card.yml mutated despite failure exit: {mutated}")
    if proc.returncode == 0:
        print("UNEXPECTED: invalid '5h' spec was accepted — repro assumptions broken")
        return 1
    if mutated:
        print("DEFECT CONFIRMED: command failed but left an earlier workflow retuned")
        return 1
    print("OK: failure exit left all workflow files untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
