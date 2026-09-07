"""Measure the recall of refine-deck's defunct-citation check.

The check lives as prose in `goc/templates/skills/refine-deck/SKILL.md`
§ "Defunct file:line citations". This script implements both the predicate
that section USED to specify and the one it specifies now, runs them over the
same population, and exits non-zero unless the current one reports every
drifted citation.

Population: every citation each open card carried *when it was filed* (the
README blob at the card's creating commit), so the measurement does not depend
on any later repair of the deck.

Ground truth per citation: the cited line no longer holds the text it held at
filing, i.e. the number now addresses unrelated code. Two predicates are scored
against it:

  bounds test   -- the old spec, "the cited line is <= EOF". Structurally
                   unable to fire on a file that grew.
  anchor test   -- the current spec: compare the text AT the cited line in HEAD
                   against the text the card anchored on at its creating
                   commit. Coincides with ground truth by construction; that is
                   the point, and the bounds test's overlap with it is 0.

The assertion that is not definitional is COMPLETENESS of the reporting. The
spec's repair step only rewrites a number on a unique, non-trivial match, so
every drifted citation must land in exactly one of two reported buckets --
auto-repaired, or residue handed to a human. A pass that emitted only the
repairable ones would be the same fail-open shape as the bounds test.
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

# `file.py:120` and the range form `file.py:120-140`, whose endpoints the spec
# maps independently.
CITE = re.compile(r"`?([A-Za-z0-9_./-]+\.py)`?:(\d+)(?:-(\d+))?")

# A line shorter than this matches everywhere, so the spec refuses to relocate
# on it. Keep in sync with the ">~12 chars" guard in the skill body.
TRIVIAL_LEN = 12

# The population has to stay big enough to exercise the blind region; a run
# over a handful of citations would pass while proving nothing.
MIN_CITATIONS = 100


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
    """Cards cite `engine.py:N` as shorthand for `goc/engine.py:N`.

    Candidates are ordered so a non-mirror match wins, per the spec.
    """
    for cand in (path, f"goc/{path}"):
        if (ROOT / cand).is_file():
            return cand
    return None


def bounds_reports(num: int, head: list[str]) -> bool:
    """The predicate the section used to specify: `the cited line is <= EOF`."""
    return num > len(head)


def anchor_reports(anchor: str, num: int, head: list[str]) -> bool:
    """The predicate the section specifies now: anchor != what is at the line."""
    if num > len(head):
        return True
    return head[num - 1].strip() != anchor.strip()


def repair(anchor: str, head: list[str]) -> tuple[str, str]:
    """Step 4: relocate the anchor, or hand the citation to a human.

    Returns (bucket, detail) where bucket is `repaired` or `residue`.
    """
    text = anchor.strip()
    if len(text) < TRIVIAL_LEN:
        return "residue", "trivial"
    hits = [i + 1 for i, line in enumerate(head) if line.strip() == text]
    if not hits:
        return "residue", "anchor absent"
    if len(hits) > 1:
        return "residue", "ambiguous"
    return "repaired", str(hits[0])


def main() -> int:
    from goc import engine

    cards = [c for c in engine.load_all_cards() if c.frontmatter.get("status") == "open"]
    head_cache: dict[str, list[str]] = {}

    unchanged = drifted = 0
    bounds_hits = anchor_hits = 0
    buckets = {"repaired": 0, "residue": 0}
    residue_kinds: dict[str, int] = {}
    unreported: list[str] = []
    false_positives: list[str] = []
    examples: list[str] = []

    for card in sorted(cards, key=lambda c: c.title):
        commit = creating_commit(card.title)
        if not commit:
            continue
        original = git("show", f"{commit}:.game-of-cards/deck/{card.title}/README.md") \
            or git("show", f"{commit}:deck/{card.title}/README.md")
        if original is None:
            continue

        cites = set()
        for m in CITE.finditer(original):
            for endpoint in (m.group(2), m.group(3)):
                if endpoint:
                    cites.add((m.group(1), int(endpoint)))

        for raw, num in sorted(cites):
            real = resolve(raw)
            if real is None:
                continue
            then = blob(commit, real)
            if then is None or num > len(then):
                continue
            if real not in head_cache:
                head_cache[real] = (ROOT / real).read_text(errors="replace").splitlines()
            head = head_cache[real]
            anchor = then[num - 1]

            # Ground truth, read straight off the two blobs.
            has_drifted = num > len(head) or head[num - 1].strip() != anchor.strip()
            # The two predicates, scored against it.
            reported = anchor_reports(anchor, num, head)
            if bounds_reports(num, head):
                bounds_hits += 1

            if not has_drifted:
                unchanged += 1
                if reported:
                    false_positives.append(f"{card.title}: {raw}:{num}")
                continue

            drifted += 1
            if not reported:
                unreported.append(f"{card.title}: {raw}:{num}")
                continue
            anchor_hits += 1
            bucket, detail = repair(anchor, head)
            buckets[bucket] += 1
            if bucket == "residue":
                residue_kinds[detail] = residue_kinds.get(detail, 0) + 1
            if len(examples) < 3:
                now = head[num - 1].strip() if num <= len(head) else "<past EOF>"
                verdict = f"-> L{detail}" if bucket == "repaired" else f"-> residue: {detail}"
                examples.append(
                    f"    {card.title}\n"
                    f"      cite {raw}:{num} in a {len(head)}-line file, so the bounds test says CLEAN\n"
                    f"      at filing: {anchor.strip()[:60]!r}\n"
                    f"      today    : {now[:60]!r}  {verdict}"
                )

    total = unchanged + drifted
    residue_detail = ", ".join(f"{k} {v}" for k, v in sorted(residue_kinds.items()))
    print(f"open cards examined            : {len(cards)}")
    print(f"citations replayed at filing   : {total}")
    print()
    print(f"  unchanged since filing       : {unchanged}")
    print(f"  DRIFTED (ground truth)       : {drifted}")
    print()
    print("verdicts on the drifted set:")
    print(f"  bounds test `line <= EOF`    : {bounds_hits} reported, {drifted - bounds_hits} missed")
    print(f"  anchor test (current spec)   : {anchor_hits} reported, {len(unreported)} missed")
    print(f"      auto-repairable          : {buckets['repaired']}")
    print(f"      residue, human-reported  : {buckets['residue']}  ({residue_detail})")
    print()
    print(f"  anchor test on the {unchanged} unchanged cites: "
          f"{len(false_positives)} false positives")
    print()
    if examples:
        print("  examples from the drifted set:")
        print("\n".join(examples))
        print()

    if total < MIN_CITATIONS:
        print(f"FAIL: only {total} citations replayed (< {MIN_CITATIONS}); "
              "the fixture is exhausted and this run proves nothing.")
        return 1
    if not drifted:
        print("FAIL: no drifted citations in the replayed population; "
              "neither predicate is under test.")
        return 1
    if unreported:
        print(f"FAIL: {len(unreported)} drifted citations went unreported by the "
              "specified check, e.g. " + unreported[0])
        return 1
    if false_positives:
        print(f"FAIL: {len(false_positives)} still-correct citations were reported "
              "as defunct, e.g. " + false_positives[0])
        return 1
    if buckets["repaired"] + buckets["residue"] != drifted:
        print("FAIL: the repair step dropped citations instead of reporting them.")
        return 1
    print(f"PASS: the specified check reports all {drifted} drifted citations "
          f"({buckets['repaired']} repairable, {buckets['residue']} handed to a "
          f"human); the bounds test it replaced reports {bounds_hits}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
