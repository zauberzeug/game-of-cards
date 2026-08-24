#!/usr/bin/env python3
"""Measure this deck's autonomous runway against its human-gated backlog.

Two numbers decide whether an autonomously-drained deck keeps working:

  runway  — cards `goc --ready` actually returns, i.e. the engine's
            `card_is_ready`: `status: open` ∧ not a draft scaffold ∧
            `human_gate: none` ∧ no active impediment overlay. This is
            the set `Skill(pull-card)` may claim, so it IS the runway.
  drain   — how often a card that was BORN gated actually gets decided
            and closed, sampled from recent closures via git history

The gate count (`human_gate: none` over open + active cards) is reported
alongside as the runway's **upper bound**, not as the runway: it is the
number the intake argument below is about, and the gap between the two is
how much of the ungated pile is claimed, deferred, or unpublished. Reading
the upper bound as the runway is a fail-open measurement — 15 gate-free
cards that are all impeded, claimed, or drafts would clear the floor with
a real runway of zero. See
`deck/reproduce-py-runway-metric-counts-gates-instead-of-the-engine-ready-predicate/`,
which is the card for that defect in this script.

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

MIN_RUNWAY = 15        # cards `goc --ready` must return to keep the picker fed
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


def goc_json(*args: str) -> list[dict]:
    """Run `goc <args> --json` against ROOT's deck and parse the payload.

    `check=True` on purpose: an invocation that fails prints nothing, and
    parsing nothing as "zero cards" is exactly the fail-open reading this
    script exists to avoid. A broken call must raise, not measure 0.

    Inherited `PYTHONPATH` is kept after ROOT so the child can still import
    `goc` when ROOT is a scratch tree that does not contain the package —
    which is how the falsifying probe in
    `deck/reproduce-py-runway-metric-counts-gates-instead-of-the-engine-ready-predicate/`
    runs this script over a synthetic deck.
    """
    inherited = os.environ.get("PYTHONPATH", "")
    pythonpath = os.pathsep.join(p for p in (str(ROOT), inherited) if p)
    out = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args, "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": pythonpath},
    ).stdout
    return json.loads(out)


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
    cards = goc_json("--status", "all")
    live = [c for c in cards if c["status"] in ("open", "active")]

    gates = Counter(c["human_gate"] for c in live)
    gate_none = gates.get("none", 0)

    # The runway is what the picker can claim, which is `goc --ready` —
    # NOT the gate count. Cross-checked against the `ready` field the
    # all-cards payload already carries (both are `card_is_ready`), so a
    # plumbing failure in either call shows up as a disagreement rather
    # than as a reassuring zero.
    ready = goc_json("--ready")
    runway = len(ready)
    ready_in_payload = sum(1 for c in cards if c["ready"])

    print(f"open + active cards: {len(live)}")
    for g in ("none", "decision", "session"):
        print(f"  human_gate: {g:9s} {gates.get(g, 0):4d}")
    print()
    print(f"gate-none cards (upper bound on the runway):   {gate_none}")
    print(f"autonomous runway (goc --ready, claimable):    {runway}")
    if runway != ready_in_payload:
        print(
            f"  [WARN] `--ready` returned {runway} but the all-cards payload "
            f"marks {ready_in_payload} ready — one of the two calls is broken."
        )

    # Why the upper bound overstates: each excluded axis, counted.
    if gate_none > runway:
        ungated_unready = [c for c in live if c["human_gate"] == "none" and not c["ready"]]
        axes = Counter()
        for c in ungated_unready:
            if c["status"] != "open":
                axes["claimed (status: active)"] += 1
            elif c.get("draft"):
                axes["unpublished draft"] += 1
            elif c.get("waiting_on") or c.get("waiting_until"):
                axes[f"impeded (waiting_on: {c.get('waiting_on') or 'until-date'})"] += 1
            else:
                axes["other"] += 1
        print(f"  {len(ungated_unready)} gate-none cards are not claimable:")
        for axis, n in sorted(axes.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"    {n:4d}  {axis}")

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
        if born_gated:
            drain = (
                f"Ungated cards close {born_none / born_gated:.0f}x more often "
                f"than gated ones get decided, so the backlog grows while the "
                f"runway does not."
            )
        else:
            # No sampled closure was born gated — a rate of "n/0" is not a
            # rate. Say so rather than printing an infinity as a multiplier.
            drain = "No sampled closure was born gated, so no drain rate is measurable."
        print(
            f"\nDEFECT PRESENT: the picker has {runway} claimable cards "
            f"(gate-none upper bound {gate_none}) against {len(gated_live)} "
            f"gated ones. {drain}"
        )
        return 1
    print(
        f"\nPASS: runway of {runway} claimable cards is above the "
        f"{MIN_RUNWAY}-card floor (gate-none upper bound {gate_none})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
