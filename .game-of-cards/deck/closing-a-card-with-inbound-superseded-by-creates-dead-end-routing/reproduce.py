"""Reproduce: close-time verbs do not check for inbound `superseded_by` references.

Sets up `A.superseded_by == [B]` with B live (`open`), then exercises each
of the four close-time paths on B:

  1. `goc done B`
  2. `goc done --bundle B unrelated`
  3. `goc status B disproved`
  4. `goc status B superseded --by C`

Each path is rerun against a freshly-seeded deck so the rows are independent.
After the fix, each close must exit non-zero with an error mentioning the
inbound `superseded_by` holder (`A`); `A`'s forward routing pointer must
still land on B in status `open`.

Exit code 0 means every close-time path was rejected as expected; non-zero
means at least one close slipped through (defect still fires).
"""

from __future__ import annotations

import os
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


REPO_ROOT = _repo_root()
sys.path.insert(0, str(REPO_ROOT))


def _write_card(
    deck_dir: Path,
    title: str,
    *,
    status: str = "open",
    superseded_by: list[str] | None = None,
    supersedes: list[str] | None = None,
    closed_at: str | None = None,
    dod_done: bool = False,
) -> None:
    card_dir = deck_dir / title
    card_dir.mkdir(parents=True, exist_ok=True)
    if superseded_by:
        sb_yaml = "\n".join([f"  - {r}" for r in superseded_by])
        sb_block = f"superseded_by:\n{sb_yaml}"
    else:
        sb_block = "superseded_by: []"
    if supersedes:
        sp_yaml = "\n".join([f"  - {r}" for r in supersedes])
        sp_block = f"supersedes:\n{sp_yaml}"
    else:
        sp_block = "supersedes: []"
    closed_yaml = f'"{closed_at}"' if closed_at else "null"
    dod_mark = "x" if dod_done else " "
    (card_dir / "README.md").write_text(
        f"""---
title: {title}
summary: ""
status: {status}
stage: null
contribution: medium
created: "2026-05-30T00:00:00Z"
closed_at: {closed_yaml}
human_gate: none
advances: []
advanced_by: []
{sb_block}
{sp_block}
tags: [bug]
definition_of_done: |
  - [{dod_mark}] TDD: placeholder
---

# {title}

Placeholder.
"""
    )
    (card_dir / "log.md").write_text("")


def _run_goc(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", "-m", "goc.cli", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


def _make_scratch_deck(tmp_root: Path, label: str) -> tuple[Path, dict[str, str]]:
    scratch = tmp_root / label
    deck_dir = scratch / ".game-of-cards" / "deck"
    deck_dir.mkdir(parents=True)
    (scratch / ".game-of-cards" / "config.yaml").write_text("skills_source: vendored\n")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return scratch, env


def main() -> int:
    rows: list[tuple[str, int, str, str]] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)

        # Path 1 — goc done B
        scratch, env = _make_scratch_deck(tmp_root, "p1-done")
        deck = scratch / ".game-of-cards" / "deck"
        _write_card(deck, "card-a", status="superseded", superseded_by=["card-b"])
        _write_card(deck, "card-b", status="open", supersedes=["card-a"], dod_done=True)
        result = _run_goc(["done", "card-b"], cwd=scratch, env=env)
        tail = (result.stderr or "").strip().splitlines()
        rows.append(("done card-b", result.returncode, tail[-1] if tail else "(no stderr)",
                     (deck / "card-b" / "README.md").read_text()))

        # Path 2 — goc done --bundle card-b unrelated
        scratch, env = _make_scratch_deck(tmp_root, "p2-bundle")
        deck = scratch / ".game-of-cards" / "deck"
        _write_card(deck, "card-a", status="superseded", superseded_by=["card-b"])
        _write_card(deck, "card-b", status="open", supersedes=["card-a"], dod_done=True)
        _write_card(deck, "unrelated", status="open", dod_done=True)
        result = _run_goc(["done", "--bundle", "card-b", "unrelated"], cwd=scratch, env=env)
        tail = (result.stderr or "").strip().splitlines()
        rows.append(("done --bundle card-b unrelated", result.returncode,
                     tail[-1] if tail else "(no stderr)",
                     (deck / "card-b" / "README.md").read_text()))

        # Path 3 — goc status card-b disproved
        scratch, env = _make_scratch_deck(tmp_root, "p3-disproved")
        deck = scratch / ".game-of-cards" / "deck"
        _write_card(deck, "card-a", status="superseded", superseded_by=["card-b"])
        _write_card(deck, "card-b", status="open", supersedes=["card-a"])
        result = _run_goc(["status", "card-b", "disproved", "--no-commit"], cwd=scratch, env=env)
        tail = (result.stderr or "").strip().splitlines()
        rows.append(("status card-b disproved", result.returncode,
                     tail[-1] if tail else "(no stderr)",
                     (deck / "card-b" / "README.md").read_text()))

        # Path 4 — goc status card-b superseded --by card-c
        scratch, env = _make_scratch_deck(tmp_root, "p4-superseded")
        deck = scratch / ".game-of-cards" / "deck"
        _write_card(deck, "card-a", status="superseded", superseded_by=["card-b"])
        _write_card(deck, "card-b", status="open", supersedes=["card-a"])
        _write_card(deck, "card-c", status="open")
        result = _run_goc(
            ["status", "card-b", "superseded", "--by", "card-c", "--no-commit"],
            cwd=scratch,
            env=env,
        )
        tail = (result.stderr or "").strip().splitlines()
        rows.append(("status card-b superseded --by card-c", result.returncode,
                     tail[-1] if tail else "(no stderr)",
                     (deck / "card-b" / "README.md").read_text()))

    print(f"{'CLOSE INVOCATION':<42} {'EXITCODE':<10} STDERR TAIL")
    print("-" * 100)
    for invocation, code, tail, _ in rows:
        print(f"{invocation:<42} {code:<10} {tail}")

    print()
    print("Interpretation:")
    print("  BEFORE fix — every row exits 0 (defect fires; B gets flipped to a")
    print("               terminal status with A.superseded_by=[B] still pointing")
    print("               at it; `goc validate` then errors reactively).")
    print("  AFTER  fix — every row exits non-zero with an error naming the")
    print("               inbound holder (`card-a`); no status mutation occurs.")

    failures: list[tuple[str, int, str]] = []
    for invocation, code, tail, b_readme in rows:
        if code == 0:
            failures.append((invocation, code, tail))
            continue
        if "card-a" not in tail and "superseded_by" not in tail:
            failures.append((invocation, code, tail))

    if failures:
        print()
        print("FAIL: the following close-time invocations were not properly rejected:")
        for invocation, code, tail in failures:
            print(f"  - {invocation}: exitcode={code}, stderr={tail!r}")
        return 1

    # Each B's README must still show status: open after a rejected close.
    for invocation, _, _, b_readme in rows:
        assert "status: open" in b_readme, (
            f"expected card-b to remain status: open after rejected {invocation!r}; "
            f"got README:\n{b_readme}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
