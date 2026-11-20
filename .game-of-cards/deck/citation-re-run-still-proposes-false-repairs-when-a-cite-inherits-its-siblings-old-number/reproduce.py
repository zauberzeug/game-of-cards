#!/usr/bin/env python3
"""Prove the citation re-run proposes a false repair after a same-commit hand-off.

Builds throwaway git repos holding one source file and one card that cites two
functions 18 lines apart — once on two lines, once side by side on one line.
Code inserted above both shifts each by 18, and a repair pass rewrites both
cites in ONE commit, so the first cite lands on the number the second one just
left. Both cites are then correct.

The closing re-run is replayed over the COMMITTED history with the anchor walk
as `Skill(refine-deck)` step 2 words it. As filed, step 2 took the newest commit
where the cite TOKEN turns from absent to present, presence being set
membership over the version's cite tokens. The inheriting cite's token never
turns: the sibling held it right up to the pass commit. So the walk anchored it
on the sibling's line and proposed moving a correct cite onto the sibling. The
amended step 2 also compares the cite's SLOT — its line with cite numbers
masked, plus its place among that line's cites — wherever the token is on both
sides of a commit, and takes a commit that handed the token to the cite.

Exits 1 while the re-run proposes a move (the fixed point fails), 0 once it
proposes none. Exits 2 if SKILL.md words step 2 as neither walk: the replay
below then needs updating to the amended rule before it can judge.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


ROOT = _repo_root()
SKILL = ROOT / "goc" / "templates" / "skills" / "refine-deck" / "SKILL.md"
TOKEN = re.compile(r"(?<![\w./-])([\w./-]+\.py):(\d+)(?:-(\d+))?(?!\d)")
CARD = Path(".game-of-cards/deck/fixture-card/README.md")
SHIFT = 18
TOKEN_WALK, SLOT_WALK = "bare token walk", "slot-comparing walk"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True,
                          capture_output=True, text=True).stdout


def source(shift: int) -> str:
    lines = [f"filler_value_{i:03d} = {i}  # filler line {i}" for i in range(1, 61 + shift)]
    lines[10 + shift - 1] = "def alpha_function_for_the_fixture():"
    lines[28 + shift - 1] = "def beta_function_for_the_fixture():"
    return "\n".join(lines) + "\n"


def card(alpha: int, beta: int, *, one_line: bool) -> str:
    head = "---\ntitle: fixture-card\n---\n\n# Fixture\n\n"
    if one_line:
        return head + (
            f"`src.py:{alpha}` is `alpha_function_for_the_fixture` and "
            f"`src.py:{beta}` is `beta_function_for_the_fixture`.\n"
        )
    return head + (
        f"- `src.py:{alpha}` — `alpha_function_for_the_fixture`, the first cite.\n"
        f"- `src.py:{beta}` — `beta_function_for_the_fixture`, the second cite.\n"
    )


def commit(repo: Path, message: str, src: str, readme: str) -> None:
    (repo / "src.py").write_text(src)
    (repo / CARD).parent.mkdir(parents=True, exist_ok=True)
    (repo / CARD).write_text(readme)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)


def documented_walk() -> str | None:
    """Which walk SKILL.md step 2 words: the bare token walk, the slot walk, or neither."""
    match = re.search(r"^2\. Anchor = .*?(?=^3\. )", SKILL.read_text(encoding="utf-8"),
                      re.S | re.M)
    if match is None:
        return None
    flat = " ".join(match.group(0).split()).lower()
    if "cite token turns from absent to present" not in flat:
        return None
    slot = all(phrase in flat for phrase in (
        "both sides", "masked", "place among",
        "another number before", "another number after",
    ))
    return SLOT_WALK if slot else TOKEN_WALK


def tokens(text: str) -> set[str]:
    return {m.group(0) for m in TOKEN.finditer(text)}


def slots(text: str) -> dict[tuple[str, int], list[str]]:
    """Each cite's slot — its line with cite numbers masked, plus its place on it."""
    out: dict[tuple[str, int], list[str]] = {}
    for line in text.split("\n"):
        masked = TOKEN.sub(lambda m: m.group(1) + ":#", line)
        for place, m in enumerate(TOKEN.finditer(line)):
            out.setdefault((masked, place), []).append(m.group(0))
    return out


