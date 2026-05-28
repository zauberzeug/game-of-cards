#!/usr/bin/env python3
"""Proof for standup-underreports-closures-and-ignores-unpulled-remote-commits.

The standup skill's "Closed since yesterday" scan derived closure recency from
filesystem mtime (`find ... -newer .game-of-cards/deck -mmin -1440`). That is
git-blind: a pull/merge/clone writes the deck directory and every log.md at one
instant, giving them identical mtimes, so the strict `-newer` test matches
nothing and standup reports "Nothing closed" even when dozens of cards closed.
It also never checked whether the local tree was behind its remote.

This script gates on the *source-of-truth template* having been fixed:
  1. Section 3 no longer uses the find/-newer/-mmin mtime heuristic.
  2. Section 3 lists closures via the engine's structured `closed_at` field.
  3. A sync-state preflight runs `git fetch` and warns when behind upstream.

It exits non-zero on the pre-fix template and zero once all three hold. The
deterministic fixture below proves *why* mtime fails, independent of this
repo's live history; the live-repo numbers are printed as supplementary
evidence but do not gate the exit (they depend on recent closures existing).
"""
import datetime
import os
import subprocess
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
TEMPLATE = ROOT / "goc" / "templates" / "skills" / "standup" / "SKILL.md"


def demonstrate_mtime_blindness() -> bool:
    """Deterministic proof: when a card's log.md and the deck dir share an
    mtime (the post-sync condition), `find -newer` misses the closure."""
    with tempfile.TemporaryDirectory() as tmp:
        deck = Path(tmp) / "deck"
        card = deck / "some-card-that-closed"
        card.mkdir(parents=True)
        log = card / "log.md"
        log.write_text("done: 2026-05-27 — fixed the thing\n")
        # Simulate a git sync: deck dir and log.md written at one instant.
        synced = datetime.datetime.now().timestamp()
        os.utime(log, (synced, synced))
        os.utime(deck, (synced, synced))
        found = subprocess.run(
            ["find", str(deck), "-name", "log.md", "-newer", str(deck), "-mmin", "-1440"],
            capture_output=True, text=True,
        ).stdout.strip()
        hits = [ln for ln in found.splitlines() if ln]
        print(f"  fixture: log.md carries a fresh closure, mtime == deck dir mtime")
        print(f"  old `find -newer` scan matched: {len(hits)} file(s)  "
              f"-> standup would print 'Nothing closed'")
        return len(hits) == 0  # bug confirmed: the closure is invisible to find


def live_closed_at_count() -> None:
    """Supplementary: what the structured closed_at record reports right now."""
    try:
        out = subprocess.run(
            ["uv", "run", "goc", "--json", "--status", "all"],
            capture_output=True, text=True, cwd=ROOT, timeout=120,
        ).stdout
        import json
        cards = json.loads(out)
    except Exception as e:  # noqa: BLE001 - supplementary only
        print(f"  (live closed_at probe skipped: {e})")
        return
    now = datetime.datetime.now(datetime.timezone.utc)

    def parse(s):
        if not s:
            return None
        try:
            d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            try:
                d = datetime.datetime.strptime(s[:10], "%Y-%m-%d")
            except Exception:
                return None
        return d.replace(tzinfo=datetime.timezone.utc) if d.tzinfo is None else d

    recent = [c for c in cards
              if (d := parse(c.get("closed_at"))) and 0 <= (now - d).total_seconds() <= 86400]
    print(f"  engine closed_at within last 24h: {len(recent)} card(s)")


def main() -> int:
    print("== Deterministic proof: mtime is git-blind ==")
    bug_demonstrated = demonstrate_mtime_blindness()
    print("== Supplementary: live deck state ==")
    live_closed_at_count()

    text = TEMPLATE.read_text() if TEMPLATE.exists() else ""
    uses_mtime = ('-newer .game-of-cards/deck' in text) or ('-mmin -1440' in text)
    uses_closed_at = 'closed_at' in text
    has_sync_check = ('git fetch' in text) and ('HEAD..@{u}' in text or 'rev-list' in text)

    print("== Template assertions (gate the exit) ==")
    print(f"  Section 3 still uses find/mtime heuristic: {uses_mtime}   (want False)")
    print(f"  closure scan uses structured closed_at:    {uses_closed_at}   (want True)")
    print(f"  sync-state preflight present:              {has_sync_check}   (want True)")

    fixed = (not uses_mtime) and uses_closed_at and has_sync_check
    if fixed:
        print("\nPASS: standup closure scan is git-independent and a sync check is in place.")
        return 0
    print("\nFAIL: standup still under-reports closures / lacks a sync-state check.")
    # Sanity: the deterministic fixture must always show the old find's blindness.
    assert bug_demonstrated, "fixture failed to reproduce the -newer blindness"
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
