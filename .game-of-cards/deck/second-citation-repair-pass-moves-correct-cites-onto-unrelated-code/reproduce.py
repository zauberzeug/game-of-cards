#!/usr/bin/env python3
"""Replay refine-deck's citation-repair recipe over this repo's own deck.

The anchor commit the skill names is read out of the skill itself
(`goc/templates/skills/refine-deck/SKILL.md`, step 2 of the defunct-citation
check), so this script measures what a pass following the shipped
instructions would actually do rather than a copy of them.

The recipe that shipped until 2026-08-17 anchored at "the card's creating
commit". That is correct exactly once. After a repair pass rewrites a cite's
line number, the number was authored by the *repair* commit, so reading it at
the *creating* commit yields whatever unrelated code happened to sit at that
offset back then — and the recipe then "relocates" the cite to wherever that
unrelated text lives now.

This script computes, for every `file:line` cite on every open card:

  SPECIFIED anchor = cited_file @ the commit the SKILL names       [line]
  REFERENCE anchor = cited_file @ commit that INTRODUCED this cite [line]

and reports the cites where the two disagree, plus a standing counterfactual
for the retired creating-commit anchor. The reference anchor degenerates to
the creating commit for a cite no pass has ever touched, so the two rules
agree on a virgin deck; they diverge only on repaired ones — which is why the
defect could not surface until a second pass ran.

Exit 1 while the specified recipe disagrees with the reference anchor,
0 once it matches.
"""

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
DECK = ROOT / ".game-of-cards" / "deck"
SKILL = ROOT / "goc" / "templates" / "skills" / "refine-deck" / "SKILL.md"

CREATING = "creating-commit"
AUTHORING = "authoring-commit"


def specified_anchor() -> str:
    """Which anchor commit does the shipped skill body name?

    The two rules are told apart by the git incantation each needs: the
    creating-commit rule exists only to find the README's ADD commit
    (`--diff-filter=A`), the authoring rule walks the README's own history
    (`--follow`) for the commit where the cite token turns from absent to
    present. Prose naming both, or neither, is unclassifiable and treated
    as the creating-commit rule so this script cannot pass by ambiguity.
    """
    step2 = re.search(
        r"^2\. Anchor = .*?(?=^3\. )",
        SKILL.read_text(encoding="utf-8"),
        re.S | re.M,
    )
    prose = step2.group(0) if step2 else ""
    walk = "--follow" in prose and "absent to present" in prose
    return AUTHORING if walk and "--diff-filter=A" not in prose else CREATING

CITE_RE = re.compile(
    r"(?<![\w/.-])((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+"
    r"\.(?:py|md|ts|json|yaml|yml|sh|toml))[:#]L?(\d+)(?:\s*[-–]\s*L?(\d+))?(?![\w.])"
)
MIRROR = (
    "claude-plugin/",
    "codex-plugin/",
    "openclaw-plugin/",
    ".claude/",
    ".codex/",
    "goc/_vendor/",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    ).stdout


def git_ok(*args: str):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


TRACKED = git("ls-files").splitlines()
TRACKED_SET = set(TRACKED)
BY_BASE = defaultdict(list)
for _p in TRACKED:
    BY_BASE[os.path.basename(_p)].append(_p)


def resolve(path: str):
    """Cards write `engine.py:N` for `goc/engine.py:N`; prefer a non-mirror match."""
    if path in TRACKED_SET:
        return path
    cands = BY_BASE.get(os.path.basename(path), [])
    pool = [p for p in cands if p.endswith("/" + path)] or cands
    pool = [p for p in pool if not p.startswith(MIRROR)] or pool
    if not pool:
        return None
    if len(pool) == 1:
        return pool[0]
    pool.sort(key=lambda p: (p.count("/"), len(p)))
    if pool[0].count("/") == pool[1].count("/") and len(pool[0]) == len(pool[1]):
        return None
    return pool[0]


_BLOB: dict = {}


def blob(commit: str, path: str):
    key = (commit, path)
    if key not in _BLOB:
        out = git_ok("show", f"{commit}:{path}")
        _BLOB[key] = out.split("\n") if out is not None else None
    return _BLOB[key]


_HEAD: dict = {}


def head_lines(path: str):
    if path not in _HEAD:
        try:
            _HEAD[path] = (ROOT / path).read_text(
                encoding="utf-8", errors="replace"
            ).split("\n")
        except OSError:
            _HEAD[path] = None
    return _HEAD[path]


def relocate(anchor: str, cur: list):
    """The skill's rule: rewrite only on a unique match of a non-trivial line."""
    if anchor is None or len(anchor.strip()) < 12:
        return None
    hits = [i + 1 for i, l in enumerate(cur) if l == anchor]
    if len(hits) != 1:
        stripped = anchor.strip()
        hits = [i + 1 for i, l in enumerate(cur) if l.strip() == stripped]
    return hits[0] if len(hits) == 1 else None


