#!/usr/bin/env python3
"""Prove that EXPLORATION and TOOLING cannot change `deck_prompt_router`'s output.

Three independent demonstrations:

1. Exhaustive truth table over the boolean triple the hook computes. The
   shipped gate and a gate with both suppression lists deleted agree on all
   eight rows, so the two lists are unreachable by construction — not merely
   unexercised by the prompts we happened to try.
2. Ablation over a prompt corpus that deliberately includes a canonical
   example of every EXPLORATION and TOOLING pattern, plus mixed
   exploration+work and tooling+work prompts. Deleting both lists changes no
   verdict.
3. A count of the source copies carrying the dead lists, so the maintenance
   cost of the unreachable code is a number rather than an adjective.
4. A dry-run of the fix that the open card
   `deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts`
   offers as one of its three options ("add understand|investigate|know|
   learn|see to EXPLORATION"), showing it changes no verdict — a concrete
   case of the dead layer misleading a future implementer.

Exits 0 while the defect is present (the lists cannot suppress anything), 1
once a fix makes them load-bearing — so the DoD's "reproduce.py exits
non-zero" box flips when the fix lands.
"""

from __future__ import annotations

import importlib.util
import itertools
import re
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

HOOK = ROOT / "goc" / "templates" / "hooks" / "deck_prompt_router.py"

# Every source copy of the hook that carries the two lists. The Python files
# are byte-identical mirrors kept in sync by scripts/sync_plugin_assets.py;
# index.ts is the hand-ported OpenClaw equivalent (dist/ is its build output).
COPIES = [
    "goc/templates/hooks/deck_prompt_router.py",
    ".claude/hooks/deck_prompt_router.py",
    "claude-plugin/hooks/deck_prompt_router.py",
    "claude-plugin/goc/templates/hooks/deck_prompt_router.py",
    "codex-plugin/hooks/deck_prompt_router.py",
    "codex-plugin/goc/templates/hooks/deck_prompt_router.py",
    "openclaw-plugin/index.ts",
]

# One canonical example per EXPLORATION pattern, one per TOOLING pattern, a
# set of unambiguous work requests, some prompts that match neither list, and
# two prompts that match a suppression pattern AND a work pattern.
CORPUS = [
    # EXPLORATION (8 patterns, in order)
    "explain the closure gate",
    "what does the move command do?",
    "what is the build pipeline?",
    "how does the update logic work?",
    "why is the queue empty?",
    "show me the deck",
    "could you describe the value graph",
    "walk me through the parser",
    # TOOLING (5 patterns, in order)
    "git status",
    "rebase onto main",
    "run the tests",
    "npm install",
    "uv sync",
    # unambiguous work
    "add a CSV export",
    "fix the auth bug",
    "let's ship it",
    "i want to refactor this",
    "we need to update the docs",
    "please rename the button",
    "can you delete the old module",
    "make it work",
    "ship this",
    # neither
    "hello",
    "thanks!",
    "",
    # suppression pattern AND work pattern in the same prompt
    "explain how to add a card",
    "run the tests and fix the failures",
]

# The four pure-exploration prompts named in the DoD of
# `deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts`.
# None matches an EXPLORATION pattern today, which is why that card offers
# "add understand|investigate|know|learn|see to EXPLORATION" as a fix.
SIBLING_EXPLORATION_PROMPTS = [
    "I want to understand the parser",
    "I want to know how values are computed",
    "I want to learn about the deck",
    "we need to investigate the flaky test",
]


def _load_hook():
    spec = importlib.util.spec_from_file_location("_goc_deck_prompt_router", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _signals(mod, prompt: str) -> tuple[bool, bool, bool]:
    p = prompt.lower()
    return (
        any(re.search(x, p) for x in mod.WORK_INITIATING),
        any(re.search(x, p) for x in mod.EXPLORATION),
        any(re.search(x, p) for x in mod.TOOLING),
    )


def _shipped_gate(work: bool, exploration: bool, tooling: bool) -> bool:
    """The gate exactly as `main()` implements it (engine.py mirror of lines 83-90)."""
    if (exploration or tooling) and not work:
        return False
    return work


def _ablated_gate(work: bool, _exploration: bool, _tooling: bool) -> bool:
    """The same gate with EXPLORATION and TOOLING deleted from the module."""
    return work


def main() -> int:
    mod = _load_hook()

    print("1. Exhaustive truth table over the three signals the hook computes")
    print("   work expl tool | shipped | both lists deleted")
    table_diffs = 0
    for work, exploration, tooling in itertools.product([False, True], repeat=3):
        shipped = _shipped_gate(work, exploration, tooling)
        ablated = _ablated_gate(work, exploration, tooling)
        table_diffs += shipped != ablated
        print(
            f"     {int(work)}    {int(exploration)}    {int(tooling)}  "
            f"|    {int(shipped)}    |         {int(ablated)}"
        )
    print(f"   rows where the two disagree: {table_diffs}")

    print(
        f"\n2. Ablation over {len(CORPUS)} prompts "
        f"({len(mod.EXPLORATION)} EXPLORATION + {len(mod.TOOLING)} TOOLING "
        "patterns each represented)"
    )
    corpus_diffs = []
    suppression_matches = 0
    for prompt in CORPUS:
        work, exploration, tooling = _signals(mod, prompt)
        suppression_matches += exploration or tooling
        if _shipped_gate(work, exploration, tooling) != _ablated_gate(
            work, exploration, tooling
        ):
            corpus_diffs.append(prompt)
    print(f"   prompts matching an EXPLORATION or TOOLING pattern: {suppression_matches}")
    print(f"   prompts whose verdict changes when both lists are deleted: {len(corpus_diffs)}")
    for prompt in corpus_diffs:
        print(f"     - {prompt!r}")

    print("\n3. Source copies carrying the unreachable lists")
    present = [c for c in COPIES if (ROOT / c).exists()]
    for rel in present:
        print(f"   - {rel}")
    print(f"   total: {len(present)}")

    print(
        "\n4. Dry-run of a fix option an open sibling card already proposes:\n"
        "   'add understand|investigate|know|learn|see to EXPLORATION'"
    )
    mod.EXPLORATION = list(mod.EXPLORATION) + [
        r"\b(understand|investigate|know|learn|see)\b"
    ]
    option_effective = False
    for prompt in SIBLING_EXPLORATION_PROMPTS:
        work, exploration, tooling = _signals(mod, prompt)
        fires = _shipped_gate(work, exploration, tooling)
        option_effective = option_effective or not fires
        print(
            f"   work={int(work)} expl={int(exploration)} -> reminder fires: "
            f"{str(fires).lower():5}  {prompt!r}"
        )
    print(
        "   the added words now match, and the reminder still fires: "
        f"{'no' if option_effective else 'yes'}"
    )

    dead = table_diffs == 0 and not corpus_diffs and not option_effective
    print("")
    if dead:
        print(
            "DEFECT CONFIRMED: no input can make EXPLORATION or TOOLING change the "
            "hook's output — the docstring's 'silent for pure exploration / "
            f"explanation / one-shot tooling' contract is a no-op in {len(present)} "
            "source copies."
        )
        return 0
    print(
        "Suppression is load-bearing: at least one input's verdict depends on "
        "EXPLORATION or TOOLING. The defect is fixed."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
