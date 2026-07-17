#!/usr/bin/env python3
"""Retune the autonomous GitHub Actions cadence (repo-local dev tool).

GitHub Actions `cron:` is a *literal* string in the workflow file —
`schedule:` cannot read a config value — so making the cadence
"configurable" means rewriting those literals in place. This script
rewrites the `- cron:` line and the adjacent managed `# cadence:`
comment in each autonomous workflow from a small interval spec.

Query the current cadence::

    python3 scripts/set_cadence.py --show

Change it (then commit and push — scheduled workflows only take effect
from the *default branch*)::

    python3 scripts/set_cadence.py --pull 1h --audit 3h --refine 3h

Interval specs: ``<N>h`` where N divides 24 (1, 2, 3, 4, 6, 8, 12) or
``24h``; ``<N>d`` for every-N-days (``1d`` is daily; ``Nd`` maps to a
day-of-month ``*/N`` step, which realigns at each month boundary — gaps
near month-end are shorter than N days); and ``1w`` for exact weekly
(every Monday, via the drift-free day-of-week field). Per-workflow minute
offsets are fixed (pull :13, audit :15, refine :45) so the three
deck-mutating cloud agents never launch on the same minute on ``main``.

This tool is intentionally **repo-local**: it targets THIS repo's own
autonomous workflow files, which ``goc install`` does not ship to
consumers. It uses only the standard library so ``python3
scripts/set_cadence.py`` works without ``uv``.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    """Walk up from this file to the repo root (the dir holding pyproject.toml)."""
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


# key -> (workflow filename, minute offset, human label). The offsets keep
# the three scheduled deck agents off each other's launch minute on `main`.
WORKFLOWS: dict[str, tuple[str, int, str]] = {
    "pull": ("pull-card.yml", 13, "pull-card"),
    "audit": ("audit-deck.yml", 15, "audit-deck"),
    "refine": ("refine-deck.yml", 45, "refine-deck"),
}

_CRON_RE = re.compile(r"^[ \t]*- cron: .*$", re.MULTILINE)
_CADENCE_RE = re.compile(r"^[ \t]*# cadence: .*$", re.MULTILINE)
_SPEC_RE = re.compile(r"^(\d+)\s*([hdw])$")


def interval_to_cron(spec: str, offset: int) -> str:
    """Translate an interval spec + minute offset into a 5-field cron string.

    Supported:
    - ``<N>h`` for N in {1, 2, 3, 4, 6, 8, 12} (must divide 24 so the
      ``*/N`` hour step doesn't reset at midnight), or ``24h``.
    - ``<N>d`` for every-N-days, 1 ≤ N ≤ 30: ``1d`` → daily; ``Nd`` (N≥2)
      → a day-of-month ``*/N`` step. cron's ``*/N`` day field realigns at
      each month boundary, so this is "roughly every N days" — the gap
      across a month end is shorter than N. That is the standard cron
      approximation; there is no exact every-N-days cron. N > 30 is
      rejected: cron's day-of-month field caps at 31, so a ``*/N`` step
      with N ≥ 31 matches only the 1st and cannot represent the requested
      cadence.
    - ``1w`` → exact weekly via the day-of-week field (every Monday); this
      one is drift-free. ``Nw`` (N≥2) has no clean cron and is rejected.

    Anything else raises ``ValueError``.
    """
    if not 0 <= offset <= 59:
        raise ValueError(f"minute offset {offset} out of range 0..59")
    m = _SPEC_RE.match(spec.strip().lower())
    if not m:
        raise ValueError(
            f"unrecognized interval {spec!r}; use <N>h (1,2,3,4,6,8,12), 24h, <N>d, or 1w"
        )
    n, unit = int(m.group(1)), m.group(2)
    if unit == "w":
        if n != 1:
            raise ValueError(
                f"{spec!r}: only 1w is expressible in cron (exact weekly via the "
                "day-of-week field); every-N-weeks has no clean cron — use 1w or <N>d"
            )
        # exact weekly: every Monday (matches this repo's historical weekly slot).
        return f"{offset} 0 * * 1"
    if unit == "d":
        if n < 1:
            raise ValueError(f"{spec!r}: day interval must be >= 1")
        if n > 30:
            raise ValueError(
                f"{spec!r}: day interval must be <= 30 "
                "(cron's day-of-month field caps at 31, so a */N step with "
                "N >= 31 matches only the 1st and fires monthly)"
            )
        if n == 1:
            return f"{offset} 0 * * *"
        # day-of-month */N: roughly every N days, realigning each month.
        return f"{offset} 0 */{n} * *"
    # unit == "h"
    if n == 24:
        return f"{offset} 0 * * *"
    if not 1 <= n <= 23 or 24 % n != 0:
        raise ValueError(
            f"{spec!r}: hour interval must divide 24 (1,2,3,4,6,8,12) or be 24h"
        )
    hour_field = "*" if n == 1 else f"*/{n}"
    return f"{offset} {hour_field} * * *"


def _workflow_path(repo_root: Path, key: str) -> Path:
    filename = WORKFLOWS[key][0]
    return repo_root / ".github" / "workflows" / filename


def _cadence_comment(label: str, spec: str, offset: int) -> str:
    return (
        f"    # cadence: {label} every {spec} (minute offset :{offset:02d}) "
        "— managed by scripts/set_cadence.py; retune via that script, "
        "not the two lines below"
    )


def retune(repo_root: Path, key: str, spec: str, *, write: bool = True) -> tuple[str, bool]:
    """Rewrite one workflow's cron + cadence comment. Return ``(cron, changed)``.

    ``write=False`` runs every validation (spec, file existence, managed-line
    guards) without touching the file — the dry-run pass ``main`` uses to make
    a multi-workflow retune all-or-nothing.
    """
    filename, offset, label = WORKFLOWS[key]
    path = _workflow_path(repo_root, key)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    cron = interval_to_cron(spec, offset)
    text = path.read_text()

    new_cron_line = f"    - cron: '{cron}'"
    new_comment = _cadence_comment(label, spec, offset)

    # Lambda replacements: sidestep re's interpretation of \1 / \g<> in
    # replacement strings (a cron like */3 is fine today, but never risk it).
    # Unbounded subn so the counts see every match — the guards below refuse
    # multi-schedule workflows instead of half-retuning them (the file is only
    # written after both guards pass).
    text2, n_cron = _CRON_RE.subn(lambda _m: new_cron_line, text)
    if n_cron != 1:
        hint = (
            "; this tool manages a single schedule per workflow — retune "
            "multi-schedule workflows by hand"
            if n_cron > 1
            else ""
        )
        raise ValueError(
            f"{filename}: expected exactly one `- cron:` line, found {n_cron}{hint}"
        )
    text3, n_cad = _CADENCE_RE.subn(lambda _m: new_comment, text2)
    if n_cad != 1:
        hint = (
            "; add a `    # cadence: ...` line above `- cron:` first"
            if n_cad == 0
            else "; remove the duplicate marker lines"
        )
        raise ValueError(
            f"{filename}: expected exactly one `# cadence:` marker line, found "
            f"{n_cad}{hint}"
        )

    changed = text3 != text
    if changed and write:
        path.write_text(text3)
    return cron, changed


def current_cadence(repo_root: Path) -> dict[str, dict[str, str]]:
    """Read each workflow's cron + cadence comment (for ``--show``)."""
    out: dict[str, dict[str, str]] = {}
    for key, (filename, _offset, _label) in WORKFLOWS.items():
        path = _workflow_path(repo_root, key)
        if not path.exists():
            out[key] = {"file": filename, "cron": "(missing file)", "comment": ""}
            continue
        text = path.read_text()
        crons = [
            m.strip()[len("- cron: "):].strip().strip("'\"")
            for m in _CRON_RE.findall(text)
        ]
        comments = [
            m.strip()[len("# cadence: "):].strip()
            for m in _CADENCE_RE.findall(text)
        ]
        out[key] = {
            "file": filename,
            "cron": ", ".join(crons) if crons else "(no cron)",
            "comment": "; ".join(comments),
        }
    return out


def _print_cadence(cadence: dict[str, dict[str, str]]) -> None:
    width = max(len(v["file"]) for v in cadence.values())
    for key in WORKFLOWS:
        v = cadence[key]
        print(f"  {v['file']:<{width}}  cron: {v['cron']}")
        if v["comment"]:
            print(f"  {'':<{width}}  ({v['comment']})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="set_cadence.py",
        description="Query or retune the autonomous GitHub Actions cadence (repo-local).",
        epilog="Interval specs: <N>h (1,2,3,4,6,8,12), 24h, <N>d (<=30), or 1w. Commit & push to apply.",
    )
    parser.add_argument(
        "--show", action="store_true", help="print the current cadence and exit"
    )
    parser.add_argument("--pull", metavar="INTERVAL", help="pull-card interval, e.g. 1h")
    parser.add_argument("--audit", metavar="INTERVAL", help="audit-deck interval, e.g. 3h")
    parser.add_argument(
        "--refine", metavar="INTERVAL", help="refine-deck interval, e.g. 3h"
    )
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    requested = {
        k: v for k, v in (("pull", args.pull), ("audit", args.audit), ("refine", args.refine)) if v
    }

    # No change requested (or --show wins): just report current state.
    if args.show or not requested:
        if not requested and not args.show:
            print(
                "No interval given; showing current cadence "
                "(use --pull/--audit/--refine to change it).\n"
            )
        _print_cadence(current_cadence(repo_root))
        return 0

    # All-or-nothing: dry-run every requested retune (spec validation via
    # interval_to_cron, file existence, managed-line guards) before the
    # mutation loop, so a failure exit always means no workflow file changed.
    for key, spec in requested.items():
        try:
            retune(repo_root, key, spec, write=False)
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    any_changed = False
    for key, spec in requested.items():
        cron, changed = retune(repo_root, key, spec)
        print(f"  {WORKFLOWS[key][0]:<16} cron: {cron:<14} ({'set' if changed else 'unchanged'})")
        any_changed = any_changed or changed

    if any_changed:
        print(
            "\nScheduled workflows run from the default branch — commit and "
            "push these changes for the new cadence to take effect."
        )
    else:
        print("\nNo changes (already at the requested cadence).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