def main() -> int:
    deck_json = subprocess.run(
        [sys.executable, "-m", "goc.cli", "--status", "all", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    ).stdout
    cards = [c for c in json.loads(deck_json) if c["status"] in ("open", "active")]

    specified = specified_anchor()

    # One tally per candidate anchor rule, scored against the reference.
    tallies = {
        mode: {
            "corrupts_correct": [],  # moves a cite that is right today
            "wrong_target": [],      # moves a cite somewhere else than reference
            "missed": 0,             # declines a cite the reference repairs
            "agree": 0,
        }
        for mode in (AUTHORING, CREATING)
    }
    total = 0
    repaired = 0  # cites whose number was authored after the card was filed

    for card in cards:
        title = card["title"]
        readme = DECK / title / "README.md"
        if not readme.exists():
            continue
        text = readme.read_text(encoding="utf-8")
        cites = [
            (m.group(0), m.group(1), int(m.group(2)))
            for m in CITE_RE.finditer(text)
        ]
        if not cites:
            continue

        rel = f".game-of-cards/deck/{title}/README.md"
        hist = git("log", "--format=%H", "--follow", "--", rel).split()
        if not hist:
            hist = git(
                "log", "--format=%H", "--follow", "--", f"deck/{title}/README.md"
            ).split()
        if not hist:
            continue
        hist.reverse()  # oldest first
        creating = hist[0]

        contents = []
        for c in hist:
            t = git_ok("show", f"{c}:{rel}")
            if t is None:
                t = git_ok("show", f"{c}:deck/{title}/README.md")
            contents.append(t or "")

        for raw, path, line in cites:
            target = resolve(path)
            if target is None:
                continue
            cur = head_lines(target)
            if cur is None:
                continue
            total += 1

            # REFERENCE anchor: the commit that introduced this exact cite token.
            intro, prev = None, False
            for c, body in zip(hist, contents):
                here = raw in body
                if here and not prev:
                    intro = c
                prev = here
            intro = intro or creating
            if intro != creating:
                repaired += 1

            def anchor_of(commit):
                src = blob(commit, target)
                if src is None or line > len(src):
                    return None
                return src[line - 1]

            reference_anchor = anchor_of(intro)
            cur_line = cur[line - 1] if line <= len(cur) else None
            reference_ok = cur_line is not None and cur_line == reference_anchor
            reference_move = (
                None if reference_ok else relocate(reference_anchor, cur)
            )

            for mode, commit in ((AUTHORING, intro), (CREATING, creating)):
                tally = tallies[mode]
                anchor = anchor_of(commit)
                ok = cur_line is not None and cur_line == anchor
                move = None if ok else relocate(anchor, cur)
                if move is not None and reference_ok:
                    tally["corrupts_correct"].append((title, raw, move))
                elif move is not None and move != reference_move:
                    tally["wrong_target"].append((title, raw, move, reference_move))
                elif move is None and reference_move is not None:
                    tally["missed"] += 1
                else:
                    tally["agree"] += 1

    def report(tally, label, who="specified"):
        print(f"{label}\n")
        print(f"  moves a cite that is CORRECT today : {len(tally['corrupts_correct'])}")
        print(f"  moves a cite to the WRONG line     : {len(tally['wrong_target'])}")
        print(f"  declines a cite it should repair   : {tally['missed']}")
        print(f"  agrees with the reference recipe   : {tally['agree']}")
        if tally["corrupts_correct"]:
            print("\n  sample — correct cites it would move:")
            for title, raw, to in tally["corrupts_correct"][:3]:
                print(f"    {raw} in {title}")
                print(f"      -> would be rewritten to line {to}")
        if tally["wrong_target"]:
            print("\n  sample — cites it would misplace:")
            for title, raw, got, want in tally["wrong_target"][:3]:
                print(f"    {raw} in {title}")
                print(f"      {who} -> {got}   reference -> {want}")
        return (
            len(tally["corrupts_correct"]) + len(tally["wrong_target"]) + tally["missed"]
        )

    print(f"open-card cites replayed: {total}")
    print(f"cites whose number a repair pass rewrote: {repaired}")
    print("  (the two anchors can only differ on these — a deck no pass has")
    print("   repaired exercises none of them, which is why one pass hid this)\n")
    print(f"anchor named by {SKILL.relative_to(ROOT)} step 2: {specified}\n")

    broken = report(
        tallies[specified],
        "Specified recipe vs reference anchor (the commit that INTRODUCED the cite):",
    )
    if specified != CREATING:
        print()
        report(
            tallies[CREATING],
            "Counterfactual — the retired creating-commit anchor, same cites:",
            who="retired  ",
        )

    if broken:
        print(
            f"\nDEFECT PRESENT: the specified recipe disagrees with the reference "
            f"anchor on {broken} of {total} cites. Running the documented pass a "
            f"second time rewrites correct citations onto unrelated code."
        )
        return 1
    print(
        "\nPASS: the recipe the skill specifies agrees with the reference anchor "
        "on every cite, including the ones an earlier pass rewrote."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
