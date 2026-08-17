#!/usr/bin/env python3
"""Measure how long this deck's repaired `file:line` citations stay correct.

Asking "how many cites are stale right now?" is not a stable question — the
answer collapses to nearly zero the moment a hygiene pass runs and climbs
again afterwards. This script asks the time-independent version instead:

  for each bulk citation-repair commit in the deck's history,
  what fraction of the numbers it wrote are already wrong at HEAD,
  and how long did that take?

A repair pass writes each number so that it points at the intended code in
the tree as of that commit. So the text at that line, read at that commit,
is what the cite means; if HEAD no longer has that text at that line, the
repair has decayed. Survival is measured per pass, so the verdict does not
depend on when the script is run relative to the last pass.

Exit 1 while the newest pass older than MIN_AGE_DAYS has decayed past
DECAY_BUDGET, 0 once repaired citations survive ordinary code growth.
"""

import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BULK_THRESHOLD = 20     # READMEs touched before a commit counts as a bulk pass
MIN_AGE_DAYS = 3        # ignore passes too recent to have been overtaken
DECAY_BUDGET = 0.25     # at most a quarter of a pass's cites may have decayed


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()

CITE_RE = re.compile(
    r"(?<![\w/.-])((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+"
    r"\.(?:py|md|ts|json|yaml|yml|sh|toml))[:#]L?(\d+)(?:\s*[-–]\s*L?(\d+))?(?![\w.])"
)
MIRROR = (
    "claude-plugin/",
    "codex-plugin/",
    "openclaw-plugin/",
    ".claude/",
    ".codex/",
    "goc/_vendor/",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    ).stdout


def git_ok(*args: str):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


TRACKED = git("ls-files").splitlines()
TRACKED_SET = set(TRACKED)
BY_BASE = defaultdict(list)
for _p in TRACKED:
    BY_BASE[os.path.basename(_p)].append(_p)


def resolve(path: str):
    if path in TRACKED_SET:
        return path
    cands = BY_BASE.get(os.path.basename(path), [])
    pool = [p for p in cands if p.endswith("/" + path)] or cands
    pool = [p for p in pool if not p.startswith(MIRROR)] or pool
    if not pool:
        return None
    if len(pool) == 1:
        return pool[0]
    pool.sort(key=lambda p: (p.count("/"), len(p)))
    if pool[0].count("/") == pool[1].count("/") and len(pool[0]) == len(pool[1]):
        return None
    return pool[0]


_BLOB: dict = {}


def blob(commit: str, path: str):
    key = (commit, path)
    if key not in _BLOB:
        out = git_ok("show", f"{commit}:{path}")
        _BLOB[key] = out.split("\n") if out is not None else None
    return _BLOB[key]


_HEAD: dict = {}


def head_lines(path: str):
    if path not in _HEAD:
        try:
            _HEAD[path] = (ROOT / path).read_text(
                encoding="utf-8", errors="replace"
            ).split("\n")
        except OSError:
            _HEAD[path] = None
    return _HEAD[path]


def cites_of(text: str):
    return {
        (m.group(1), int(m.group(2)))
        for m in CITE_RE.finditer(text)
    }


def bulk_passes():
    """Deck commits that rewrote citations across many cards at once."""
    out = git(
        "log", "--format=@%H %ct", "--name-only", "--", ".game-of-cards/deck"
    )
    commits, sha, when, files = [], None, 0, []
    for line in out.splitlines():
        if line.startswith("@"):
            if sha and len(files) >= BULK_THRESHOLD:
                commits.append((sha, when, files))
            parts = line[1:].split()
            sha, when, files = parts[0], int(parts[1]), []
        elif line.strip().endswith("README.md"):
            files.append(line.strip())
    if sha and len(files) >= BULK_THRESHOLD:
        commits.append((sha, when, files))
    return commits


def main() -> int:
    now = datetime.now(tz=timezone.utc)
    rows = []

    for sha, when, files in bulk_passes():
        parent = git("rev-parse", f"{sha}^").strip()
        if not parent:
            continue
        written = []
        for rel in files:
            after = git_ok("show", f"{sha}:{rel}")
            if after is None:
                continue
            before = git_ok("show", f"{parent}:{rel}") or ""
            # cites whose (path, line) pair this commit introduced
            for path, line in cites_of(after) - cites_of(before):
                target = resolve(path)
                if target is None:
                    continue
                src = blob(sha, target)
                if src is None or line > len(src):
                    continue
                anchor = src[line - 1]
                if not anchor.strip():
                    continue
                written.append((target, line, anchor))
        if len(written) < BULK_THRESHOLD:
            continue

        decayed = 0
        for target, line, anchor in written:
            cur = head_lines(target)
            if cur is None or line > len(cur) or cur[line - 1] != anchor:
                decayed += 1
        age = (now - datetime.fromtimestamp(when, tz=timezone.utc)).days
        subject = git("log", "-1", "--format=%s", sha).strip()
        rows.append((sha[:9], age, decayed, len(written), subject))

    if not rows:
        print("No bulk citation-repair pass found in this deck's history.")
        return 0

    print("Decay of each bulk citation-repair pass, measured at HEAD:\n")
    print(f"  {'commit':10s} {'age':>5s}  {'decayed':>14s}   subject")
    for sha, age, decayed, total, subject in rows:
        pct = 100.0 * decayed / total
        print(
            f"  {sha:10s} {age:>4d}d  {decayed:5d}/{total:<5d} ({pct:3.0f}%)  "
            f"{subject[:52]}"
        )

    judged = [r for r in rows if r[1] >= MIN_AGE_DAYS]
    if not judged:
        print(
            f"\nEvery pass is younger than {MIN_AGE_DAYS} days — too soon to judge."
        )
        return 0

    sha, age, decayed, total, _ = judged[0]
    rate = decayed / total
    print(
        f"\nnewest pass at least {MIN_AGE_DAYS} days old: {sha}, {age} days ago — "
        f"{decayed}/{total} of its citations ({100.0*rate:.0f}%) are already wrong, "
        f"budget {100.0*DECAY_BUDGET:.0f}%"
    )

    if rate > DECAY_BUDGET:
        growth = []
        for path in ("goc/engine.py", "goc/install.py"):
            cur = head_lines(path)
            old = blob(sha, path)
            if cur and old:
                growth.append(f"{path} {len(old)} -> {len(cur)} lines")
        if growth:
            print("  over that span: " + "; ".join(growth))
        print(
            "\nDEFECT PRESENT: a bare line number does not survive ordinary code "
            "growth, so citation repair is permanent recurring work and a reader "
            "cannot trust a cite between hygiene passes."
        )
        return 1

    print("\nPASS: repaired citations survive ordinary code growth.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
