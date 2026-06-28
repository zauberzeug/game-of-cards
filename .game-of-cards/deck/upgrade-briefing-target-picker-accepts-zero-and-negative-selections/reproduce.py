"""Reproduce: the goc upgrade briefing-target picker accepts `0` and negative
selections because `found[int(raw) - 1]` uses Python negative indexing instead
of bounds-checking against the advertised 1-based range.

Exits 0 when the defect is FIXED (picker aborts with SystemExit(2) on `0` and
`-1`); exits 1 while the defect is present (picker silently selects a file).
"""

import io
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

from goc import install  # noqa: E402


def _run_picker(raw: str, found):
    """Drive _resolve_upgrade_briefing_target with `raw` fed over non-TTY stdin.

    Returns ('selected', <file>) if the picker chose a file, or
    ('abort', <exit_code>) if it called sys.exit().
    """
    orig_stdin = sys.stdin
    orig_detect = install._detect_briefing_targets_on_disk
    sys.stdin = io.StringIO(raw + "\n")
    install._detect_briefing_targets_on_disk = lambda target: tuple(found)
    try:
        choice = install._resolve_upgrade_briefing_target(
            Path("."), explicit_target=None, dry_run=False
        )
        return ("selected", choice)
    except SystemExit as exc:
        return ("abort", exc.code)
    finally:
        sys.stdin = orig_stdin
        install._detect_briefing_targets_on_disk = orig_detect


def main() -> int:
    found = ["AGENTS.md", "CLAUDE.md", "CLAUDE.local.md"]
    ok = True

    for raw in ("0", "-1"):
        kind, val = _run_picker(raw, found)
        if kind == "abort" and val == 2:
            print(f"raw={raw!r:5} -> abort (exit {val})  OK")
        else:
            print(
                f"raw={raw!r:5} -> {kind} {val!r}  DEFECT: "
                "out-of-range input should abort with exit 2"
            )
            ok = False

    # Sanity: a valid in-range selection must still work.
    kind, val = _run_picker("2", found)
    if kind == "selected" and val == "CLAUDE.md":
        print(f"raw={'2'!r:5} -> selected {val!r}  OK (in-range control)")
    else:
        print(f"raw={'2'!r:5} -> {kind} {val!r}  UNEXPECTED: in-range pick broke")
        ok = False

    if ok:
        print("\nPASS: picker rejects 0 and negative selections.")
        return 0
    print("\nFAIL: picker accepts out-of-range selections via negative indexing.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
