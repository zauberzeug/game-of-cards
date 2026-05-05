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
        new = _run(cwd, env, "new", "smoke-card", "--gate", "none", "--tag", "story")
        readme = cwd / ".game-of-cards" / "deck" / "smoke-card" / "README.md"
        readme.write_text(readme.read_text().replace("- [ ] (replace with real criteria)", "- [x] closure ok"))
        log = cwd / ".game-of-cards" / "deck" / "smoke-card" / "log.md"
        log.write_text("## 2026-05-04 — Closure\n\n- ok\n")
        attest = _run(cwd, env, "attest", "smoke-card", "--non-interactive")
        config_text = (cwd / ".game-of-cards" / "config.yaml").read_text()
        log_text = log.read_text()

    print(f"install_exit={install.returncode}")
    print(f"new_exit={new.returncode}")
    print(f"attest_exit={attest.returncode}")
    print(f"config_has_dod_100={'dod-100-percent' in config_text}")
    print(f"log_has_layer3={'Layer-3 (GoC DoD)' in log_text}")
    print(f"log_has_dod_100={'dod-100-percent' in log_text}")
    print(f"log_has_log_check={'log-md-closure-entry' in log_text}")
    print("attest_stdout_last_line=" + (attest.stdout.strip().splitlines()[-1] if attest.stdout.strip() else ""))

    if install.returncode != 0 or new.returncode != 0:
        return 1
    missing_defaults = "dod-100-percent" not in config_text
    empty_attestation = "Layer-3 (GoC DoD)" not in log_text
    if attest.returncode == 0 and missing_defaults and empty_attestation:
        print("defect present: fresh install attestation passes with no layer-3 checks")
        return 1
    print("ok: fresh install records default GoC layer-3 closure checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
