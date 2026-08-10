#!/usr/bin/env python3
"""Reproduce: `_git_auto_commit` lets `git` write straight to goc's stdout.

`git add` and `git commit` are the only two `subprocess.run` calls in
`goc/engine.py` that omit `capture_output=True`, so git's porcelain summary
lands on goc's own stdout. Two observable consequences, both checked here:

  A. NOISE — the summary (`[main abc1234] deck: …` / ` 1 file changed, …`)
     appears in the verb's output, duplicating the `  committed` line goc
     prints as its own deliberate one-line report.
  B. ORDER — when stdout is a pipe (agent tool capture, CI logs, `| head`),
     Python block-buffers its own prints while the git child writes to the
     inherited fd immediately, so git's lines arrive BEFORE the verb line
     that announced the mutation. On a tty the order is right and only (A)
     fires, which is why this is invisible in interactive use.

Exits 0 when the defect is FIXED (no git porcelain on stdout, verb report in
code order), 1 while it still fires.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
"""

from __future__ import annotations

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


ROOT = _repo_root()

# `git commit`'s porcelain summary: the `[branch sha] subject` header and the
# diffstat line beneath it. Neither is anything goc chose to print.
_PORCELAIN = (
    re.compile(r"^\[[^\]]+ [0-9a-f]{7,}\] "),
    re.compile(r"^ \d+ files? changed"),
    re.compile(r"^ (create|delete) mode \d+ "),
)

# Every verb below auto-commits through `_git_auto_commit`. `status … active`
# leads because it is the first mutation of every pull-card session.
CASES = [
    ("status-active", ["status", "alpha", "active"], "alpha: open → active"),
    ("wait", ["wait", "alpha", "--reason", "external"], "alpha: waiting_on='external'"),
    ("advance", ["advance", "alpha", "--by", "beta"], "advance: alpha.advanced_by += beta"),
]


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return env


def _goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env=_env(),
        capture_output=True,
        text=True,
    )


def _seed(repo: Path) -> None:
    """A committed two-card deck with auto_commit on — the shipped default."""
    subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "probe@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "probe"], cwd=repo, check=True)
    (repo / ".game-of-cards" / "deck").mkdir(parents=True)
    (repo / ".game-of-cards" / "config.yaml").write_text("workflow:\n  auto_commit: true\n")
    for title in ("alpha", "beta"):
        r = _goc(repo, "new", title, "--summary", "probe card", "--gate", "none")
        if r.returncode != 0:
            raise RuntimeError(f"goc new {title} failed: {r.stderr}")
        readme = repo / ".game-of-cards" / "deck" / title / "README.md"
        # Author the scaffold, then publish it: `_git_auto_commit` drops draft
        # cards from the commit set, so an unpublished scaffold never reaches
        # the `git commit` this card is about.
        readme.write_text(
            readme.read_text()
            .replace("- [ ] (replace with real criteria)", "- [ ] MECHANICAL: real criterion")
            .replace("(write the design doc here)", "Body.")
        )
        r = _goc(repo, "publish", title, "--no-commit")
        if r.returncode != 0:
            raise RuntimeError(f"goc publish {title} failed: {r.stderr}")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=repo, check=True)


def main() -> int:
    findings: list[str] = []
    for label, args, verb_line_prefix in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _seed(repo)
            result = _goc(repo, *args)
            lines = result.stdout.splitlines()
            print(f"--- goc {' '.join(args)}  (stdout through a pipe) ---")
            for i, line in enumerate(lines):
                print(f"  [{i}] {line}")

            if result.returncode != 0:
                findings.append(f"{label}: exited {result.returncode}")
                continue
            if "  committed" not in lines:
                findings.append(f"{label}: no commit landed — case did not exercise the path")
                continue

            leaked = [ln for ln in lines if any(p.match(ln) for p in _PORCELAIN)]
            if leaked:
                findings.append(f"{label}: git porcelain on goc stdout: {leaked[0]!r}")

            verb_idx = next(
                (i for i, ln in enumerate(lines) if ln.startswith(verb_line_prefix)), None
            )
            if verb_idx is None:
                findings.append(f"{label}: verb report line {verb_line_prefix!r} missing")
            elif leaked:
                first_leak = min(i for i, ln in enumerate(lines) if ln in leaked)
                if first_leak < verb_idx:
                    findings.append(
                        f"{label}: git line at [{first_leak}] precedes the verb report "
                        f"at [{verb_idx}] — output reordered under a pipe"
                    )
            print()

    if findings:
        print("defect present:")
        for f in findings:
            print(f"  - {f}")
        return 1
    print("defect fixed: no git porcelain on goc stdout; verb report in code order")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
