"""Reproduce: `goc validate`'s CASCADE_CHAIN_ROOT warning counts only cards
stored as `status: blocked`, a value the three-axis model retired, so it
never fires on a deck encoded the way the methodology now prescribes.

`validate_blocker_coherence` (`goc/engine.py`) walks downstream from every
gated card through `advanced_by` edges, but only through descendants whose
stored status is `blocked`. Since 2026-05-26 a card that waits on a
prerequisite stays `open` (card-schema reference.md § Three-axis model:
"Nothing is ever steady-state `blocked`"), and this repo's own deck holds
no `blocked` card at all.

Four throwaway decks, each run through the real `goc validate` in a
subprocess. They share one shape: a gated root card and a chain of cards
below it, linked root -> c1 -> c2 -> c3 with both edge halves written.
Each downstream card lists its parent in `advanced_by`, so the
`advanced-by-closed` check keeps it from closing until the parent closes.

  A. legacy encoding: the three downstream cards are `status: blocked`.
     This is the control. If A does not warn, the harness cannot observe
     the warning at all and the other verdicts prove nothing.
  B. current encoding: the same chain, with the downstream cards
     `status: open`. A has the same graph and gate, so B should warn too.
  C. current encoding, only two downstream cards: below the threshold
     of 3, so no warning. Guards against a fix that warns on every chain.
  D. current encoding, with the root at `human_gate: none`. There is no
     human cord to pull, so no warning. Guards against a fix that drops
     the gate condition.

Exit codes: 0 = defect no longer fires (B warns; A warns; C and D stay
silent), 1 = defect fires (B is silent, or a fix over-fires on C or D),
2 = harness or precondition broken (A silent, a validate crash, or a
fixture the validator rejects).

Run via `uv run python .game-of-cards/deck/cascade-root-warning-counts-only-cards-in-the-retired-blocked-status/reproduce.py`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path | None:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir() and (p / "goc" / "_launch.py").is_file():
            return p
        p = p.parent
    return None


WARNING = "WARN CASCADE_CHAIN_ROOT"

CONFIG = """\
layer_2_project_dod: []
layer_3_goc_dod:
  - name: advanced-by-closed
    kind: derived
workflow:
  auto_commit: false
"""


def _card(title: str, *, status: str, gate: str, advances: list[str], advanced_by: list[str]) -> str:
    def block(items: list[str]) -> str:
        return "[]" if not items else "\n" + "\n".join(f"  - {i}" for i in items)

    return (
        "---\n"
        f"title: {title}\n"
        f'summary: "Fixture card {title} for the cascade-root reproducer."\n'
        f"status: {status}\n"
        "stage: null\n"
        "contribution: medium\n"
        'created: "2026-01-01T00:00:00Z"\n'
        "closed_at: null\n"
        f"human_gate: {gate}\n"
        f"advances: {block(advances)}\n"
        f"advanced_by: {block(advanced_by)}\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [ ] TDD: fixture item\n"
        "---\n"
        "\n"
        f"# {title}\n"
        "\n"
        "Fixture.\n"
    )


def _chain_deck(root_gate: str, downstream_status: str, depth: int) -> dict[str, str]:
    """root -> c1 -> ... -> c<depth>, every edge written on both halves."""
    titles = ["cascade-root"] + [f"chain-card-{i}" for i in range(1, depth + 1)]
    cards = {}
    for i, title in enumerate(titles):
        cards[title] = _card(
            title,
            status="open" if i == 0 else downstream_status,
            gate=root_gate if i == 0 else "decision",
            advances=[titles[i + 1]] if i + 1 < len(titles) else [],
            advanced_by=[titles[i - 1]] if i > 0 else [],
        )
    return cards


CASES = (
    # (key, label, deck, expect_warning)
    ("A", "legacy: 3 downstream cards stored as `blocked` (control)", _chain_deck("decision", "blocked", 3), True),
    ("B", "current: the same chain, downstream cards `open`", _chain_deck("decision", "open", 3), True),
    ("C", "current: only 2 downstream cards (below threshold 3)", _chain_deck("decision", "open", 2), False),
    ("D", "current: 3 downstream cards, root at human_gate none", _chain_deck("none", "open", 3), False),
)


def _run_validate(launcher: Path, cards: dict[str, str]) -> subprocess.CompletedProcess:
    workdir = Path(tempfile.mkdtemp(prefix="goc-cascade-root-"))
    try:
        (workdir / ".game-of-cards").mkdir()
        (workdir / ".game-of-cards" / "config.yaml").write_text(CONFIG)
        deck = workdir / ".game-of-cards" / "deck"
        deck.mkdir()
        for title, text in cards.items():
            (deck / title).mkdir()
            (deck / title / "README.md").write_text(text)
            (deck / title / "log.md").write_text("")
        env = os.environ.copy()
        env.pop("GOC_WORKTREE_DECK", None)
        env.pop("GOC_WORKER", None)
        return subprocess.run(
            [sys.executable, str(launcher), "validate"],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> int:
    repo_root = _repo_root()
    if repo_root is None:
        print("HARNESS BROKEN: no ancestor directory holds .game-of-cards/ + goc/_launch.py")
        return 2
    launcher = repo_root / "goc" / "_launch.py"
    if not launcher.is_file():
        print(f"HARNESS BROKEN: launcher not found at {launcher}")
        return 2

    print("Each deck: gated root -> chain of downstream cards (advanced_by edges, both halves written).")
    print(f"Detector under test: `goc validate` stderr line starting {WARNING!r}.")
    print()

    verdicts: dict[str, bool] = {}
    for key, label, cards, expect in CASES:
        try:
            result = _run_validate(launcher, cards)
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"HARNESS BROKEN: validate could not run for case {key}: {exc}")
            return 2
        warn_lines = [ln for ln in result.stderr.splitlines() if ln.startswith(WARNING)]
        fired = bool(warn_lines)
        verdicts[key] = fired
        mark = "ok" if fired == expect else ("DEFECT" if key == "B" else "UNEXPECTED")
        print(f"[{key}] {label}")
        print(f"    validate exit {result.returncode}; CASCADE_CHAIN_ROOT fired: {fired} (expected {expect})  [{mark}]")
        for ln in warn_lines:
            print(f"    {ln}")
        if result.returncode != 0:
            print("    --- validate stderr (non-zero exit) ---")
            print("    " + result.stderr.strip().replace("\n", "\n    "))
            print(f"HARNESS BROKEN: fixture deck {key} fails `goc validate`; its warnings prove nothing.")
            return 2
    print()

    if not verdicts["A"]:
        print(
            "PRECONDITION BROKEN: the legacy-encoded control (A) raised no CASCADE_CHAIN_ROOT, "
            "so the harness cannot observe the warning. If the warning class was deliberately "
            "retired, rewrite this reproducer's success condition to match that decision."
        )
        return 2
    over_fired = [k for k in ("C", "D") if verdicts[k]]
    if not verdicts["B"]:
        print(
            "DEFECT: the same gated chain warns when its downstream cards are stored as the retired "
            "`blocked` status (A) and stays silent when they are `open`, the encoding the three-axis "
            "model prescribes (B). On a migrated deck the warning can never fire."
        )
        return 1
    if over_fired:
        print(
            f"DEFECT (fix over-fires): CASCADE_CHAIN_ROOT fired on negative control(s) {over_fired} "
            "— a below-threshold chain or an ungated root is not a cascade root."
        )
        return 1
    print("FIXED: the warning fires for the gated chain whichever status encoding its downstream cards use, "
          "and stays silent on the below-threshold and ungated controls.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
