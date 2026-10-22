#!/usr/bin/env python3
"""Cites whose anchor commit is decided by a *different* cite's history.

The recipe in `goc/templates/skills/refine-deck/reference.md` § "Citation
anchor check" locates a cite's anchor commit by walking the card's own history
and taking the newest commit at which the cite token turns from absent to
present.  As shipped from 2026-08-17 to 2026-09-14, the token was the whole
identity and presence was a substring search over the README text, so nothing
tied the walk to the OCCURRENCE being repaired.  Two ways that breaks inside
one card —

  1. **substring collision** — `path:N` occurs inside `path:N-M`, so the
     single-line cite reads as "already present" at every commit the range
     existed, and inherits the range's older anchor;
  2. **convergence** — a repair pass moves cite A onto the number cite B
     already held, so from then on the two occurrences are one token with one
     history and no walk can anchor them apart, even in principle.

Either way the cite is anchored on text it never named, verdicted defunct
when it is correct, and "repaired" onto a wrong line.

Two checks, both read-only:

1. The shipped prose is classified.  The fix is two rules on the same walk:
   presence has to be SET MEMBERSHIP in the version's own extracted cite
   tokens (which removes the substring half outright), and a token the card
   holds at two or more in-scope occurrences has to be DECLINED (which is the
   only honest answer to the convergence half).  Prose carrying the walk
   without both is unguarded — including the text this replaced, which called
   the token "exact" and so read as precise already: the word modified the
   token while the test around it was still a substring `in`.

2. The deck is censused: every in-scope cite in an open or active card where
   the two readings of the presence test pick DIFFERENT anchor commits with
   different anchor text, plus the population of cards holding one in-scope
   token at two or more occurrences.  Neither count changes with the fix —
   those cites still exist.  What changes is their disposition: a collided
   cite gets the anchor its own occurrence wrote instead of a neighbour's,
   and a repeated token becomes a residue row a reader sees.

Exits 0 when no cite the shipped recipe would rewrite is anchored on a commit
decided by a different cite's history.
"""
import json
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
DECK = ROOT / ".game-of-cards" / "deck"

EXT = r"(?:py|ts|js|mjs|cjs|md|ya?ml|json|sh|toml|txt|cfg|ini|tsx)"
CITE = re.compile(
    r"(?<![\w/.-])([A-Za-z0-9_][A-Za-z0-9_./-]*\." + EXT + r"):(\d+)"
    r"(?:\s*[-–]\s*(\d+))?(?![\w.-])"
)
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
MIRROR = ("claude-plugin/", "codex-plugin/", "openclaw-plugin/", ".claude/", ".codex/", "goc/_vendor/")

SKILL = ROOT / "goc/templates/skills/refine-deck/SKILL.md"
REFERENCE = ROOT / "goc/templates/skills/refine-deck/reference.md"


def git(*args: str) -> str | None:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    return None if r.returncode else r.stdout.decode("utf-8", "replace")


def resolve(path: str, universe: set[str]) -> str | None:
    if path in universe:
        return path
    cands = [f for f in universe if f.endswith("/" + path)]
    if not cands:
        return None
    pool = [c for c in cands if not c.startswith(MIRROR)] or cands
    return sorted(pool, key=lambda c: (c.count("/"), len(c)))[0]


def in_scope_cites(text: str):
    """Prose cites and fenced comment-label cites; pasted records are out of scope."""
    fence = False
    for ln in text.split("\n"):
        if FENCE.match(ln):
            fence = not fence
            continue
        for cm in CITE.finditer(ln):
            if ln[cm.end():].startswith(":"):
                continue                                     # grep-style record
            if fence and not re.search(r"(^|\s)(#|//)[^\n]*$", ln[: cm.start()]):
                continue                                     # fenced, not a label
            yield cm.group(0), cm.group(1), int(cm.group(2)), cm.group(3)


def _flat(prose: str) -> str:
    """Hard-wrapped prose as one lowercase line, so rules survive rewrapping."""
    return " ".join(prose.split()).lower()


def occurrence_guarded(prose: str) -> bool | None:
    """Does this stretch of prose tie the anchor walk to an OCCURRENCE?

    None when the prose never walks the history at all — it is not the
    anchor rule and there is nothing to classify.
    """
    flat = _flat(prose)
    if "absent to present" not in flat:
        return None
    token_exact = "set membership" in flat and "substring" in flat
    repeats_declined = (
        "two or more" in flat or "more than one" in flat
    ) and "decline" in flat
    return token_exact and repeats_declined


def shipped_anchor_rules() -> dict[str, bool | None]:
    """The two surfaces a pass can follow, each classified on its own."""
    skill = SKILL.read_text(encoding="utf-8")
    step2 = re.search(r"^2\. Anchor = .*?(?=^3\. )", skill, re.S | re.M)
    ref = REFERENCE.read_text(encoding="utf-8")
    section = re.search(r"^## Citation anchor check$.*?(?=^## )", ref, re.S | re.M)
    return {
        "SKILL.md step 2": occurrence_guarded(step2.group(0)) if step2 else None,
        "reference.md § anchor": occurrence_guarded(section.group(0)) if section else None,
    }


