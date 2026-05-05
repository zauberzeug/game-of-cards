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


def _run(cwd: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"

        install = _run(cwd, env, "install", "--agents", "codex")
        if install.returncode != 0:
            print(install.stdout)
            print(install.stderr)
            return install.returncode
        (cwd / ".game-of-cards" / "deck" / ".goc-version").write_text("0.0.1\n")
        upgrade = _run(cwd, env, "upgrade", "--dry-run")

    first_lines = "\n".join(upgrade.stdout.splitlines()[:8])
    print(f"install_exit={install.returncode}")
    print("installed_codex=True")
    print("installed_claude=False")
    print(f"upgrade_exit={upgrade.returncode}")
    print(first_lines)

    planned_claude = "agents: claude" in upgrade.stdout
    planned_codex = "agents: codex" in upgrade.stdout
    if upgrade.returncode == 0 and planned_claude and not planned_codex:
        print("defect present: no-flag upgrade in a Codex-only repo plans Claude")
        return 1
    print("ok: no-flag upgrade preserves the installed harness surface")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
