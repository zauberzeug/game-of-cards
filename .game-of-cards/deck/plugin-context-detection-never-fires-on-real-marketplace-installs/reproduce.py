"""Prove _is_plugin_context() never fires on a real marketplace install layout.

Stages the bundled plugin engine (claude-plugin/goc — which deliberately
omits templates/skills/) under two payload layouts and runs
`goc install --local-skills --dry-run` against each:

  1. Real marketplace layout: <cache>/<mkt>/game-of-cards/0.0.24/goc
     — the layout _claude_plugin_present() documents as "verified against
     live Claude Code installs". Expected designed behavior: the
     _LOCAL_SKILLS_PLUGIN_REFUSAL (exit 2). Actual: unhandled
     FileNotFoundError traceback (exit 1) because _is_plugin_context()
     checks `_PACKAGE_DIR.parent.name in {"claude-plugin", ...}` and the
     parent is named "0.0.24".
  2. Source-repo layout: .../claude-plugin/goc — the only layout the
     detection matches. The refusal fires (exit 2).

Defect proven when layout 1 exits with a traceback instead of the refusal
while layout 2 exits 2 with the refusal text.
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


REPO = _repo_root()


def run_install(payload_parent_name: str) -> subprocess.CompletedProcess:
    tmp = Path(tempfile.mkdtemp(prefix="goc-plugin-ctx-"))
    consumer = tmp / "consumer"
    consumer.mkdir()
    payload_root = tmp / "cache" / "mkt" / "game-of-cards" / payload_parent_name
    payload_root.mkdir(parents=True)
    shutil.copytree(REPO / "claude-plugin" / "goc", payload_root / "goc")
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", "install", "--local-skills", "--dry-run"],
        cwd=consumer,
        env={"PYTHONPATH": str(payload_root), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )


def main() -> int:
    real = run_install("0.0.24")  # marketplace versioned layout
    src = run_install("claude-plugin")  # source-repo layout

    print(f"[marketplace layout 0.0.24/goc]   exit={real.returncode}")
    tail = (real.stderr or real.stdout).strip().splitlines()[-1:]
    print(f"  last stderr line: {tail[0] if tail else '<empty>'}")
    print(f"[source layout claude-plugin/goc] exit={src.returncode}")
    head = (src.stderr or src.stdout).strip().splitlines()[:1]
    print(f"  first stderr line: {head[0] if head else '<empty>'}")

    refusal_fired_real = "not supported when running under the plugin" in (
        real.stderr + real.stdout
    )
    refusal_fired_src = "not supported when running under the plugin" in (
        src.stderr + src.stdout
    )
    crashed_real = "FileNotFoundError" in real.stderr or "Traceback" in real.stderr

    if not refusal_fired_real and crashed_real and refusal_fired_src:
        print(
            "\nDEFECT CONFIRMED: refusal is dead on the real marketplace layout"
            " (raw FileNotFoundError traceback instead); it only fires when the"
            " payload dir is literally named 'claude-plugin'."
        )
        return 0
    if refusal_fired_real:
        print("\nDefect no longer fires: refusal triggered on the marketplace layout.")
        return 1
    print("\nUnexpected output shape — inspect manually.")
    print("--- real layout stderr ---\n" + real.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