def main() -> int:
    print("=== 1. does the shipped recipe anchor per OCCURRENCE? ===")
    rules = shipped_anchor_rules()
    for label, verdict in rules.items():
        word = {True: "guarded", False: "UNGUARDED", None: "not found"}[verdict]
        print(f"  {label:<24}: {word}")
    guarded = all(v is True for v in rules.values())
    print()

    head_files = set((git("ls-files") or "").split("\n"))
    deck = json.loads(subprocess.run(
        [sys.executable, "-m", "goc.cli", "--status", "all", "--json"],
        cwd=ROOT, capture_output=True, text=True,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin", "HOME": str(Path.home())},
    ).stdout)

    total, findings, repeated = 0, [], {}
    for card in [c["title"] for c in deck if c["status"] in ("open", "active")]:
        readme = DECK / card / "README.md"
        if not readme.exists():
            continue
        log = git("log", "--follow", "--format=@%H", "--name-only", "--",
                  str(readme.relative_to(ROOT)))
        commits, sha = [], None
        for ln in (log or "").split("\n"):
            if ln.startswith("@"):
                sha = ln[1:].strip()
            elif ln.strip() and sha:
                commits.append((sha, ln.strip()))
                sha = None
        commits.reverse()
        texts = [git("show", f"{s}:{p}") or "" for s, p in commits]
        toksets = [{m.group(0) for m in CITE.finditer(t)} for t in texts]

        here = list(in_scope_cites(readme.read_text(encoding="utf-8")))
        total += len(here)
        tokens = [t for t, _p, _s, _e in here]
        dup = {t for t in tokens if tokens.count(t) > 1}
        if dup:
            repeated[card] = sorted(dup)

        for token, path, start, end in here:
            # The same walk, read two ways: substring presence over the README
            # text, and membership in that version's extracted cite tokens.
            loose = strict = None
            for i, t in enumerate(texts):
                if token in t and not (i and token in texts[i - 1]):
                    loose = i
                if token in toksets[i] and not (i and token in toksets[i - 1]):
                    strict = i
            if loose is None or strict is None or loose == strict:
                continue
            hpath = resolve(path, head_files)
            if not hpath:
                continue
            hl = (ROOT / hpath).read_text(encoding="utf-8", errors="replace").split("\n")

            def anchor_at(idx: int, n: int) -> str | None:
                s, p = commits[idx]
                ap = resolve(path, set((git("ls-tree", "-r", "--name-only", s) or "").split("\n")))
                blob = git("show", f"{s}:{ap}") if ap else None
                if blob is None:
                    return None
                al = blob.split("\n")
                return al[n - 1] if 1 <= n <= len(al) else None

            head_line = hl[start - 1] if 1 <= start <= len(hl) else None
            a_loose, a_strict = anchor_at(loose, start), anchor_at(strict, start)
            if a_loose == a_strict:
                continue
            findings.append((card, token, commits[loose][0][:9], commits[strict][0][:9],
                             a_loose or "", a_strict or "", head_line or ""))

    print("=== 2. what the two readings of the presence test disagree about ===")
    print(f"  in-scope cites over open/active cards   : {total}")
    print(f"  ...anchored on a different commit by each"
          f" : {len(findings)}  over {len({f[0] for f in findings})} cards")
    for card, token, cl, cs, al, asx, hd in sorted(findings):
        moved = "a rewrite onto a wrong line" if al != hd else "harmless here"
        print(f"\n  {token:<26} {card[:52]}")
        print(f"      substring walk -> {cl}  anchor {al.strip()[:58]!r}")
        print(f"      membership     -> {cs}  anchor {asx.strip()[:58]!r}")
        print(f"      HEAD line      ->            {hd.strip()[:58]!r}   ({moved})")

    print(f"\n  cards holding one in-scope token at two or more occurrences,")
    print(f"  which no walk can anchor apart even in principle: {len(repeated)}")
    print("  (benign while both occurrences still mean the same line; a repair")
    print("   that moves one onto the other's number is what turns the shape")
    print("   into the defect above, and the passes manufacture that shape)")
    print()

    misanchored = 0 if guarded else sum(1 for f in findings if f[4] != f[6])
    print(f"cites the shipped recipe rewrites from another cite's anchor : {misanchored}")
    if guarded:
        print("  presence is membership, so a cite no longer reads as present")
        print("  inside a range that merely spells its number, and a token the")
        print("  card holds twice is DECLINED as residue rather than rewritten")
    else:
        print("  the shipped recipe relocates them, confidently and uniquely,")
        print("  onto the line another cite's anchor text now occupies — and")
        print("  then verdicts the result `current` on every later pass")
    return 1 if misanchored else 0


if __name__ == "__main__":
    sys.exit(main())
