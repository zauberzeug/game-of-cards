"""Demonstrate that `scripts/sync_plugin_assets.py` deletes user-authored
files under `.claude/skills/` / `.claude/hooks/` and then crashes trying to
`git add` the now-nonexistent untracked path.

Runs in a throwaway clone — the working repo is never modified.
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


def main() -> int:
    root = _repo_root()
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "clone"
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", f"file://{root}", str(clone)],
            check=True,
        )
        user_skill = clone / ".claude" / "skills" / "my-deploy-helper" / "SKILL.md"
        user_skill.parent.mkdir(parents=True)
        user_skill.write_text(
            "---\nname: my-deploy-helper\ndescription: user-authored, not GoC's\n---\n\nDeploy notes.\n"
        )
        user_hook = clone / ".claude" / "hooks" / "my_custom_hook.py"
        user_hook.write_text("# user-authored hook, not from goc/templates/hooks/\n")

        proc = subprocess.run(
            [sys.executable, "scripts/sync_plugin_assets.py"],
            cwd=clone,
            capture_output=True,
            text=True,
        )

        print(f"sync script exit code: {proc.returncode} (expected 0)")
        if proc.returncode != 0:
            failures += 1
            tail = (proc.stderr or proc.stdout).strip().splitlines()[-3:]
            for line in tail:
                print(f"  {line}")

        for label, path in (("user skill", user_skill), ("user hook", user_hook)):
            if path.exists():
                print(f"OK   {label} preserved: {path.relative_to(clone)}")
            else:
                failures += 1
                print(
                    f"FAIL {label} DELETED by sync: {path.relative_to(clone)} "
                    "(contract: user-authored files are not GoC-owned and must never be deleted)"
                )

    if failures:
        print(f"\n{failures} defect signal(s) — sync prunes user-authored files.")
        return 1
    print("\nDefect no longer fires: user-authored files survive the sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