def handed_off(before: str, after: str, tok: str) -> bool:
    """Both versions hold `tok`: did this commit hand it to a different cite?"""
    old, new = slots(before), slots(after)
    held_before = {s for s, toks in old.items() if tok in toks}
    held_after = {s for s, toks in new.items() if tok in toks}
    if held_before & held_after:
        return False  # one cite kept its number
    return any(s in old for s in held_after) or any(s in new for s in held_before)


def replay(repo: Path, walk: str) -> list[str]:
    """Steps 2-4 of the citation recipe over committed history, per cite."""
    shas = git(repo, "log", "--follow", "--format=%H", "--", str(CARD)).split()[::-1]
    versions = [(sha, git(repo, "show", f"{sha}:{CARD}")) for sha in shas]
    head_lines = (repo / "src.py").read_text().split("\n")
    proposals = []
    for m in TOKEN.finditer((repo / CARD).read_text()):
        tok, num = m.group(0), int(m.group(2))
        anchor, previous, was_present = None, "", False
        for sha, text in versions:
            present = tok in tokens(text)
            if present and not was_present:
                anchor = sha
            elif present and walk == SLOT_WALK and handed_off(previous, text, tok):
                anchor = sha
            previous, was_present = text, present
        text = git(repo, "show", f"{anchor}:src.py").split("\n")[num - 1].strip()
        subject = git(repo, "log", "-1", "--format=%s", anchor).strip()
        now = head_lines[num - 1].strip()
        line = f"  {tok:<10} anchored at '{subject}': {text!r}"
        if text == now:
            print(line + "  -> current")
            continue
        hits = [i + 1 for i, ln in enumerate(head_lines) if ln.strip() == text]
        if len(hits) == 1:
            print(line + f"\n  {'':<10} HEAD line {num} is {now!r}  -> PROPOSES src.py:{hits[0]}")
            proposals.append(f"{tok} -> src.py:{hits[0]}")
        else:
            print(line + "  -> declined")
    return proposals


def run_fixture(walk: str, *, one_line: bool) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "probe@example.invalid")
        git(repo, "config", "user.name", "probe")
        commit(repo, "file the card", source(0), card(10, 28, one_line=one_line))
        commit(repo, f"grow src.py by {SHIFT} lines above both functions", source(SHIFT),
               card(10, 28, one_line=one_line))
        commit(repo, "repair pass: re-anchor both cites", source(SHIFT),
               card(10 + SHIFT, 28 + SHIFT, one_line=one_line))

        head = (repo / "src.py").read_text().split("\n")
        shape = "side by side on one line" if one_line else "on two lines"
        print(f"Cites {shape}. After the committed pass:")
        print(f"  src.py:{10 + SHIFT} = {head[10 + SHIFT - 1]!r}")
        print(f"  src.py:{28 + SHIFT} = {head[28 + SHIFT - 1]!r}")
        print("Both cites name the function their prose names. Closing re-run:")
        proposals = replay(repo, walk)
        print()
        return proposals


def main() -> int:
    walk = documented_walk()
    if walk is None:
        print("SKILL.md step 2 words the anchor walk as neither the bare token walk")
        print("nor the slot-comparing walk; update replay() to the amended rule")
        print("before reading a verdict here.")
        return 2
    print(f"SKILL.md step 2 words the {walk}; replaying it over committed history.\n")
    proposals = run_fixture(walk, one_line=False) + run_fixture(walk, one_line=True)
    if proposals:
        print(f"DEFECT: the re-run proposes {len(proposals)} move(s) of a correct cite: {proposals}")
        print("Each would land the alpha cite on beta's definition, a number the card")
        print("already holds for beta. Committing first did not help: the token")
        print(f"src.py:{10 + SHIFT} never turned from absent to present.")
        return 1
    print("PASS: the re-run proposes no further repair; the pass is a fixed point.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
