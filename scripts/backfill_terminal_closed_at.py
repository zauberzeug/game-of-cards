#!/usr/bin/env python3
"""Backfill `closed_at` on existing disproved / superseded cards.

Until card `record-closure-date-for-disproved-and-superseded-cards`,
`closed_at` was only written by `goc done`. Cards that exited via
`goc status <title> disproved|superseded` carry `closed_at: null`,
which the new symmetric validator rejects.

For each disproved/superseded card with `closed_at: null`, this script
asks git for the most recent commit touching the card's README and
writes that timestamp into the frontmatter. Cards whose history yields
no useful timestamp (e.g. created by hand without an auto-commit) are
printed as a warning and skipped — a human resolves them by editing
the frontmatter directly.

Usage:
    python scripts/backfill_terminal_closed_at.py            # dry-run
    python scripts/backfill_terminal_closed_at.py --apply    # write
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Import without installing — the engine ships in goc/ at the repo root.
sys.path.insert(0, str(ROOT))
from goc.engine import DECK_DIR, load_all_cards, mutate_frontmatter_field  # noqa: E402

TERMINAL_NON_DONE = frozenset({"disproved", "superseded"})


def latest_readme_commit_iso(readme: Path) -> str | None:
    """Return UTC ISO author-date of the latest commit touching `readme`, or None.

    Normalized to the `YYYY-MM-DDTHH:MM:SSZ` shape that goc's validator
    accepts (offset-aware → UTC), matching the shape `_cmd_done` writes.
    """
    rel = readme.relative_to(ROOT)
    try:
        out = subprocess.check_output(
            ["git", "log", "-1", "--format=%aI", "--", str(rel)],
            cwd=ROOT,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return None
    if not out:
        return None
    dt = datetime.fromisoformat(out).astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry-run).")
    args = ap.parse_args()

    cards = load_all_cards()
    targets = [
        c for c in cards
        if c.status in TERMINAL_NON_DONE and c.closed_at is None
    ]
    if not targets:
        print("nothing to backfill — all terminal non-done cards already have closed_at")
        return 0

    skipped: list[str] = []
    fixed: list[tuple[str, str]] = []

    for card in targets:
        readme = DECK_DIR / card.title / "README.md"
        ts = latest_readme_commit_iso(readme)
        if not ts:
            skipped.append(card.title)
            continue
        fixed.append((card.title, ts))
        if args.apply:
            text = readme.read_text()
            text = mutate_frontmatter_field(text, "closed_at", ts)
            readme.write_text(text)

    label = "applied" if args.apply else "would write"
    for title, ts in fixed:
        print(f"{label}: {title}  closed_at: {ts}  (status: {next(c.status for c in targets if c.title == title)})")

    for title in skipped:
        print(f"WARNING: {title}: no git history for README — skip and resolve by hand", file=sys.stderr)

    if not args.apply and fixed:
        print(f"\ndry-run: rerun with --apply to write {len(fixed)} card(s)", file=sys.stderr)

    return 1 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
