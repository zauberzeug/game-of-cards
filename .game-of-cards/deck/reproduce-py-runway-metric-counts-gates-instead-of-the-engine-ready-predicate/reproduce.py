#!/usr/bin/env python3
"""Reproduce: a card's runway metric counts gates where the engine counts pullability.

`deck-fills-with-decision-gated-cards-faster-than-they-are-decided/reproduce.py`
gates its exit code on the deck's "autonomous runway". It used to compute that
number as

    gates = Counter(c["human_gate"] for c in live)   # live = open + active
    runway = gates.get("none", 0)

a one-axis gate count. The engine's `card_is_ready` — the predicate
`goc --ready` and therefore `Skill(pull-card)` actually select with — gates on
four axes: `status == "open"` (so a claimed card is out), not a draft scaffold,
`human_gate == "none"`, and no active impediment overlay. Three of the four are
missing from the gate count, so it is an *upper bound* on the runway, and the
bound is loosest exactly where the number decides something: a deck whose only
ungated cards are impeded, claimed, or unpublished reports a comfortable runway
while the picker can claim nothing.

This probe runs the real script — a verbatim copy, so whatever is committed is
what gets measured — against two synthetic decks:

  Scenario A (fail-open):  16 `human_gate: none` cards, every one of them
                           impeded, claimed, or an unpublished draft.
                           Gate count 16, true runway 0. The old metric
                           reported 16 and cleared its own MIN_RUNWAY=15
                           floor with a real runway of zero.
  Scenario B (control):    the same deck plus 3 genuinely pullable cards.
                           Gate count 19, true runway 3. This is here so a
                           runway that reads 0 because the plumbing broke
                           cannot pass as a runway that reads 0 because the
                           predicate is right.

Exit code:
  0 — the script derives its runway from the engine and still reports the
      gate count as a separate upper-bound line
  1 — the script's runway is a gate count (defect present), or it stopped
      reporting the upper bound, or the control scenario disagrees

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
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
TARGET = (
    ROOT
    / ".game-of-cards"
    / "deck"
    / "deck-fills-with-decision-gated-cards-faster-than-they-are-decided"
    / "reproduce.py"
)

FRONTMATTER = """\
---
title: {title}
summary: "Scratch card for the runway-metric reproducer."
status: {status}
stage: null
contribution: {contribution}
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: {human_gate}
advances: []
advanced_by: []
tags: []
{extra}definition_of_done: |
  - [ ] MECHANICAL: scratch card, never closed
---

# {title}

## Summary

