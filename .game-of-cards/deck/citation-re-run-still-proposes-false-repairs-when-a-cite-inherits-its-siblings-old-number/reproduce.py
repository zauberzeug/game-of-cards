#!/usr/bin/env python3
"""Prove the citation re-run proposes a false repair after a same-commit hand-off.

Builds a throwaway git repo holding one source file and one card that cites two
functions 18 lines apart. Code inserted above both shifts each by 18, and a
repair pass rewrites both cites in ONE commit, so the first cite lands on the
number the second one just left. Both cites are then correct.

The closing re-run is replayed over the COMMITTED history with the anchor walk
exactly as `Skill(refine-deck)` step 2 words it: the anchor is the newest
commit where the cite TOKEN turns from absent to present, presence being set
membership over the version's cite tokens. The inheriting cite's token never
turns: the sibling held it right up to the pass commit. So the walk anchors it
on the sibling's line and proposes moving a correct cite onto the sibling.

Exits 1 while the re-run proposes a move (the fixed point fails), 0 once it
proposes none. Exits 2 if SKILL.md no longer words step 2 as a token walk:
the replay below then needs updating to the amended rule before it can judge.
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


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True,
                          capture_output=True, text=True).stdout


def source(shift: int) -> str:
    lines = [f"filler_value_{i:03d} = {i}  # filler line {i}" for i in range(1, 61 + shift)]
    lines[10 + shift - 1] = "def alpha_function_for_the_fixture():"
    lines[28 + shift - 1] = "def beta_function_for_the_fixture():"
    return "\n".join(lines) + "\n"


def card(alpha: int, beta: int) -> str:
    return (
        "---\ntitle: fixture-card\n---\n\n# Fixture\n\n"
        f"- `src.py:{alpha}` — `alpha_function_for_the_fixture`, the first cite.\n"
        f"- `src.py:{beta}` — `beta_function_for_the_fixture`, the second cite.\n"
    )


def commit(repo: Path, message: str, src: str, readme: str) -> None:
    (repo / "src.py").write_text(src)
    (repo / CARD).parent.mkdir(parents=True, exist_ok=True)
    (repo / CARD).write_text(readme)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)


def documented_walk_is_token_level() -> bool:
    flat = " ".join(SKILL.read_text(encoding="utf-8").split())
    return "cite token turns from absent to present" in flat


def replay(repo: Path) -> list[str]:
    """Step 2-4 of the citation recipe over committed history, per cite."""
    shas = git(repo, "log", "--follow", "--format=%H", "--", str(CARD)).split()[::-1]
    head_lines = (repo / "src.py").read_text().split("\n")
    proposals = []
    for m in TOKEN.finditer((repo / CARD).read_text()):
        tok, num = m.group(0), int(m.group(2))
        anchor, prev = None, False
        for sha in shas:
            present = tok in {t.group(0) for t in TOKEN.finditer(git(repo, "show", f"{sha}:{CARD}"))}
            if present and not prev:
                anchor = sha
            prev = present
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


def main() -> int:
    if not documented_walk_is_token_level():
        print("SKILL.md step 2 no longer words the anchor walk as a token walk;")
        print("update replay() to the amended rule before reading a verdict here.")
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "probe@example.invalid")
        git(repo, "config", "user.name", "probe")
        commit(repo, "file the card", source(0), card(10, 28))
        commit(repo, f"grow src.py by {SHIFT} lines above both functions", source(SHIFT), card(10, 28))
        commit(repo, "repair pass: re-anchor both cites", source(SHIFT), card(10 + SHIFT, 28 + SHIFT))

        head = (repo / "src.py").read_text().split("\n")
        print(f"After the committed pass: src.py:{10 + SHIFT} = {head[10 + SHIFT - 1]!r}")
        print(f"                          src.py:{28 + SHIFT} = {head[28 + SHIFT - 1]!r}")
        print("Both cites name the function their prose names.\n")
        print("Closing re-run, step 2 as SKILL.md words it, over committed history:")
        proposals = replay(repo)
        print()
        if proposals:
            print(f"DEFECT: the re-run proposes {len(proposals)} move(s) of a correct cite: {proposals}")
            print("The alpha cite would land on beta's definition, a number the card")
            print("already holds for beta. Committing first did not help: the token")
            print(f"src.py:{10 + SHIFT} never turned from absent to present.")
            return 1
        print("PASS: the re-run proposes no further repair; the pass is a fixed point.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
