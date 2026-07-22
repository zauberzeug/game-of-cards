"""Reproduce: goc wait --until accepts a trailing-newline date that then
crashes every full-value reader (goc validate, goc --waiting).

Exits non-zero while the defect fires; exits 0 once fixed.
"""
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

from goc.engine import _is_iso_date  # noqa: E402

BAD = "2026-08-01\n"

failures = []

# 1) The predicate itself: accepts a value its consumers cannot parse.
if _is_iso_date(BAD):
    failures.append(f"_is_iso_date({BAD!r}) is True — consumers parse the full value and raise")
print(f"_is_iso_date({BAD!r}) -> {_is_iso_date(BAD)} (want False)")

# 2) End-to-end: wait accepts it, validate then tracebacks.
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    subprocess.run(["git", "init", "-q", str(tmp)], check=True)
    deck = tmp / ".game-of-cards" / "deck"
    deck.mkdir(parents=True)

    def goc(*args):
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=tmp, capture_output=True, text=True,
            env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"},
        )

    assert goc("new", "probe-card").returncode == 0
    wait = goc("wait", "probe-card", "--until", BAD)
    print(f"goc wait --until {BAD!r} exit={wait.returncode} (want 2)")
    if wait.returncode == 0:
        failures.append("goc wait accepted the trailing-newline date")
        validate = goc("validate")
        crashed = "Traceback" in validate.stderr
        print(f"goc validate exit={validate.returncode} traceback={crashed} (want no traceback)")
        if crashed:
            failures.append("goc validate crashed with an uncaught traceback:\n"
                            + validate.stderr.strip().splitlines()[-1])

if failures:
    print("\n[FAIL] defect fires:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("\n[OK] defect no longer fires")
