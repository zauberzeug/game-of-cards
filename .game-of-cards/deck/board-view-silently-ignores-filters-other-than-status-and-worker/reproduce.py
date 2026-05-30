"""Reproduce: `--board` silently ignores every filter except `--status`
(`--done`) and `--worker`.

The default-command path computes `filtered` via `filter_cards(..., ready=,
tags=, human_gate=, contribution=, advances=, advanced_by=, ...)` and a
following `waiting` post-filter, but in the `--board` branch
(`engine.py:2858`) it discards that result whenever the user did not pass
`--status` / `--done` / `--worker`:

    board_cards = filtered if (status_filter_explicit or args.worker) else cards

So `goc --ready --board`, `goc --tag bug --board`, `goc --human-gate none
--board`, `goc --contribution high --board`, `goc --waiting --board`,
`goc --advances X --board`, `goc --advanced-by X --board`, and
`goc --closed-since 7d --board` all render the entire deck. The same
filters drive the table renderer correctly, so this is specifically the
`--board` code path.

This script builds a synthetic three-card deck (one open & ready, one
open & gated, one open with a different tag) in a temp directory, runs
`goc` from inside it (deck root is resolved from cwd), and compares the
table vs. board renderers.
"""
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


def _write_card(deck_dir: Path, title: str, *, gate: str, tags: list[str]) -> None:
    card_dir = deck_dir / title
    card_dir.mkdir(parents=True, exist_ok=True)
    tag_inline = "[" + ", ".join(tags) + "]"
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        'summary: ""\n'
        "status: open\n"
        "stage: null\n"
        "contribution: medium\n"
        'created: "2026-05-30T00:00:00Z"\n'
        "closed_at: null\n"
        f"human_gate: {gate}\n"
        "advances: []\n"
        "advanced_by: []\n"
        f"tags: {tag_inline}\n"
        "definition_of_done: |\n"
        "  - [ ] placeholder\n"
        "---\n"
        f"\n# {title}\n"
    )
    (card_dir / "log.md").write_text("")


def _run(cwd: Path, *args) -> str:
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args, "--no-color"],
        cwd=cwd, env=env, capture_output=True, text=True, check=False,
    ).stdout


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        # Minimal scaffolding so engine resolves the deck without triggering
        # legacy/dual-tree warnings.
        deck = tmp_root / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        # Stub pyproject.toml so the parent-walk doesn't reach the real one.
        (tmp_root / "pyproject.toml").write_text('[project]\nname = "stub"\n')

        # Ready card: open + human_gate=none + tag=bug
        _write_card(deck, "ready-bug-card", gate="none", tags=["bug"])
        # Gated card: open + human_gate=decision + tag=bug (filtered out by --ready)
        _write_card(deck, "gated-bug-card", gate="decision", tags=["bug"])
        # Unrelated tag: open + human_gate=decision + tag=documentation
        _write_card(deck, "documentation-card", gate="decision", tags=["documentation"])

        table_ready = _run(tmp_root, "--ready")
        table_tag = _run(tmp_root, "--tag", "documentation")
        board_ready = _run(tmp_root, "--ready", "--board")
        board_tag = _run(tmp_root, "--tag", "documentation", "--board")

        def has_row(haystack: str, title: str) -> bool:
            """True if `title` appears at the start of any output row (a card listing,
            not a substring of the leverage / active-notice line)."""
            return any(line.lstrip().startswith(title) for line in haystack.splitlines())

        results = []
        # Sanity: table renderer respects the filters.
        results.append(("table --ready shows ready-bug-card", has_row(table_ready, "ready-bug-card")))
        results.append(("table --ready hides gated-bug-card", not has_row(table_ready, "gated-bug-card")))
        results.append(("table --ready hides documentation-card", not has_row(table_ready, "documentation-card")))
        results.append(("table --tag=documentation shows documentation-card", has_row(table_tag, "documentation-card")))
        results.append(("table --tag=documentation hides ready-bug-card", not has_row(table_tag, "ready-bug-card")))

        # Defect: board renderer drops every filter except --status/--worker.
        results.append(("BUG: board --ready hides gated-bug-card", "gated-bug-card" not in board_ready))
        results.append(("BUG: board --ready hides documentation-card", "documentation-card" not in board_ready))
        results.append(("BUG: board --tag=documentation hides ready-bug-card", "ready-bug-card" not in board_tag))
        results.append(("BUG: board --tag=documentation hides gated-bug-card", "gated-bug-card" not in board_tag))

        for label, ok in results:
            print(f"{'PASS' if ok else 'FAIL'}  {label}")
        return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    sys.exit(main())
