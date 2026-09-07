"""Ctrl-D at a goc confirmation prompt raises an uncaught EOFError.

Three interactive sites branch on `sys.stdin.isatty()` and guard EOF on the
NON-tty branch only:

    if sys.stdin.isatty():
        ans = input(...)                     # <- can raise EOFError, unguarded
    else:
        try:
            ans = sys.stdin.readline()...    # <- guarded, but returns "" at EOF
        except (EOFError, OSError):
            return default

`readline()` signals EOF by returning `""`, so the guarded branch never raises
and the `except` there is dead. `input()` DOES raise `EOFError` at EOF, and that
is the branch a real terminal takes — so pressing Ctrl-D crashes the verb.

Case 1 drives the two helpers directly under a pty with Ctrl-D on the line.
Case 2 runs the real `goc migrate` CLI the same way, in front of its
`shutil.rmtree`. Case 3 is the contrast that pins the defect: the SAME question
answered by an empty pipe declines cleanly, because that path is guarded.

Run:  uv run python .game-of-cards/deck/ctrl-d-at-a-goc-confirmation-prompt-crashes-with-a-traceback/reproduce.py
"""

from __future__ import annotations

import os
import pty
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

from goc import engine, install  # noqa: E402

CARD = """---
title: legacy-card
summary: "A legacy-tree card for the migrate prompt."
status: open
stage: null
contribution: low
created: 2026-01-01
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: nothing
---

# legacy-card

body
"""


def call_with_ctrl_d(fn):
    """Call `fn()` with stdin a real tty holding a leading Ctrl-D (EOF).

    This is exactly what a human pressing Ctrl-D at the prompt produces: the
    line discipline turns ^D at the start of a line into end-of-file, and
    `isatty()` stays True so the TTY branch is the one taken.
    """
    master, slave = pty.openpty()
    saved = sys.stdin
    sys.stdin = os.fdopen(slave, "r")
    os.write(master, b"\x04")
    try:
        return "returned", fn()
    except EOFError as exc:
        return "EOFError", exc
    finally:
        sys.stdin = saved
        os.close(master)


def case_1() -> bool:
    print("=== case 1: Ctrl-D at the two confirm helpers (tty) ===")
    crashed = False
    for label, fn in (
        ("engine.confirm", lambda: engine.confirm("Remove legacy tree?")),
        ("install._confirm", lambda: install._confirm("Remove leftover vendored layout?")),
    ):
        kind, value = call_with_ctrl_d(fn)
        if kind == "EOFError":
            crashed = True
            print(f"  {label}: EOFError({value})  <-- CRASH")
        else:
            print(f"  {label}: returned {value!r}")
    # The guard that IS present sits on a call that cannot raise.
    r, w = os.pipe()
    os.close(w)
    with os.fdopen(r) as at_eof:
        print(f"  (guarded branch: readline() at EOF -> {at_eof.readline()!r}, never raises)")
    return crashed


def _migrate_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    (repo / ".game-of-cards" / "deck").mkdir(parents=True)
    legacy = repo / "deck" / "legacy-card"
    legacy.mkdir(parents=True)
    (legacy / "README.md").write_text(CARD)
    subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
    return repo


def _run_migrate(repo: Path, *, stdin) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", "migrate"],
        cwd=repo,
        stdin=stdin,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )


def case_2(tmp: Path) -> bool:
    print("\n=== case 2: `goc migrate`, Ctrl-D at its rmtree confirmation (tty) ===")
    repo = _migrate_repo(tmp / "ctrl-d")
    master, slave = pty.openpty()
    os.write(master, b"\x04")
    try:
        proc = _run_migrate(repo, stdin=slave)
    finally:
        os.close(master)
        os.close(slave)
    crashed = "EOFError" in proc.stderr
    print(f"  exit={proc.returncode}  EOFError in stderr: {crashed}")
    tail = [ln for ln in proc.stderr.splitlines() if ln.strip()]
    for line in tail[-3:]:
        print(f"    {line}")
    print(f"  legacy deck/ still present: {(repo / 'deck').exists()}")
    return crashed


def case_3(tmp: Path) -> bool:
    print("\n=== case 3: same question, empty pipe (the guarded branch) ===")
    repo = _migrate_repo(tmp / "piped")
    proc = _run_migrate(repo, stdin=subprocess.DEVNULL)
    clean = "EOFError" not in proc.stderr
    print(f"  exit={proc.returncode}  EOFError in stderr: {not clean}")
    print(f"  stderr: {proc.stderr.strip()!r}")
    print(f"  legacy deck/ still present: {(repo / 'deck').exists()}")
    return clean


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        helpers_crashed = case_1()
        cli_crashed = case_2(tmp)
        piped_clean = case_3(tmp)

    print()
    if helpers_crashed or cli_crashed:
        print(
            "DEFECT: the TTY branch raises EOFError out of the verb, while the "
            "same refusal on the non-TTY branch is handled.\n"
            "Expected: Ctrl-D declines and returns the prompt's `default`, the "
            "outcome an empty pipe already produces."
        )
        return 1
    if not piped_clean:
        print("UNEXPECTED: the piped path regressed; it must keep declining cleanly.")
        return 1
    print(
        "FIXED: Ctrl-D no longer raises out of any confirmation prompt, and the "
        "piped decline is unchanged."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
