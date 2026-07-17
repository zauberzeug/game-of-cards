"""Prove the Codex skill resolver picks the lexicographically-last plugin
cache version instead of the newest one.

Builds a fake ~/.codex/plugins/cache tree with version dirs 0.0.9 (old
mtime) and 0.0.27 (new mtime), then runs the exact resolver pipeline
embedded in CODEX_GOC_COMMAND_RESOLVER (goc/install.py).

Exits 0 when the resolver picks the mtime-newest bootstrap (fixed);
exits 1 while it picks the stale 0.0.9 (defect present).
"""

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


sys.path.insert(0, str(_repo_root()))

from goc.install import CODEX_GOC_COMMAND_RESOLVER  # noqa: E402


def main() -> int:
    match = re.search(r"GOC_BOOTSTRAP=\$\((.+?)\)\n", CODEX_GOC_COMMAND_RESOLVER)
    if not match:
        print("could not locate the resolver pipeline in CODEX_GOC_COMMAND_RESOLVER")
        return 1
    pipeline = match.group(1)

    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp) / ".codex" / "plugins" / "cache" / "marketplace"
        old = cache / "game-of-cards" / "0.0.9" / "skills" / "_goc-bootstrap.sh"
        new = cache / "game-of-cards" / "0.0.27" / "skills" / "_goc-bootstrap.sh"
        for script in (old, new):
            script.parent.mkdir(parents=True)
            script.write_text("#!/bin/sh\n")
            script.chmod(0o755)
        # 0.0.9 installed first (older), 0.0.27 is the surviving upgrade.
        os.utime(old, (1_000_000_000, 1_000_000_000))
        os.utime(new, (2_000_000_000, 2_000_000_000))

        picked = subprocess.run(
            pipeline,
            shell=True,
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": tmp},
        ).stdout.strip()

    print(f"resolver snippet from goc/install.py picks: {picked}")
    print(f"mtime-newest (expected): {new}")
    if picked == str(new):
        print("OK: resolver selects the newest installed version")
        return 0
    print("DEFECT CONFIRMED: lexicographic sort selects the stale 0.0.9 over 0.0.27")
    return 1


if __name__ == "__main__":
    sys.exit(main())
