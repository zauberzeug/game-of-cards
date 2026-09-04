"""Proof that `goc.md` — the published CLI reference — steers authors onto the
deprecated `status: blocked` and never names the overlay that replaced it.

Two claims, checked independently:

  1. STATIC. The "Common verbs" table's `goc status` row lists `blocked` as a
     normal target state with no deprecation marker, and the whole document
     never mentions `goc wait` / `waiting_on` / the impediment overlay. The
     skill bodies (the authoritative surface) say `blocked` is deprecated.
  2. BEHAVIORAL. Following that row verbatim produces a card that validates
     clean yet vanishes from every `status: open` query with no reason
     recorded — exactly the failure the three-axis model replaced. The
     documented replacement (`goc wait`) keeps the card visible and only
     withholds it from `--ready`.

Exits non-zero while the defect stands; zero once `goc.md` marks `blocked`
deprecated and documents the overlay.
"""

from __future__ import annotations

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
GOC_MD = ROOT / "goc.md"
SKILLS = ROOT / "goc" / "templates" / "skills"

# The `goc status` row of goc.md's "Common verbs" table.
_STATUS_ROW = re.compile(r"^\|\s*`goc status [^`]*`\s*\|(?P<cell>[^|]*)\|", re.M)

# Words that would mark the row's `blocked` mention as deprecated.
_DEPRECATION = ("deprecat", "legacy", "removed", "do not use")

# The mechanism that replaced `blocked`.
_REPLACEMENT = ("goc wait", "waiting_on", "impediment overlay")


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin", "HOME": str(cwd)},
        capture_output=True,
        text=True,
        check=False,
    )


def static_claims() -> list[str]:
    text = GOC_MD.read_text(encoding="utf-8")
    failures: list[str] = []

    m = _STATUS_ROW.search(text)
    if m is None:
        failures.append("goc.md lost its `goc status` row — re-anchor this check.")
    else:
        cell = m.group("cell")
        line = m.group(0).strip()
        print("goc.md `goc status` row:")
        print(f"  {line}")
        if "blocked" in cell and not any(w in cell.lower() for w in _DEPRECATION):
            failures.append(
                "the `goc status` row offers `blocked` as a normal target "
                "state with no deprecation marker"
            )

    missing = [w for w in _REPLACEMENT if w not in text]
    print(f"\ngoc.md mentions of the replacement mechanism: missing={missing}")
    if len(missing) == len(_REPLACEMENT):
        failures.append(
            "goc.md never mentions `goc wait` / `waiting_on` / the impediment "
            "overlay, so it offers no correct alternative"
        )

    # The authoritative surface the purge card actually updated.
    marked = sorted(
        p.relative_to(ROOT).as_posix()
        for p in SKILLS.rglob("*.md")
        if "blocked" in (t := p.read_text(encoding="utf-8"))
        and any(w in t.lower() for w in _DEPRECATION)
    )
    print(f"\nskill bodies that call `blocked` deprecated ({len(marked)}):")
    for p in marked:
        print(f"  {p}")
    return failures


def behavioral_claim() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="goc-blocked-doc-") as tmp:
        repo = Path(tmp)
        (repo / ".game-of-cards" / "deck").mkdir(parents=True)
        _run(["new", "probe-card", "--summary", "probe", "--no-commit"], repo)

        card = repo / ".game-of-cards" / "deck" / "probe-card" / "README.md"
        card.write_text(
            card.read_text(encoding="utf-8").replace(
                "- [ ] (replace with real criteria)", "- [ ] MECHANICAL: criteria"
            ),
            encoding="utf-8",
        )
        _run(["publish", "probe-card", "--no-commit"], repo)

        # A) exactly what goc.md's `goc status` row tells the reader to run.
        _run(["status", "probe-card", "blocked", "--no-commit"], repo)
        blocked_queue = _run([], repo).stdout.strip()
        blocked_validate = _run(["validate"], repo).stdout.strip().splitlines()[-1]
        print("\nA) after the documented `goc status probe-card blocked`:")
        print(f"  goc          -> {blocked_queue}")
        print(f"  goc validate -> {blocked_validate}")

        # B) the replacement goc.md never names.
        _run(["status", "probe-card", "open", "--no-commit"], repo)
        _run(["wait", "probe-card", "--reason", "external", "--no-commit"], repo)
        wait_queue = _run([], repo).stdout.strip().splitlines()
        wait_ready = _run(["--ready"], repo).stdout.strip().splitlines()[-1]
        print("\nB) after the undocumented `goc wait probe-card --reason external`:")
        for line in wait_queue:
            print(f"  goc          -> {line}")
        print(f"  goc --ready  -> {wait_ready}")

        if "probe-card" in blocked_queue:
            print("\n(behavioral claim no longer holds — blocked card stays queued)")
        else:
            failures.append(
                "the documented `blocked` flip drops the card out of the "
                "default `status: open` queue with no reason recorded, while "
                "the undocumented `goc wait` keeps it visible"
            )
    return failures


def main() -> int:
    print("=" * 72)
    print("STATIC: goc.md vs the skill bodies")
    print("=" * 72)
    failures = static_claims()

    print()
    print("=" * 72)
    print("BEHAVIORAL: what following the doc actually produces")
    print("=" * 72)
    failures += behavioral_claim()

    print()
    if failures:
        print(f"DEFECT STANDS ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("FIXED: goc.md deprecates `blocked` and documents the overlay.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
