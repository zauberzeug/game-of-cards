#!/usr/bin/env python3
"""`goc upgrade` from a plugin-bundled engine, in a repo pinned `skills_source: vendored`.

Scaffolds a throwaway repo with the source engine's documented
`goc install --local-skills`, then runs `goc upgrade` through the plugin
wrapper. Expected after the fix: a polite refusal (exit 2) naming the
config pin. Observed today: an unhandled `FileNotFoundError`, exit 1.

Exits 0 once the plugin path no longer tracebacks.
"""

from __future__ import annotations

import os
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


def main() -> int:
    wrapper = ROOT / "claude-plugin" / "bin" / "goc"
    if not wrapper.exists():
        print(f"[SKIP] no plugin wrapper at {wrapper}")
        return 0

    work = Path(tempfile.mkdtemp(prefix="goc-vendored-"))
    try:
        repo = work / "consumer"
        repo.mkdir()
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e.x",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e.x"}
        subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True, env=env)
        (repo / "README.md").write_text("# demo\n")
        subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True, env=env)

        # The documented vendored install, run with the SOURCE engine.
        subprocess.run(
            [sys.executable, "-m", "goc.cli", "install", "--local-skills"],
            cwd=repo, env={**env, "PYTHONPATH": str(ROOT)},
            capture_output=True, check=True,
        )
        pin = [ln for ln in (repo / ".game-of-cards" / "config.yaml").read_text().splitlines()
               if ln.startswith("skills_source:")]
        print(f"config pin: {pin[0] if pin else '(absent)'}")

        failures = []
        for label, argv in (("upgrade", []), ("upgrade --dry-run", ["--dry-run"])):
            proc = subprocess.run(
                [str(wrapper), "upgrade", *argv], cwd=repo,
                capture_output=True, text=True,
            )
            err = proc.stderr
            tracebacked = "Traceback (most recent call last)" in err
            tail = err.strip().splitlines()[-1] if err.strip() else "(no stderr)"
            print(f"\n[{label}] exit={proc.returncode} traceback={tracebacked}")
            print(f"  {tail}")
            if tracebacked:
                failures.append(label)

        if failures:
            print(f"\n[FAIL] plugin-engine upgrade tracebacks in a vendored-pinned repo: "
                  f"{', '.join(failures)}")
            return 1
        print("\n[OK] plugin-engine upgrade refuses cleanly instead of tracebacking.")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
