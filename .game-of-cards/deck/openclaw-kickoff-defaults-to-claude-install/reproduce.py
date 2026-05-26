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
    """Guard: a fresh repo driven through the OpenClaw-bundled engine must plan
    a no-harness scaffold — `.game-of-cards/` + AGENTS.md only, never `agents:
    claude` or a `CLAUDE.md` append.

    History: when this card was filed (2026-05-18), the bundled engine fell back
    to the documented Claude default on a blank repo, so this script reported the
    defect (`agents: claude`, `claude append CLAUDE.md`). After the fix
    (`_is_openclaw_plugin_context()` → no-harness default in `goc/install.py`),
    the script asserts the corrected contract and exits zero. It runs against the
    *bundled* `openclaw-plugin/goc/` mirror, so it also fails if the plugin asset
    sync ever drifts from source.
    """

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

        if proc.returncode != 0:
            print(f"\nFAIL: expected exit 0, got {proc.returncode}")
            return 1

        # The OpenClaw default must be no harness: the shared briefing lands in
        # AGENTS.md, and nothing pins the Claude harness.
        wrong = [needle for needle in ("agents: claude", "claude append CLAUDE.md") if needle in output]
        required = [needle for needle in ("agents: none", "shared append AGENTS.md") if needle not in output]
        if wrong:
            print(f"\nDEFECT PRESENT: OpenClaw-bundled install still plans Claude harness writes: {wrong}")
            return 1
        if required:
            print(f"\nFAIL: OpenClaw-safe scaffold missing expected markers: {required}")
            return 1

        print(f"\nTMPDIR={tmpdir}")
        print("ok: OpenClaw-bundled install plans a no-harness scaffold (AGENTS.md only, no CLAUDE.md).")
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
