from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


INVALID_QUOTED_NEW = re.compile(r'goc new "([^"]*\s+[^"]*)"')


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


def _find_invalid_examples(repo: Path) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for rel in (Path("README.md"), Path("goc.md")):
        for lineno, line in enumerate((repo / rel).read_text().splitlines(), start=1):
            if INVALID_QUOTED_NEW.search(line):
                hits.append((str(rel), lineno, line.strip()))
    return hits


def main() -> int:
    repo = _repo_root()
    hits = _find_invalid_examples(repo)
    print(f"invalid_doc_examples={len(hits)}")
    for rel, lineno, line in hits:
        print(f"{rel}:{lineno}: {line}")

    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "new", "rename the button", "--gate", "none", "--tag", "story"],
            cwd=tmp,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    print(f"advertised_shape_exit={result.returncode}")
    print(f"advertised_shape_stderr={result.stderr.strip()}")
    if hits and result.returncode != 0:
        print("defect present: docs advertise a goc new title shape the CLI rejects")
        return 1
    print("ok: direct goc new examples use valid card slugs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
