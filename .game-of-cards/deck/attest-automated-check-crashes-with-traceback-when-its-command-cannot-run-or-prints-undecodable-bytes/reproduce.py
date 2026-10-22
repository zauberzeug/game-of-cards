"""Reproduce: `goc attest` crashes on an automated check that cannot run or
prints bytes that do not decode, instead of recording a FAIL row.

Each case builds a throwaway deck holding one card and one `kind: automated`
layer-2 check, runs `goc attest <card> --non-interactive` from the source
tree, and reports the exit code, whether stderr carries a traceback, and the
check's result row. The contract is the one the missing-command case already
honours: a `[ ] <check> — <why>` row, a closure-verification block in log.md,
and exit 2. Exits 1 while any crash case raises; 0 once all of them fail cleanly.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


ROOT = _repo_root()
CARD = "probe-card"
CONFIG = """\
layer_2_project_dod:
  - name: {name}
    kind: automated
    cmd: {cmd}
layer_3_goc_dod: []
workflow:
  auto_commit: false
"""


def _goc(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    env.pop("GOC_WORKTREE_DECK", None)
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, capture_output=True, text=True, check=False,
    )


def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join('"' + i.replace("\\", "\\\\").replace('"', '\\"') + '"' for i in items) + "]"


def run_case(label: str, name: str, make_cmd) -> bool:
    """Return True when the case crashed (the defect), False when it failed cleanly."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / ".game-of-cards" / "deck").mkdir(parents=True)
        (repo / ".game-of-cards" / "config.yaml").write_text(CONFIG.format(name=name, cmd=_yaml_list(make_cmd(repo))))
        new = _goc(repo, "new", CARD, "--summary", "Probe card.", "--no-commit")
        if new.returncode != 0:
            raise RuntimeError(f"goc new failed: {new.stderr}")
        r = _goc(repo, "attest", CARD, "--non-interactive")
        crashed = "Traceback" in r.stderr
        row = next((ln.strip() for ln in r.stdout.splitlines() if ln.strip().startswith(("[ ]", "[x]")) and name in ln), None)
        log = (repo / ".game-of-cards" / "deck" / CARD / "log.md").read_text()
        last = r.stderr.strip().splitlines()[-1] if crashed else ""
        print(f"{label}")
        print(f"  exit={r.returncode}  traceback={'YES' if crashed else 'no'}  "
              f"closure block written={'yes' if 'Closure verification' in log else 'NO'}")
        print(f"  row: {row or '(none)'}")
        if crashed:
            print(f"  stderr tail: {last}")
        return crashed


def _script(repo: Path, body: str, *, executable: bool) -> list[str]:
    path = repo / "check.sh"
    path.write_text(body)
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR if executable else mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    return [str(path)]


CONTROL = [
    ("control — check command does not exist (FileNotFoundError, already handled)",
     "missing-command", lambda repo: [str(repo / "no-such-check")]),
]
CASES = [
    ("case 1 — check script without the executable bit (PermissionError)",
     "not-executable", lambda repo: _script(repo, "#!/bin/sh\necho ok\n", executable=False)),
    ("case 2 — executable check script without a shebang line (ENOEXEC)",
     "no-shebang", lambda repo: _script(repo, "echo ok\n", executable=True)),
    ("case 3 — check exits 1 and prints bytes that are not UTF-8 (UnicodeDecodeError)",
     "undecodable-output",
     lambda repo: [sys.executable, "-c",
                   "import sys; sys.stderr.buffer.write(b'caf\\xe9 \\xff failed\\n'); sys.exit(1)"]),
]


def main() -> int:
    for label, name, make_cmd in CONTROL:
        run_case(label, name, make_cmd)
    crashes = [label for label, name, make_cmd in CASES if run_case(label, name, make_cmd)]
    print()
    if crashes:
        print(f"DEFECT CONFIRMED: {len(crashes)} of {len(CASES)} check shapes crash `goc attest` "
              "with a traceback instead of recording a FAIL row.")
        return 1
    print("OK: every check shape is recorded as a FAIL row; no traceback.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
