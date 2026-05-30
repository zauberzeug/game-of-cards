"""Reproduce: the BACKWARDS_EPIC_EDGE warning's suggested fix is a no-op.

Builds a minimal backwards-aggregation-epic deck in a fresh temp repo,
runs the two commands the warning literally tells the user to run, and
shows the on-disk edge state before / after. The bad edge is unchanged.
Then runs the corrected sequence and shows the edge is fixed.

Exit zero iff the swapped sequence leaves state unchanged AND the
corrected sequence removes the backwards edge.
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


REPO = _repo_root()
sys.path.insert(0, str(REPO))

from goc import engine  # noqa: E402


def run(cmd: list[str], cwd: Path) -> str:
    out = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, check=False
    )
    return (out.stdout + out.stderr).strip()


def edges(deck_dir: Path, title: str) -> tuple[list[str], list[str]]:
    card = engine.load_card(deck_dir / title)
    fm = card.frontmatter
    return (
        list(fm.get("advances") or []),
        list(fm.get("advanced_by") or []),
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "scratch"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
        # Use the in-tree goc engine — `uv run --project <REPO>` resolves it.
        env_uv = ["uv", "run", "--project", str(REPO), "goc"]

        # Scaffold the deck and four cards.
        subprocess.run(env_uv + ["install"], cwd=str(repo),
                       capture_output=True, check=True)
        for slug, contrib in [
            ("card-a", "high"),
            ("child-x", "low"),
            ("child-y", "low"),
            ("child-z", "low"),
        ]:
            subprocess.run(
                env_uv + ["new", slug, "--contribution", contrib, "--allow-jargon"],
                cwd=str(repo), capture_output=True, check=True,
            )
        # Lower the default decision gate on every card so the warning's
        # `else` branch (which is the swapped one) fires, not the
        # `human_gate == decision` branch.
        for slug in ("card-a", "child-x", "child-y", "child-z"):
            subprocess.run(
                env_uv + ["decide", slug,
                          "--decision", "go", "--because", "needed"],
                cwd=str(repo), capture_output=True, check=True,
            )
        # Build the backwards-epic shape: card-a.advances -> children.
        for child in ("child-x", "child-y", "child-z"):
            subprocess.run(
                env_uv + ["advance", child, "--by", "card-a", "--no-commit"],
                cwd=str(repo), capture_output=True, check=True,
            )

        deck = repo / ".game-of-cards" / "deck"

        def snapshot(label: str) -> None:
            adv_a, ab_a = edges(deck, "card-a")
            adv_x, ab_x = edges(deck, "child-x")
            print(f"=== {label} ===")
            print(f"card-a.advances     = {adv_a}")
            print(f"card-a.advanced_by  = {ab_a}")
            print(f"child-x.advances    = {adv_x}")
            print(f"child-x.advanced_by = {ab_x}")
            print()

        snapshot("initial state")

        # Read the warning text the user actually sees.
        warn = subprocess.run(
            env_uv + ["validate"], cwd=str(repo),
            capture_output=True, text=True, check=False,
        )
        for line in warn.stdout.splitlines():
            if "BACKWARDS_EPIC_EDGE" in line and "card-a" in line:
                print("=== goc validate (warning, abridged) ===")
                print(line[:200] + ("..." if len(line) > 200 else ""))
                print()
                break

        # The verbatim suggested sequence.
        print("=== running the suggested commands verbatim ===")
        print("$ goc unadvance card-a --by child-x")
        print(run(env_uv + ["unadvance", "card-a", "--by", "child-x",
                            "--no-commit"], repo))
        print("$ goc advance child-x --by card-a")
        print(run(env_uv + ["advance", "child-x", "--by", "card-a",
                            "--no-commit"], repo))
        print()
        snapshot("state after suggested commands (verbatim)")

        adv_a_after_swapped, _ = edges(deck, "card-a")
        swapped_left_edge = "child-x" in adv_a_after_swapped

        # The corrected sequence.
        print("=== running the CORRECTED commands ===")
        print("$ goc unadvance child-x --by card-a")
        print(run(env_uv + ["unadvance", "child-x", "--by", "card-a",
                            "--no-commit"], repo))
        print("$ goc advance card-a --by child-x")
        print(run(env_uv + ["advance", "card-a", "--by", "child-x",
                            "--no-commit"], repo))
        print()
        snapshot("state after CORRECTED commands")

        adv_a_final, ab_a_final = edges(deck, "card-a")
        corrected_removed_edge = "child-x" not in adv_a_final
        corrected_added_inverse = "child-x" in ab_a_final

        # Verdict.
        print("=== verdict ===")
        print(f"swapped sequence left card-a.advances:[child-x] in place: "
              f"{swapped_left_edge}")
        print(f"corrected sequence removed the bad edge:                  "
              f"{corrected_removed_edge}")
        print(f"corrected sequence added the inverse edge:                "
              f"{corrected_added_inverse}")

        ok = (
            swapped_left_edge
            and corrected_removed_edge
            and corrected_added_inverse
        )
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
