#!/usr/bin/env python3
"""Reproduce: a card title that plainly breaks AGENTS.md's English-only rule.

The title used here is the real one this repo carried from 2026-07-18 until a
refine-deck pass renamed it by hand on 2026-07-27. It is a well-formed slug —
lower-kebab, ASCII, no jargon tokens — so every guard in the filing path
accepted it for nine days.

This script probes two predicates, because the fix deliberately changed only
one of them:

  * `engine._check_title_antipatterns` — the goc-shipped filing-path guard. It
    still accepts the title, and that is the intended end state: English-only
    is *this repo's* authoring convention, not goc semantics, and a team
    running goc on a German codebase is entitled to a German deck.
  * `scripts/check_card_language.py` — the repo-local guard added by this card.
    It flags the title, and the regression suite
    (`tests/test_card_authoring_rules.py`) runs it over the whole deck in CI on
    every push.

Each probe carries a control that the predicate is known to catch, so a dead
scanner cannot masquerade as a passing one.

Run from the repo root:

    uv run python .game-of-cards/deck/card-authoring-rules-in-agents-md-have-no-enforcement-path/reproduce.py

Exits 1 while no guard rejects the title, 0 once one does.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402

# The title as it was actually filed. German: "OpenClaw plugin skills force
# multiple reads per session."
OFFENDER = "openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session"

# Controls the two predicates are each known to catch, proving the scanner is
# alive — without them, an empty offender list would be indistinguishable from
# a dead check.
JARGON_CONTROL = "r88-runSimulation-fails"
LANGUAGE_CONTROL = "konfiguration-wird-nicht-geladen"


def _load_language_guard():
    spec = importlib.util.spec_from_file_location(
        "_goc_card_language_guard", ROOT / "scripts" / "check_card_language.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    guard = _load_language_guard()

    engine_hits = engine._check_title_antipatterns(OFFENDER)
    engine_control = engine._check_title_antipatterns(JARGON_CONTROL)
    language_hits = guard.flag_text(OFFENDER)
    language_control = guard.flag_text(LANGUAGE_CONTROL)

    print("goc-shipped filing-path guard (engine._check_title_antipatterns)")
    print(f"  rules defined:                 {len(engine.TITLE_ANTIPATTERNS)}")
    print(f"  control {JARGON_CONTROL!r} -> {len(engine_control)} hit(s)")
    print(f"  offender -> {len(engine_hits)} hit(s): {engine_hits}")
    print("repo-local English-only guard (scripts/check_card_language.py)")
    print(f"  marker words:                  {len(guard.MARKER_WORDS)}")
    print(f"  control {LANGUAGE_CONTROL!r} -> {len(language_control)} hit(s)")
    print(f"  offender -> {len(language_hits)} hit(s): {language_hits}")

    if not engine_control or not language_control:
        print(
            "\nINCONCLUSIVE — a control title was not flagged, so that scanner is "
            "broken and this run proves nothing about the English-only gap. Fix "
            "the control first."
        )
        return 1

    if language_hits:
        print(
            "\nOK — the repo-local guard flags the non-English title, and "
            "`tests/test_card_authoring_rules.py` runs it over every card in CI. "
            "The engine predicate still accepts it by design: goc does not ship "
            "an English-only policy to consumers."
        )
        return 0

    print(
        "\nFAIL — both scanners are alive (each flags its control) and neither "
        "rejects a title that breaks AGENTS.md's English-only rule."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
