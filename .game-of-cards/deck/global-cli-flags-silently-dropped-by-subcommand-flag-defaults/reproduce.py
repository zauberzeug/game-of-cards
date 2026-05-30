"""Reproduce: goc global CLI flags silently dropped by subcommand defaults.

Exits non-zero while the defect is present. Once a remedy is in place
(parent-value preservation) and `_cmd_quality_pass` honours `--done`,
this script exits zero.

Defects demonstrated:

  1. `goc --status done quality-pass`        → status_flag='open'   (expected 'done')
  2. `goc --done quality-pass`               → done_flag=True ignored by handler
  3. `goc --contribution high new <title>`   → contribution='medium'(expected 'high')
  4. `goc --worker alice triage`             → worker=None          (expected 'alice')
"""
from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc.engine import _build_parser  # noqa: E402

parser = _build_parser()

failures: list[str] = []

cases = [
    # (argv, attribute, expected, label)
    (["--status", "done", "quality-pass"],   "status_flag",  "done",  "--status done quality-pass"),
    (["--status", "all",  "quality-pass"],   "status_flag",  "all",   "--status all quality-pass"),
    (["--contribution", "high", "new", "x"], "contribution", "high",  "--contribution high new x"),
    (["--worker", "alice", "triage"],        "worker",       "alice", "--worker alice triage"),
]

print("global-flag-vs-subparser-default collision check\n")
print(f"{'invocation':45}  {'attr':14} {'observed':12} {'expected':12} verdict")
print("-" * 100)

for argv, attr, expected, label in cases:
    args = parser.parse_args(argv)
    observed = getattr(args, attr, "<missing>")
    ok = observed == expected
    verdict = "OK" if ok else "FAIL"
    print(f"goc {label:42}  {attr:14} {observed!r:12} {expected!r:12} {verdict}")
    if not ok:
        failures.append(f"{label}: {attr}={observed!r} (expected {expected!r})")

# Separate check: `--done` shortcut for quality-pass. The parser writes
# `done_flag=True` but `_cmd_quality_pass` reads only `status_flag`, so
# the documented "Shortcut for --status done" expands to a no-op for
# this subcommand.
args = parser.parse_args(["--done", "quality-pass"])
done_flag = getattr(args, "done_flag", None)
status_flag = getattr(args, "status_flag", None)
# After a fix that honours the shortcut, the handler should observe
# status_flag == "done" (or the equivalent). Today, status_flag is
# 'open' AND done_flag is never consulted.
import inspect  # noqa: E402
import goc.engine as eng  # noqa: E402

handler_src = inspect.getsource(eng._cmd_quality_pass)
honours_done = "done_flag" in handler_src
print()
print(f"goc --done quality-pass: done_flag={done_flag!r}, status_flag={status_flag!r}")
print(f"  _cmd_quality_pass references done_flag? {honours_done}")
if not honours_done:
    failures.append("_cmd_quality_pass ignores args.done_flag (silent no-op for the documented shortcut)")

print()
if failures:
    print(f"FAIL: {len(failures)} collision site(s) still present:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("PASS: all global flags survive into the subcommand handler.")
    sys.exit(0)
