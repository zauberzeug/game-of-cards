"""Reproduce the malformed-frontmatter inconsistency.

Scaffolds a fresh deck in a temp dir, writes a card whose README.md has
an opening `---` but NO closing `---`, runs `goc show`, `goc validate`,
and `goc done` against it, and prints each command's exit code + stderr.

Post-fix invariants asserted at the bottom:
  1. `goc show` succeeds (exit 0) AND emits a warning to stderr
     mentioning "frontmatter unterminated".
  2. `goc validate` exits non-zero AND its stderr names the card and
     says "frontmatter unterminated" (not "missing frontmatter").
  3. `goc done` exits non-zero AND its stderr says "frontmatter parse
     failed" or "frontmatter unterminated" (not "not found at <path>").

Pre-fix: assertion (1) fails (no warning), (2) fails ("missing
frontmatter" instead), (3) fails ("not found at <path>" instead).
"""
from __future__ import annotations

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
GOC = [sys.executable, "-m", "goc.cli"]


def _run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(Path.home())}
    env["PYTHONPATH"] = str(REPO)
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, env=env
    )
    return proc.returncode, proc.stdout, proc.stderr


MALFORMED_README = """---
title: my-card
status: open
stage: null
contribution: medium
created: "2026-05-17T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] something

## Body starts here without a closing ---
"""


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="goc-fm-repro-"))
    try:
        rc, _, err = _run(GOC + ["install", "--claude"], workdir)
        if rc != 0:
            print(f"install failed (rc={rc}): {err}", file=sys.stderr)
            return rc
        rc, _, err = _run(GOC + ["new", "--gate", "none", "my-card"], workdir)
        if rc != 0:
            print(f"new failed (rc={rc}): {err}", file=sys.stderr)
            return rc

        readme = workdir / ".game-of-cards" / "deck" / "my-card" / "README.md"
        readme.write_text(MALFORMED_README)

        print("=" * 60)
        print("goc show my-card")
        print("=" * 60)
        rc_show, out_show, err_show = _run(GOC + ["show", "my-card"], workdir)
        print(f"exit={rc_show}")
        print(f"stdout: {out_show!r}"[:200])
        print(f"stderr: {err_show!r}")

        print("=" * 60)
        print("goc validate")
        print("=" * 60)
        rc_val, out_val, err_val = _run(GOC + ["validate"], workdir)
        print(f"exit={rc_val}")
        print(f"stdout: {out_val!r}"[:200])
        print(f"stderr: {err_val!r}")

        print("=" * 60)
        print("goc done my-card")
        print("=" * 60)
        rc_done, out_done, err_done = _run(GOC + ["done", "my-card"], workdir)
        print(f"exit={rc_done}")
        print(f"stdout: {out_done!r}"[:200])
        print(f"stderr: {err_done!r}")

        print("=" * 60)
        print("Post-fix invariants")
        print("=" * 60)
        failures: list[str] = []

        if rc_show != 0:
            failures.append(f"show should succeed (exit 0); got {rc_show}")
        if "frontmatter unterminated" not in err_show.lower() and "unterminated" not in err_show.lower():
            failures.append(
                "show stderr should warn about unterminated frontmatter; "
                f"got: {err_show!r}"
            )

        if rc_val == 0:
            failures.append("validate should fail; exited 0")
        if "missing frontmatter" in err_val.lower() and "unterminated" not in err_val.lower():
            failures.append(
                "validate uses stale 'missing frontmatter' phrasing; "
                f"expected 'frontmatter unterminated' in stderr"
            )

        if rc_done == 0:
            failures.append("done should fail; exited 0")
        if "not found at" in err_done.lower() and "parse failed" not in err_done.lower():
            failures.append(
                "done uses stale 'not found at <path>' phrasing for parse "
                f"failure; expected 'frontmatter parse failed' or similar"
            )

        if failures:
            print("FAIL:")
            for f in failures:
                print(f"  - {f}")
            return 1
        print("OK: all post-fix invariants satisfied")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