Scratch card for the runway-metric reproducer.
"""

# Every card here is `human_gate: none`, and every one of them fails a
# DIFFERENT `card_is_ready` conjunct than the gate. 16 of them, one over the
# script's MIN_RUNWAY floor of 15 — that is the whole point: the gate count
# clears the floor, the engine reports nothing claimable.
UNPULLABLE = (
    [
        (f"impeded-on-a-vendor-{i}", {"status": "open", "waiting_on": "external"})
        for i in range(1, 4)
    ]
    + [
        (f"deferred-until-the-far-future-{i}", {"status": "open", "waiting_until": "2999-01-01"})
        for i in range(1, 4)
    ]
    + [
        (f"already-claimed-by-another-session-{i}", {"status": "active"})
        for i in range(1, 6)
    ]
    + [
        (f"unpublished-draft-scaffold-{i}", {"status": "open", "draft": "true"})
        for i in range(1, 6)
    ]
)

# Realism only — the gated pile the parent card is about. Neither predicate
# counts these, so they must not move either number.
GATED = [
    ("parked-on-a-decision", {"status": "open", "human_gate": "decision"}),
    ("parked-on-a-session", {"status": "open", "human_gate": "session"}),
]

# The control: plain open, ungated, unimpeded, authored.
PULLABLE = [(f"genuinely-ready-{i}", {"status": "open"}) for i in range(1, 4)]

OVERLAY_KEYS = ("waiting_on", "waiting_until", "draft")


def _write_card(deck: Path, title: str, fields: dict) -> None:
    extra = "".join(f"{k}: {fields[k]}\n" for k in OVERLAY_KEYS if k in fields)
    card = deck / title
    card.mkdir(parents=True)
    (card / "README.md").write_text(
        FRONTMATTER.format(
            title=title,
            status=fields.get("status", "open"),
            contribution=fields.get("contribution", "medium"),
            human_gate=fields.get("human_gate", "none"),
            extra=extra,
        ),
        encoding="utf-8",
    )
    (card / "log.md").write_text("", encoding="utf-8")


def _build_repo(base: Path, cards: list[tuple[str, dict]]) -> Path:
    """A scratch repo the copied script will resolve as its own ROOT.

    The copy lands in `probe/`, not in a deck card directory, so `_repo_root()`
    walks up to this `pyproject.toml` and every path the script derives —
    `.game-of-cards/deck`, the `goc.cli` subprocess cwd — points at the
    synthetic deck instead of this repo's.
    """
    base.mkdir(parents=True, exist_ok=True)
    (base / "pyproject.toml").write_text("[project]\nname = 'scratch'\n", encoding="utf-8")
    (base / ".game-of-cards").mkdir()
    (base / ".game-of-cards" / "config.yaml").write_text(
        "workflow:\n  auto_commit: false\n", encoding="utf-8"
    )
    deck = base / ".game-of-cards" / "deck"
    deck.mkdir()
    for title, fields in cards:
        _write_card(deck, title, fields)
    probe_dir = base / "probe"
    probe_dir.mkdir()
    copied = probe_dir / "reproduce.py"
    shutil.copyfile(TARGET, copied)
    return copied


def _child_env() -> dict[str, str]:
    """Keep this repo importable: the copy runs with a scratch ROOT."""
    env = dict(os.environ)
    env.pop("GOC_WORKER", None)
    inherited = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(ROOT), inherited) if p)
    return env


def _goc_json(repo: Path, *args: str) -> list[dict]:
    out = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args, "--json"],
        cwd=repo,
        env=_child_env(),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(out)


RUNWAY_RE = re.compile(r"^autonomous runway[^:]*:\s*(\d+)\s*$", re.M)
GATE_BREAKDOWN_RE = re.compile(r"^\s*human_gate:\s*none\s+(\d+)\s*$", re.M)
UPPER_BOUND_RE = re.compile(r"^gate-none cards \(upper bound[^:]*:\s*(\d+)\s*$", re.M)


def _run_target(copied: Path) -> tuple[str, int]:
    proc = subprocess.run(
        [sys.executable, str(copied)],
        cwd=copied.parent,
        env=_child_env(),
        capture_output=True,
        text=True,
    )
    return proc.stdout + proc.stderr, proc.returncode


def _scenario(base: Path, name: str, cards: list[tuple[str, dict]]) -> dict:
    copied = _build_repo(base, cards)
    repo = copied.parent.parent

    # The two predicates, measured independently of the script under test.
    live = [c for c in _goc_json(repo, "--status", "all") if c["status"] in ("open", "active")]
    legacy = sum(1 for c in live if c["human_gate"] == "none")   # the old metric
    engine = len(_goc_json(repo, "--ready"))                     # card_is_ready

    out, code = _run_target(copied)
    m_runway = RUNWAY_RE.search(out)
    m_gate = GATE_BREAKDOWN_RE.search(out)
    m_bound = UPPER_BOUND_RE.search(out)

    print(f"=== Scenario {name}: {len(cards)} scratch cards ===")
    print(f"  legacy metric (gate count over open+active): {legacy}")
    print(f"  engine predicate (goc --ready / card_is_ready): {engine}")
    print(f"  script's reported runway: "
          f"{m_runway.group(1) if m_runway else '(no runway line found)'}")
    print(f"  script's reported gate-none upper bound: "
          f"{m_bound.group(1) if m_bound else '(no upper-bound line found)'}")
    print(f"  script exit code: {code}")
    print()
    return {
        "legacy": legacy,
        "engine": engine,
        "runway": int(m_runway.group(1)) if m_runway else None,
        "gate_breakdown": int(m_gate.group(1)) if m_gate else None,
        "upper_bound": int(m_bound.group(1)) if m_bound else None,
        "output": out,
    }


def main() -> int:
    if not TARGET.exists():
        print(f"[FAIL] target script not found: {TARGET}")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        a = _scenario(tmp / "a", "A (fail-open)", UNPULLABLE + GATED)
        b = _scenario(tmp / "b", "B (control)", UNPULLABLE + GATED + PULLABLE)

    failures: list[str] = []

    # Scenario A is the falsifying case: the legacy metric must clear the
    # script's own 15-card floor while the engine reports nothing claimable.
    # If the fixture stops exhibiting that, the probe proves nothing.
    if a["legacy"] < 15:
        failures.append(
            f"fixture broken: scenario A gate count is {a['legacy']}, "
            "needs 15+ to clear MIN_RUNWAY"
        )
    if a["engine"] != 0:
        failures.append(
            f"fixture broken: scenario A should have 0 pullable cards, "
            f"engine says {a['engine']}"
        )

    if a["runway"] is None:
        failures.append("scenario A: no `autonomous runway ...: N` line in the output")
    elif a["runway"] != a["engine"]:
        failures.append(
            f"scenario A: script reports runway {a['runway']} where the engine "
            f"reports {a['engine']} — the runway is still a gate count"
        )

    # The gate count is the upper bound and the parent card's intake argument
    # uses it, so the fix must ADD a number rather than replace one.
    if a["gate_breakdown"] != a["legacy"]:
        failures.append(
            f"scenario A: gate breakdown line reports {a['gate_breakdown']}, "
            f"expected {a['legacy']} — the upper bound stopped being reported"
        )
    if a["upper_bound"] != a["legacy"]:
        failures.append(
            f"scenario A: no explicit `gate-none cards (upper bound ...)` line "
            f"reporting {a['legacy']}"
        )

    # The control: a runway pinned at 0 by broken plumbing would pass
    # scenario A. It must track the engine when there IS work.
    if b["engine"] != len(PULLABLE):
        failures.append(
            f"fixture broken: scenario B should have {len(PULLABLE)} pullable "
            f"cards, engine says {b['engine']}"
        )
    if b["runway"] != b["engine"]:
        failures.append(
            f"scenario B: script reports runway {b['runway']} where the engine "
            f"reports {b['engine']}"
        )
    if b["upper_bound"] != b["legacy"]:
        failures.append(
            f"scenario B: upper bound reports {b['upper_bound']}, expected {b['legacy']}"
        )

    if failures:
        print("[FAIL] the runway metric does not agree with the engine:")
        for f in failures:
            print(f"  - {f}")
        print()
        print("--- scenario A output, verbatim ---")
        print(a["output"].rstrip())
        return 1

    print(
        f"[OK] runway tracks `card_is_ready` ({a['runway']} on the fail-open "
        f"deck, {b['runway']} on the control) and the gate count is still "
        f"reported as the upper bound ({a['upper_bound']} / {b['upper_bound']})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
