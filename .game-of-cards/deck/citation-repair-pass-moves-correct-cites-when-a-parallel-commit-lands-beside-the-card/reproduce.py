"""Reproduce: the citation recipe moves cites numbered against a neighbouring commit's tree.

refine-deck's citation anchor check (`goc/templates/skills/refine-deck/reference.md`
§ Citation anchor check) anchors a cite at the commit that last wrote its
number, reads the cited line there, and relocates the cite when HEAD holds that
text uniquely somewhere else. That assumes the number was computed against the
anchor commit's tree. Two cards in this deck were numbered against the tree of
a parallel commit to the cited file that landed minutes away from the card:

  later tree    66678c34 files openclaw-plugin-hooks-never-deliver-...;
                ffc0f4bc, 400 s later, adds six lines above the cited handlers.
                The card's numbers fit ffc0f4bc.
  earlier tree  dc484d63 files auto-commit-publishes-dangling-edges-...;
                6d36c3dc, 37 s earlier, adds six lines above the cited calls.
                The card's numbers fit 6d36c3dc^, the tree before it.

Everything is replayed on immutable commits, so later code motion cannot
change the verdict. For each instance the probe takes the tree the author
numbered against as "HEAD" — every cite is correct there by construction — and
applies the documented rule: anchor text = the cited line at the anchor
commit, relocate on a unique match. A proposed move is a correct cite moved.

Exit codes: 0 = defect no longer fires (the reference's citation section
carries the `anchor tree ambiguous` decline this card's fix adds), 1 = defect
fires (the documented recipe moves at least one correct cite and the reference
has no such rule), 2 = the harness or a precondition is broken (commits
missing, e.g. a shallow clone, or the replay's assumptions no longer hold).

Run with:  uv run python .game-of-cards/deck/citation-repair-pass-moves-correct-cites-when-a-parallel-commit-lands-beside-the-card/reproduce.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir() and (p / "goc").is_dir():
            return p
        p = p.parent
    raise RuntimeError("goc source tree not found")


ROOT = _repo_root()
REFERENCE = ROOT / "goc" / "templates" / "skills" / "refine-deck" / "reference.md"
GUARD = "anchor tree ambiguous"

# (label, cited path, anchor commit, tree the author numbered against,
#  {cited number: what the card's prose names, as a line prefix})
INSTANCES = [
    ("later tree", "openclaw-plugin/index.ts", "66678c34", "ffc0f4bc", {
        763: 'api.on("before_prompt_build"',
        797: 'api.on("agent_end"',
    }),
    ("earlier tree", "goc/engine.py", "dc484d63", "6d36c3dc^", {
        5237: "if _git_auto_commit(commit_targets,",
        5710: "if _git_auto_commit([DECK_DIR / title, DECK_DIR / advancer]",
        5426: "commit_targets = [card_dir, *(DECK_DIR / t",
    }),
]


def _lines(rev: str, path: str) -> list[str] | None:
    res = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT,
                         capture_output=True, text=True)
    return res.stdout.split("\n") if res.returncode == 0 else None


def main() -> int:
    moved = total = 0
    for label, path, anchor_rev, author_rev, cites in INSTANCES:
        anchor_tree, author_tree = _lines(anchor_rev, path), _lines(author_rev, path)
        if anchor_tree is None or author_tree is None:
            print(f"PRECONDITION: {anchor_rev} / {author_rev} not available (shallow clone?)")
            return 2
        print(f"[{label}] {path}: anchor commit {anchor_rev}, numbered against {author_rev}")
        for n, names in cites.items():
            total += 1
            at_author = author_tree[n - 1].strip()
            if not at_author.startswith(names):
                print(f"HARNESS BROKEN: {path}:{n} at {author_rev} is {at_author!r}")
                return 2
            anchor = anchor_tree[n - 1].strip()
            hits = [i for i, line in enumerate(author_tree, 1) if line.strip() == anchor]
            verdict = (f"relocate to :{hits[0]} (unique match)"
                       if len(anchor) >= 12 and len(hits) == 1
                       else f"declines ({len(hits)} matches)")
            moved += verdict.startswith("relocate")
            print(f"  `{path}:{n}` — the card means : {at_author[:58]}")
            print(f"     anchor text at {anchor_rev}  : {anchor[:58]}")
            print(f"     documented rule        : {verdict}")
        print()

    text = REFERENCE.read_text(encoding="utf-8") if REFERENCE.is_file() else ""
    section = re.search(r"^## Citation anchor check\n(.*?)(?=^## )", text, re.M | re.S)
    if section is None:
        print("HARNESS BROKEN: reference.md has no § Citation anchor check")
        return 2
    guarded = GUARD in section.group(1)
    print(f"reference.md citation section carries `{GUARD}`: {guarded}")

    if guarded:
        print("\nDefect no longer fires: the recipe has a rule for cites numbered against a"
              " neighbouring commit's tree.")
        return 0
    if moved:
        print(f"\nDEFECT PRESENT: the documented recipe moves {moved} of {total} correct cites"
              " numbered against a parallel commit's tree.")
        return 1
    print("\nHARNESS BROKEN: the documented rule no longer proposes a move on either instance")
    return 2


if __name__ == "__main__":
    sys.exit(main())
