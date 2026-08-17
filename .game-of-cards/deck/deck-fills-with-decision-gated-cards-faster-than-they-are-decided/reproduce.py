#!/usr/bin/env python3
"""Measure this deck's autonomous runway against its human-gated backlog.

Two numbers decide whether an autonomously-drained deck keeps working:

  runway  — open cards at `human_gate: none`, the only ones the picker
            may claim (`Skill(next-card)` filters to them for loop safety)
  drain   — how often a card that was BORN gated actually gets decided
            and closed, sampled from recent closures via git history

If cards are filed behind a gate faster than gates are cleared, the runway
shrinks toward zero while the deck grows, and the loop starves on a deck
that is mostly work nobody is doing.

Exit 1 while the runway is under MIN_RUNWAY open cards, 0 once the
autonomous queue has real depth again.
"""

import json
import os
import random
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

MIN_RUNWAY = 15        # open gate=none cards the picker needs to stay fed
SAMPLE = 50            # closed cards sampled for the drain measurement
STALE_DAYS = 60        # no log activity for this long = forgotten


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
DECK = ROOT / ".game-of-cards" / "deck"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    ).stdout


def readme_at(commit: str, title: str) -> str:
    for rel in (
        f".game-of-cards/deck/{title}/README.md",
        f"deck/{title}/README.md",
    ):
        r = subprocess.run(
            ["git", "show", f"{commit}:{rel}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            return r.stdout
    return ""


def first_commit(title: str):
    for rel in (
        f".game-of-cards/deck/{title}/README.md",
        f"deck/{title}/README.md",
    ):
        out = git("log", "--format=%H", "--follow", "--", rel).split()
        if out:
            return out[-1]
    return None


def main() -> int:
    raw = subprocess.run(
        [sys.executable, "-m", "goc.cli", "--status", "all", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    ).stdout
    cards = json.loads(raw)
    live = [c for c in cards if c["status"] in ("open", "active")]

    gates = Counter(c["human_gate"] for c in live)
    runway = gates.get("none", 0)

    print(f"open + active cards: {len(live)}")
    for g in ("none", "decision", "session"):
        print(f"  human_gate: {g:9s} {gates.get(g, 0):4d}")
    print(f"\nautonomous runway (gate=none, claimable by the picker): {runway}")

    # --- drain: were recently-closed cards ever gated? ---
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
    closed = [
        c for c in cards
        if c["status"] == "done" and (c.get("closed_at") or "") >= cutoff
    ]
    rng = random.Random(817)
    sample = rng.sample(closed, min(SAMPLE, len(closed)))
    born_gated = born_none = unknown = 0
    for c in sample:
        sha = first_commit(c["title"])
        if not sha:
            unknown += 1
            continue
        body = readme_at(sha, c["title"])
        if "human_gate: decision" in body or "human_gate: session" in body:
            born_gated += 1
        elif "human_gate: none" in body:
            born_none += 1
        else:
            unknown += 1

    print(f"\nsample of {len(sample)} cards closed in the last 90 days:")
    print(f"  born gated, later decided and closed: {born_gated}")
    print(f"  born at gate=none:                    {born_none}")
    if unknown:
        print(f"  indeterminate:                        {unknown}")

    # --- how much of the gated backlog is going stale? ---
    import re

    today = date.today()
    stale = 0
    gated_live = [c for c in live if c["human_gate"] != "none"]
    for c in gated_live:
        log = DECK / c["title"] / "log.md"
        dates = []
        if log.exists():
            dates = re.findall(
                r"^##\s+(\d{4}-\d{2}-\d{2})",
                log.read_text(encoding="utf-8"),
                re.M,
            )
        ref = max(dates) if dates else (c.get("created") or "")[:10]
        try:
            if (today - date.fromisoformat(ref)).days >= STALE_DAYS:
                stale += 1
        except ValueError:
            pass
    print(
        f"\ngated open cards with no log activity for {STALE_DAYS}+ days: "
        f"{stale}/{len(gated_live)}"
    )

    if runway < MIN_RUNWAY:
        ratio = (born_none / born_gated) if born_gated else float("inf")
        print(
            f"\nDEFECT PRESENT: the picker has {runway} claimable cards against "
            f"{len(gated_live)} gated ones. Ungated cards close "
            f"{ratio:.0f}x more often than gated ones get decided, so the "
            f"backlog grows while the runway does not."
        )
        return 1
    print(f"\nPASS: runway of {runway} cards is above the {MIN_RUNWAY}-card floor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
