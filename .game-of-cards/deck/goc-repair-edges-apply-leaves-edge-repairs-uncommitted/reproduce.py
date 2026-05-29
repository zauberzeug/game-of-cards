"""Demonstrate that `goc repair-edges --apply` leaves the working tree dirty.

Sets up a throwaway repo with two cards in a half-edge state
(`foo.advances: [bar]` but `bar.advanced_by: []`), runs
`goc repair-edges --apply`, and checks two things:

1. The repair landed on disk (`bar.advanced_by` now contains `foo`).
2. The repair was NOT auto-committed (HEAD unchanged; working tree dirty).

For contrast, the same fixture is also exercised with `goc advance --by`,
which IS expected to auto-commit. The asymmetry is the defect.
"""
from __future__ import annotations

import os
import re
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


def _introduce_half_edge(deck_dir: Path) -> None:
    foo_readme = deck_dir / "foo" / "README.md"
    text = foo_readme.read_text()
    text = re.sub(r"^advances: \[\]$", "advances:\n  - bar", text, flags=re.MULTILINE)
    foo_readme.write_text(text)


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="goc-repair-edges-audit-"))
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
        _git("add", "-A", cwd=workdir)
        _git("commit", "-q", "-m", "init", cwd=workdir)

        deck_dir = workdir / ".game-of-cards" / "deck"
        _introduce_half_edge(deck_dir)
        _git("add", "-A", cwd=workdir)
        _git("commit", "-q", "-m", "introduce half-edge", cwd=workdir)

        head_before = _git("rev-parse", "HEAD", cwd=workdir).stdout.strip()

        r = _goc("repair-edges", "--apply", cwd=workdir)
        print("--- goc repair-edges --apply ---")
        print(r.stdout, end="")
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
            return 1

        bar_readme = (deck_dir / "bar" / "README.md").read_text()
        repair_on_disk = "advanced_by:\n  - foo" in bar_readme
        if not repair_on_disk:
            print("FAIL: repair did not land on disk", file=sys.stderr)
            print(bar_readme, file=sys.stderr)
            return 1
        print("OK: repair landed on disk (bar/README.md now lists foo in advanced_by).")

        head_after = _git("rev-parse", "HEAD", cwd=workdir).stdout.strip()
        status = _git("status", "--short", cwd=workdir).stdout.strip()

        print(f"\nHEAD before repair: {head_before[:8]}")
        print(f"HEAD after  repair: {head_after[:8]}")
        print(f"git status --short after repair:\n{status or '(clean)'}")

        if head_after != head_before:
            print("UNEXPECTED: repair-edges advanced HEAD; bug appears fixed.")
            return 1
        if not status:
            print("UNEXPECTED: working tree clean; repair seems to have committed silently.")
            return 1
        print("\nDEFECT CONFIRMED: repair-edges wrote to disk but did NOT commit.")

        # Contrast with goc advance --by, which IS expected to auto-commit.
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

        print("\nASYMMETRY DEMONSTRATED: advance commits; repair-edges does not.")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
