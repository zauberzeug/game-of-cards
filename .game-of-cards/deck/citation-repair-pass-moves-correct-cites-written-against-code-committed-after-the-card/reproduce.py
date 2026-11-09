"""Reproduce: the citation recipe moves a cite that was written against a later tree.

refine-deck's citation anchor check (`goc/templates/skills/refine-deck/reference.md`
§ Citation anchor check) anchors a cite at the commit that last wrote its
number, reads the cited line there, and relocates the cite when HEAD holds that
text uniquely somewhere else. That assumes the number was computed against the
anchor commit's tree.

The instance, replayed on immutable commits so later code motion cannot change
the verdict:

  66678c34  2026-10-31 05:16:46Z  files openclaw-plugin-hooks-never-deliver-...
            with cites `openclaw-plugin/index.ts:763` (before_prompt_build) and
            `:797` (agent_end)
  ffc0f4bc  2026-10-31 05:23:26Z  adds six lines to openclaw-plugin/index.ts
            above both handlers

The card's numbers were computed against ffc0f4bc's tree. The probe takes
ffc0f4bc as "HEAD" — the tree in which every one of those cites is correct by
construction — and applies the documented rule: anchor text = the cited line at
66678c34, relocate on a unique match. If the rule proposes a move, it moves a
correct cite.

Exit codes: 0 = defect no longer fires (the reference's residue table carries an
`anchor tree ambiguous` decline, so the documented recipe declines these cites
instead of moving them), 1 = defect fires (the documented recipe moves at
least one correct cite), 2 = the harness or a precondition is broken (commits
missing, e.g. a shallow clone; the replay's assumptions about the two trees no
longer hold).

Run with:  uv run python .game-of-cards/deck/citation-repair-pass-moves-correct-cites-written-against-code-committed-after-the-card/reproduce.py
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
PATH = "openclaw-plugin/index.ts"
ANCHOR_COMMIT = "66678c34"   # wrote the numbers (the card's filing commit)
AUTHOR_TREE = "ffc0f4bc"     # the tree the numbers were computed against
CITES = {763: 'api.on("before_prompt_build"', 797: 'api.on("agent_end"'}
GUARD = "anchor tree ambiguous"


def _lines(rev: str) -> list[str] | None:
    res = subprocess.run(["git", "show", f"{rev}:{PATH}"], cwd=ROOT,
                         capture_output=True, text=True)
    return res.stdout.split("\n") if res.returncode == 0 else None


def _commit_time(rev: str) -> int | None:
    res = subprocess.run(["git", "show", "-s", "--format=%ct", rev], cwd=ROOT,
                         capture_output=True, text=True)
    return int(res.stdout) if res.returncode == 0 and res.stdout.strip() else None


def main() -> int:
    anchor_tree, author_tree = _lines(ANCHOR_COMMIT), _lines(AUTHOR_TREE)
    t0, t1 = _commit_time(ANCHOR_COMMIT), _commit_time(AUTHOR_TREE)
    if None in (anchor_tree, author_tree, t0, t1):
        print("PRECONDITION: commits 66678c34 / ffc0f4bc not available (shallow clone?)")
        return 2
    print(f"{PATH}: anchor commit {ANCHOR_COMMIT}, next commit to the file {AUTHOR_TREE}"
          f" {t1 - t0}s later\n")

    moved = 0
    for n, names in CITES.items():
        at_author = author_tree[n - 1].strip()
        if not at_author.startswith(names):
            print(f"HARNESS BROKEN: {PATH}:{n} at {AUTHOR_TREE} is {at_author!r}, not the handler")
            return 2
        anchor = anchor_tree[n - 1].strip()
        hits = [i for i, line in enumerate(author_tree, 1) if line.strip() == anchor]
        print(f"`{PATH}:{n}` — the card means : {at_author[:60]}")
        print(f"   anchor text at {ANCHOR_COMMIT}   : {anchor[:60]}")
        if len(anchor) < 12 or len(hits) != 1:
            print(f"   documented rule          : declines ({len(hits)} matches)\n")
            continue
        print(f"   documented rule          : relocate to :{hits[0]} (unique match)\n")
        moved += 1

    text = REFERENCE.read_text(encoding="utf-8") if REFERENCE.is_file() else ""
    section = re.search(r"^## Citation anchor check\n(.*?)(?=^## )", text, re.M | re.S)
    if section is None:
        print("HARNESS BROKEN: reference.md has no § Citation anchor check")
        return 2
    guarded = GUARD in section.group(1)
    print(f"reference.md residue table carries `{GUARD}`: {guarded}")

    if moved and not guarded:
        print(f"\nDEFECT PRESENT: the documented recipe moves {moved} of {len(CITES)} correct cites"
              " written against a tree committed after the card.")
        return 1
    if guarded:
        print("\nDefect no longer fires: the documented recipe declines a cite whose file was"
              " committed again right after the anchor commit.")
        return 0
    print("\nHARNESS BROKEN: the documented rule no longer proposes a move on the instance")
    return 2


if __name__ == "__main__":
    sys.exit(main())
