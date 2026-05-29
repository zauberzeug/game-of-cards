"""Demonstrate that `goc move` leaves cross-reference rewrites uncommitted.

Sets up a throwaway repo with two cards `foo` and `bar` wired so that
`foo.advanced_by: [bar]` (so `foo`'s README will be rewritten by the
cross-reference pass), then runs `goc move bar bar-renamed` and checks:

1. The rename landed on disk.
2. HEAD did NOT advance (no auto-commit).
3. `git status --short` reports both the staged-rename + unstaged
   modifications on the renamed card and the unstaged cross-reference
   rewrite on `foo`.

For contrast, the same fixture is also exercised with `goc advance`,
which IS expected to auto-commit. The asymmetry is the defect.
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


REPO_ROOT = _repo_root()


def _goc(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", "--project", str(REPO_ROOT), "goc", *args],
        cwd=cwd, capture_output=True, text=True, check=False,
        env={**os.environ, "GIT_AUTHOR_NAME": "Audit", "GIT_AUTHOR_EMAIL": "audit@test",
             "GIT_COMMITTER_NAME": "Audit", "GIT_COMMITTER_EMAIL": "audit@test"},
    )


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="goc-move-uncommitted-audit-"))
    try:
        _git("init", "-q", cwd=workdir)
        _git("config", "user.email", "audit@test", cwd=workdir)
        _git("config", "user.name", "Audit", cwd=workdir)

        r = _goc("install", "--claude", cwd=workdir)
        if r.returncode != 0:
            print("FAIL: goc install failed:", r.stderr, file=sys.stderr)
            return 1
        for slug in ("foo", "bar"):
            r = _goc("new", slug, "--contribution", "medium", "--tag", "bug", cwd=workdir)
            if r.returncode != 0:
                print(f"FAIL: goc new {slug}:", r.stderr, file=sys.stderr)
                return 1
        # Wire bar → foo so foo carries a cross-reference to bar.
        r = _goc("advance", "foo", "--by", "bar", cwd=workdir)
        if r.returncode != 0:
            print("FAIL: goc advance:", r.stderr, file=sys.stderr)
            return 1
        _git("add", "-A", cwd=workdir)
        _git("commit", "-q", "-m", "init", cwd=workdir)

        head_before = _git("rev-parse", "HEAD", cwd=workdir).stdout.strip()

        r = _goc("move", "bar", "bar-renamed", cwd=workdir)
        print("--- goc move bar bar-renamed ---")
        print(r.stdout, end="")
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
            return 1

        deck_dir = workdir / ".game-of-cards" / "deck"
        rename_landed = (deck_dir / "bar-renamed" / "README.md").exists() and not (deck_dir / "bar" / "README.md").exists()
        if not rename_landed:
            print("FAIL: rename did not land on disk", file=sys.stderr)
            return 1
        print("OK: rename landed on disk (bar/ → bar-renamed/).")

        # Cross-reference in foo should be rewritten in the working tree.
        foo_readme = (deck_dir / "foo" / "README.md").read_text()
        xref_rewritten = "bar-renamed" in foo_readme
        if not xref_rewritten:
            print("UNEXPECTED: cross-reference in foo NOT rewritten; the rewrite phase did nothing.", file=sys.stderr)
            return 1
        print("OK: cross-reference in foo rewritten (foo/README.md now mentions bar-renamed).")

        head_after = _git("rev-parse", "HEAD", cwd=workdir).stdout.strip()
        status = _git("status", "--short", cwd=workdir).stdout.strip()

        print(f"\nHEAD before move: {head_before[:8]}")
        print(f"HEAD after  move: {head_after[:8]}")
        print(f"git status --short after move:\n{status or '(clean)'}")

        if head_after != head_before:
            print("UNEXPECTED: move advanced HEAD; bug appears fixed.")
            return 1
        if not status:
            print("UNEXPECTED: working tree clean; move seems to have committed silently.")
            return 1
        print("\nDEFECT CONFIRMED: move wrote rewrites + log entry to disk but did NOT commit.")

        # Contrast with goc advance, which IS expected to auto-commit.
        r = _goc("new", "baz", "--contribution", "medium", "--tag", "bug", cwd=workdir)
        if r.returncode != 0:
            print("setup-FAIL: goc new baz:", r.stderr, file=sys.stderr)
            return 1
        _git("add", "-A", cwd=workdir)
        _git("commit", "-q", "-m", "add baz", cwd=workdir)

        head_before_adv = _git("rev-parse", "HEAD", cwd=workdir).stdout.strip()
        r = _goc("advance", "foo", "--by", "baz", cwd=workdir)
        print("\n--- goc advance foo --by baz (control) ---")
        print(r.stdout, end="")
        head_after_adv = _git("rev-parse", "HEAD", cwd=workdir).stdout.strip()
        status_adv = _git("status", "--short", cwd=workdir).stdout.strip()
        print(f"HEAD before advance: {head_before_adv[:8]}")
        print(f"HEAD after  advance: {head_after_adv[:8]}")
        print(f"git status --short after advance: {status_adv or '(clean)'}")
        if head_after_adv == head_before_adv:
            print("FAIL: goc advance did not auto-commit (control failed; defect comparison invalid).", file=sys.stderr)
            return 1
        print("OK: goc advance auto-commits (control passes).")

        print("\nASYMMETRY DEMONSTRATED: advance commits; move does not.")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
