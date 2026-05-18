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


def main() -> int:
    repo = _repo_root()
    plugin_root = repo / "openclaw-plugin"
    if not plugin_root.exists():
        raise RuntimeError(f"openclaw plugin root not found: {plugin_root}")

    tmpdir = Path(tempfile.mkdtemp(prefix="goc-openclaw-kickoff-"))
    env = os.environ.copy()
    env["PYTHONPATH"] = str(plugin_root)

    cmd = [sys.executable, "-m", "goc.cli", "install", "--dry-run"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=tmpdir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        output = proc.stdout + proc.stderr
        print(output.rstrip())

        must_contain = [
            "agents: claude",
            "claude append CLAUDE.md",
        ]
        missing = [needle for needle in must_contain if needle not in output]
        if proc.returncode != 0:
            print(f"\nFAIL: expected exit 0, got {proc.returncode}")
            return 1
        if missing:
            print(f"\nFAIL: missing expected markers: {missing}")
            return 1

        print(f"\nTMPDIR={tmpdir}")
        print("Observed wrong default: OpenClaw-bundled install plans Claude harness writes.")
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
