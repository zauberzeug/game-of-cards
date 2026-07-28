#!/usr/bin/env python3
"""A prohibition guard whose scanner stops matching keeps the build green.

Several tests in `tests/` are *prohibition guards*: they scan a source or doc
tree for an offending shape and assert the offender list is empty. The shape of
that assertion is `assertEqual([], offenders)` — which passes both when the
tree is clean AND when the scanner has quietly stopped matching anything.
Nothing distinguishes the two.

This script simulates scanner death. For each guard it takes the prohibition
pattern, rewrites it to a regex that can never match, runs that guard's own
tests, and reports the verdict:

  STILL GREEN  — the scanner is dead and no test noticed. Fail-open.
  CAUGHT       — some test in the file exercises the scanner against source
                 that DOES offend, so killing the pattern turns the build red.

Nothing in the repo is modified: each guard is copied to a temp file with its
`ROOT` rebound to an absolute path, and the mutation is applied to the copy.

Exits non-zero while any prohibition guard is fail-open.
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
sys.path.insert(0, str(ROOT))

NEVER_MATCHES = '"(?!x)x"'

# (test file, prohibition-scanner name). Each names a pattern the guard uses
# with "this shape must NOT appear" semantics — the fail-open class. Presence
# and cardinality guards (`assertIn`, `assertEqual(count, 1)`) are excluded
# deliberately: killing their scanner drops the count to zero, so they fail
# closed and need no sensitivity test.
GUARDS = [
    ("tests/test_guidance_accuracy.py", "_STALE_PATTERN"),
    ("tests/test_guidance_accuracy.py", "_STALE_BICONDITIONAL"),
    ("tests/test_guidance_accuracy.py", "_STALE_STUB"),
    ("tests/test_skill_frontmatter_strict_yaml.py", "NESTED_MAPPING_COLON"),
    # positive control — a guard that DOES prove its own sensitivity
    ("tests/test_count_message_pluralization.py", "HARDCODED_PLURAL"),
]

# `NAME = re.compile(...)` up to the end of that logical assignment.
def _kill_pattern(source: str, name: str) -> str | None:
    """Rewrite `name`'s re.compile(...) argument so it can never match."""
    anchor = re.search(rf"^(\s*){re.escape(name)}\s*=\s*re\.compile\(", source, re.MULTILINE)
    if anchor is None:
        return None
    # walk to the matching close paren of re.compile(
    depth, i = 1, anchor.end()
    while i < len(source) and depth:
        depth += (source[i] == "(") - (source[i] == ")")
        i += 1
    indent = anchor.group(1)
    return source[: anchor.start()] + f"{indent}{name} = re.compile({NEVER_MATCHES})" + source[i:]


def _run_guard(path: Path, mutation: str | None) -> tuple[bool, str]:
    """Run one guard file (optionally with a scanner killed). True == passed."""
    source = path.read_text(encoding="utf-8")
    if mutation is not None:
        killed = _kill_pattern(source, mutation)
        if killed is None:
            return True, f"pattern {mutation} not found"
        source = killed
    # the copy lives elsewhere, so pin ROOT instead of deriving it from __file__
    source = source.replace("Path(__file__).resolve().parents[1]", f'Path(r"{ROOT}")')
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / path.name
        copy.write_text(source, encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "-v", path.name],
            cwd=tmp, env=env, capture_output=True, text=True,
        )
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip().splitlines()[-1]


print("baseline — every guard passes on the unmodified tree:")
for rel in dict.fromkeys(g[0] for g in GUARDS):
    ok, tail = _run_guard(ROOT / rel, None)
    print(f"  {'PASS' if ok else 'FAIL'}  {rel}  ({tail})")

print("\nscanner killed — does anything notice?")
fail_open: list[str] = []
for rel, name in GUARDS:
    ok, _ = _run_guard(ROOT / rel, name)
    if ok:
        fail_open.append(f"{rel}::{name}")
        print(f"  STILL GREEN  {rel}::{name}")
    else:
        print(f"  CAUGHT       {rel}::{name}")

print()
if fail_open:
    print(
        f"FAIL: {len(fail_open)} prohibition guard(s) keep passing with a dead "
        "scanner — they assert an empty offender list without ever proving the "
        "list can be non-empty:"
    )
    for entry in fail_open:
        print(f"  {entry}")
    sys.exit(1)
print("PASS: every prohibition guard turns red when its scanner stops matching")
