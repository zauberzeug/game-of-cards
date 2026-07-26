"""Prove the `retrospective` skill's closure queries hide non-`done` closures.

Builds a throwaway deck with one closure of each terminal status
(`done`, `disproved`, `superseded`), then runs the exact query the
skill's Context block / Step 1 / Step 5 use (`goc --status done --json`)
against it and compares the population to the engine's own terminal set.

Exits non-zero while the defect fires.
"""

from __future__ import annotations

import json
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

from goc.engine import TERMINAL_STATUSES  # noqa: E402

SKILL = ROOT / "goc" / "templates" / "skills" / "retrospective" / "SKILL.md"

# The three sites in the skill body that gather closure history.
QUERY_SITES = ("Context block", "Step 1 — Gather recent closures", "Step 5 — Velocity feel")


def _goc(cwd: Path, *args: str) -> str:
    env = dict(os.environ, PYTHONPATH=str(ROOT), GOC_WORKER="")
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, capture_output=True, text=True,
    )
    return proc.stdout


def _author(card_dir: Path) -> None:
    """Clear the draft flag and satisfy the DoD so the card can close."""
    readme = card_dir / "README.md"
    text = readme.read_text()
    text = text.replace("draft: true\n", "")
    text = text.replace("human_gate: decision", "human_gate: none")
    text = text.replace(
        "- [ ] (replace with real criteria)", "- [x] scaffolded for the probe [manual]"
    )
    text = text.replace(
        "title: ", "summary: probe card for the retrospective scope check\ntitle: ", 1
    )
    readme.write_text(text)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "probe@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "probe"], cwd=repo, check=True)
        (repo / ".game-of-cards").mkdir()
        (repo / ".game-of-cards" / "deck").mkdir()
        (repo / ".game-of-cards" / "config.yaml").write_text(
            "auto_commit: false\nclaim_push: false\n"
        )

        plan = {
            "probe-done-card": "done",
            "probe-disproved-card": "disproved",
            "probe-superseded-card": "superseded",
        }
        for title in plan:
            _goc(repo, "new", title, "--contribution", "medium", "--tag", "bug")
            _author(repo / ".game-of-cards" / "deck" / title)
        # `superseded` needs a live successor to point at.
        _goc(repo, "new", "probe-successor-card", "--contribution", "medium", "--tag", "bug")
        _author(repo / ".game-of-cards" / "deck" / "probe-successor-card")

        _goc(repo, "done", "probe-done-card")
        _goc(repo, "status", "probe-disproved-card", "disproved")
        _goc(
            repo, "status", "probe-superseded-card", "superseded",
            "--by", "probe-successor-card",
        )

        skill_query = json.loads(_goc(repo, "--status", "done", "--json"))
        every_card = json.loads(_goc(repo, "--status", "all", "--json"))
        truly_closed = [c for c in every_card if c["status"] in TERMINAL_STATUSES]

        print("engine TERMINAL_STATUSES        :", ", ".join(sorted(TERMINAL_STATUSES)))
        print("closures written to the deck    :", len(truly_closed))
        for c in sorted(truly_closed, key=lambda c: c["title"]):
            print(f"    {c['status']:<11} {c['title']}  closed_at={c['closed_at']}")
        print()
        print("`goc --status done --json` yields:", len(skill_query))
        for c in sorted(skill_query, key=lambda c: c["title"]):
            print(f"    {c['status']:<11} {c['title']}")

        hidden = sorted(
            c["title"] for c in truly_closed
            if c["title"] not in {q["title"] for q in skill_query}
        )
        print()
        print("closures the retrospective cannot see:", len(hidden))
        for title in hidden:
            print(f"    {title}")

        body = SKILL.read_text()
        n_sites = body.count("--status done --json")
        print()
        print(f"`--status done --json` occurrences in {SKILL.relative_to(ROOT)}: {n_sites}")
        print(f"   across {len(QUERY_SITES)} query sites:", "; ".join(QUERY_SITES))
        print("   (the Context block carries the bootstrap + bare-goc fallback pair)")
        print(
            "   contradicted instruction (SKILL.md Step 3): "
            '"Cards closed with `disproved` or `superseded` — what was wrong?"'
        )

        if hidden or n_sites:
            print()
            print(
                "[FAIL] the skill's closure queries scope to `done`, so "
                f"{len(hidden)} of {len(truly_closed)} closures are invisible "
                "to the retrospective that explicitly asks about them."
            )
            return 1
        print()
        print("[OK] every terminal closure is reachable from the skill's queries.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
