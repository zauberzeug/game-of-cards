"""Reproduce the misleading-error defect in `_run_automated_check`.

When `layer_2_project_dod[*].cmd` is written as a YAML scalar string
with whitespace (the natural shorthand a first-time user reaches for,
e.g. `cmd: "pytest -q"`), `subprocess.run(cmd, ...)` without
`shell=True` treats the WHOLE string as the executable name and raises
`FileNotFoundError`. The error handler at engine.py:3758 then formats
the message with `cmd[0]` — for a string, that is the FIRST CHARACTER,
producing `"command not found: p"` instead of
`"command not found: pytest -q"`.

The contract that `cmd` must be a list of tokens is undocumented in
`goc/templates/game_of_cards/config.yaml` (no example) and unvalidated
in `load_deck_config()`. Today's reproduce exits non-zero; after a fix
that either validates the shape or formats the missing-cmd message
correctly, this script should exit zero.
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

from goc.engine import _run_automated_check  # noqa: E402


def main() -> int:
    print("Case 1 — cmd as a list (correct shape).")
    passed, summary = _run_automated_check({"cmd": ["true"]})
    print(f"  cmd=['true']      passed={passed!r}  summary={summary!r}")
    list_ok = passed is True

    print("Case 2 — cmd as a YAML scalar string with whitespace.")
    passed, summary = _run_automated_check({"cmd": "pytest -q"})
    print(f"  cmd='pytest -q'   passed={passed!r}  summary={summary!r}")
    misleading = summary == "command not found: p"

    print()
    if list_ok and misleading:
        print("DEFECT CONFIRMED: scalar-string cmd is silently accepted and the")
        print("missing-command error reports just the first character of the cmd")
        print("string. After a fix that validates the cmd shape or formats the")
        print("error without cmd[0]-indexing a string, this script exits zero.")
        return 1

    print("Defect did not fire — either the shape is now validated upstream,")
    print("or the error formatter no longer mis-indexes a string cmd.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
