"""Reproduce: goc attest crashes on a skipped check whose description is null.

`_cmd_attest`'s skip branch builds a summary via
`check.get('description', '')[:60]` (goc/engine.py). The `''` default
only guards an *absent* key; a present-but-None value (config
`description: null`) makes `.get` return None and `None[:60]` raises
`TypeError`, aborting the whole attest run.

This script drives the real `goc` CLI end-to-end in a throwaway repo:
it installs goc, writes a config whose skipped check has a null
description plus one sibling check that still runs (so the all-skipped
guard does not short-circuit first), and runs `goc attest`. It exits
non-zero while the bug is present (the run crashes / errors) and zero
once the null-coalescing fix lands.
"""

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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))


def _run_goc(cwd, *args):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)

        install = _run_goc(cwd, "install")
        if install.returncode != 0:
            print("setup FAIL: goc install errored\n", install.stderr)
            return 1

        # Two checks: the skipped one carries an explicit null description;
        # the other runs so the all-skipped guard does not fire first.
        config = cwd / ".game-of-cards" / "config.yaml"
        config.write_text(
            "layer_2_project_dod: []\n"
            "layer_3_goc_dod:\n"
            "  - name: dod-100-percent\n"
            "    kind: derived\n"
            "  - name: log-md-closure-entry\n"
            "    kind: derived\n"
            "    description: null\n"
        )

        _run_goc(cwd, "new", "smoke-card", "--gate", "none", "--tag", "story", "--allow-jargon")
        readme = cwd / ".game-of-cards" / "deck" / "smoke-card" / "README.md"
        readme.write_text(
            readme.read_text().replace("- [ ] (replace with real criteria)", "- [x] closure ok")
        )

        attest = _run_goc(
            cwd,
            "attest",
            "smoke-card",
            "--skip",
            "log-md-closure-entry",
            "--non-interactive",
        )

        print("goc attest returncode:", attest.returncode)
        print("--- stdout ---")
        print(attest.stdout)
        if attest.stderr.strip():
            print("--- stderr ---")
            print(attest.stderr)

        if "TypeError" in attest.stderr or "not subscriptable" in attest.stderr:
            print("\nFAIL: attest crashed with TypeError on a null check description")
            return 1
        if attest.returncode != 0:
            print("\nFAIL: attest exited non-zero on a null check description")
            return 1
        if "log-md-closure-entry — SKIPPED" not in attest.stdout:
            print("\nFAIL: expected the skipped-check line to render")
            return 1

        print("\nPASS: null check description rendered as SKIPPED, no crash")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
