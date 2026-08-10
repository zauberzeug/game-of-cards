"""Show that refine-deck's `<= EOF` citation check cannot fire on a growing file.

The check is specified in `goc/templates/skills/refine-deck/SKILL.md` as
"verify each cited file exists and the cited line is <= EOF". This script
replays it against every citation each open card carried *when it was filed*
(the README blob at the card's creating commit), so the measurement does not
depend on any later repair of the deck.

For each citation it computes two verdicts:

  EOF verdict      -- what the shipped check reports today: clean iff the
                      cited line number is still within the file.
  content verdict  -- whether the cited line still holds the text it held at
                      filing time; "moved" means the citation now points at
                      unrelated code.

Citations that are `moved` but `clean` are the blind region: real rot the
shipped predicate is structurally unable to report.
"""

import re
import subprocess
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

CITE = re.compile(r"`?([A-Za-z0-9_./-]+\.py)`?:(\d+)")


def git(*args: str) -> str | None:
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def creating_commit(title: str) -> str | None:
    out = git(
        "log", "--diff-filter=A", "--format=%H", "--",
        f".game-of-cards/deck/{title}/README.md", f"deck/{title}/README.md",
    )
    return out.split()[-1] if out and out.split() else None


def blob(commit: str, path: str) -> list[str] | None:
    out = git("show", f"{commit}:{path}")
    return out.splitlines() if out is not None else None


def resolve(path: str) -> str | None:
    """Cards cite `engine.py:N` as shorthand for `goc/engine.py:N`."""
    for cand in (path, f"goc/{path}"):
        if (ROOT / cand).is_file():
            return cand
    return None


def main() -> int:
    from goc import engine

    cards = [c for c in engine.load_all_cards() if c.frontmatter.get("status") == "open"]
    head_cache: dict[str, list[str]] = {}

    blind = clean_and_current = flagged = 0
    examples: list[str] = []

    for card in sorted(cards, key=lambda c: c.title):
        commit = creating_commit(card.title)
        if not commit:
            continue
        original = git("show", f"{commit}:.game-of-cards/deck/{card.title}/README.md") \
            or git("show", f"{commit}:deck/{card.title}/README.md")
        if original is None:
            continue

        for raw, num in {(m.group(1), int(m.group(2))) for m in CITE.finditer(original)}:
            real = resolve(raw)
            if real is None:
                continue
            then = blob(commit, real)
            if then is None or num > len(then):
                continue
            if real not in head_cache:
                head_cache[real] = (ROOT / real).read_text(errors="replace").splitlines()
            now = head_cache[real]

            eof_clean = num <= len(now)
            moved = not eof_clean or now[num - 1].strip() != then[num - 1].strip()

            if not eof_clean:
                flagged += 1
            elif moved:
                blind += 1
                if len(examples) < 5:
                    examples.append(
                        f"    {card.title}\n"
                        f"      cite {raw}:{num} -> {real} has {len(now)} lines, so EOF check says CLEAN\n"
                        f"      at filing: {then[num - 1].strip()[:66]!r}\n"
                        f"      today    : {now[num - 1].strip()[:66]!r}"
                    )
            else:
                clean_and_current += 1

    total = blind + clean_and_current + flagged
    print(f"open cards examined            : {len(cards)}")
    print(f"citations replayed at filing   : {total}")
    print()
    print(f"  still correct                : {clean_and_current}")
    print(f"  FLAGGED by the `<= EOF` check: {flagged}")
    print(f"  MOVED but reported clean     : {blind}   <-- the blind region")
    print()
    if examples:
        print("  examples:")
        print("\n".join(examples))
        print()

    if blind and not flagged:
        print("FAIL: the shipped check reported a clean deck while", blind,
              "citations pointed at unrelated code.")
        return 1
    if blind:
        print("FAIL:", blind, "moved citations went unreported;",
              flagged, "were caught only because those files shrank.")
        return 1
    print("PASS: every moved citation was reported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
