#!/usr/bin/env python3
"""Cites the citation-repair recipe calls `current` on the strength of a brace.

The recipe in `goc/templates/skills/refine-deck/reference.md` § "Citation
anchor check" decides in two steps.  As shipped from 2026-08-10 to
2026-09-14, step 3 asked whether the cite is defunct — "Anchor text != the
text at that line in HEAD -> defunct" — with no predicate on what that text
is, while step 4 relocated a defunct cite and *only there* guarded on
substance: "rewrite the number only when the match is UNIQUE and the line is
NON-TRIVIAL: skip blanks, bare braces, and anything under roughly 12
characters, which match everywhere."

So a cite whose anchor line is `}` was verdicted `current` whenever HEAD also
held `}` at that offset, which in a brace-dense or blank-line-dense file is
the common case rather than the exceptional one.  The recipe's own words say
why that is not evidence: those lines "match everywhere".  And `current` is a
silent verdict — no decline line, no residue row — so nothing surfaced it.

Two checks, both read-only:

1. The shipped prose is classified.  The fix is an ORDERING: the
   non-triviality predicate has to run BEFORE the comparison, on both
   surfaces (`refine-deck/SKILL.md` step 3 and `reference.md`'s **Deciding.**
   paragraph), and name the DECLINE it produces.  Prose that reaches a
   verdict without the predicate ahead of it, or that keeps the predicate
   downstream where it shipped, is unguarded.

2. The deck is censused: every in-scope cite in an open or active card whose
   anchor text matches HEAD at the cited offset, split by whether that
   anchor line is one the predicate refuses.  The split does not change with
   the fix — those cites still exist.  What changes is their disposition:
   under a guarded recipe they are declines a reader sees, not `current`
   verdicts nobody can.

Exits 0 when no `current` verdict the shipped recipe would issue rests on a
trivial anchor line.
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


def git(*args: str) -> str | None:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    return None if r.returncode else r.stdout.decode("utf-8", "replace")


def trivial(line: str | None) -> bool:
    """The recipe's non-triviality predicate: blanks, bare braces, <~12 chars."""
    if line is None:
        return True
    t = line.strip()
    return len(t) < 12 or bool(re.fullmatch(r"[\{\}\(\)\[\],;:]+", t))


def resolve(path: str, universe: set[str]) -> str | None:
    if path in universe:
        return path
    cands = [f for f in universe if f.endswith("/" + path)]
    if not cands:
        return None
    pool = [c for c in cands if not c.startswith(MIRROR)] or cands
    return sorted(pool, key=lambda c: (c.count("/"), len(c)))[0]


def in_scope_cites(readme: Path):
    """Prose cites and fenced comment-label cites; pasted records are out of scope."""
    for lineno, ln in enumerate(readme.read_text(encoding="utf-8").split("\n"), 1):
        m = FENCE.match(ln)
        if m:
            in_scope_cites.fence = not getattr(in_scope_cites, "fence", False)
            continue
        for cm in CITE.finditer(ln):
            if ln[cm.end():].startswith(":"):
                continue                                     # grep-style record
            if getattr(in_scope_cites, "fence", False) and not re.search(
                r"(^|\s)(#|//)[^\n]*$", ln[: cm.start()]
            ):
                continue                                     # fenced, not a label
            yield lineno, cm.group(0), cm.group(1), int(cm.group(2)), cm.group(3)
    in_scope_cites.fence = False


SKILL = ROOT / "goc/templates/skills/refine-deck/SKILL.md"
REFERENCE = ROOT / "goc/templates/skills/refine-deck/reference.md"


def _flat(prose: str) -> str:
    """Hard-wrapped prose as one lowercase line, so rules survive rewrapping."""
    return " ".join(prose.split()).lower()


def decide_guarded(prose: str) -> bool | None:
    """Does this stretch of prose refuse a trivial anchor BEFORE comparing?

    None when the prose reaches no defunct/current verdict at all — it is
    not the deciding rule and there is nothing to classify.
    """
    flat = _flat(prose)
    if "defunct" not in flat:
        return None
    if "bare brace" not in flat:
        return False
    return (
        flat.index("bare brace") < flat.index("defunct")
        and "decline" in flat
        and "never `current`" in flat
    )


def shipped_decide_rules() -> dict[str, bool | None]:
    """The two surfaces a pass can follow, each classified on its own."""
    skill = SKILL.read_text(encoding="utf-8")
    section = re.search(
        r"^### Defunct file:line citations$.*?(?=^#{1,3} \S)", skill, re.S | re.M
    )
    step3 = re.search(r"^3\. .*?(?=^4\. )", section.group(0), re.S | re.M) if section else None
    ref = REFERENCE.read_text(encoding="utf-8")
    anchor_sec = re.search(r"^## Citation anchor check$.*?(?=^## )", ref, re.S | re.M)
    deciding = re.search(
        r"^\*\*Deciding\.\*\* .*?(?=\n\n\*\*)", anchor_sec.group(0), re.S | re.M
    ) if anchor_sec else None
    return {
        "SKILL.md step 3": decide_guarded(step3.group(0)) if step3 else None,
        "reference.md **Deciding.**": decide_guarded(deciding.group(0)) if deciding else None,
    }


def main() -> int:
    print('=== 1. does the shipped recipe refuse a trivial anchor first? ===')
    rules = shipped_decide_rules()
    for label, verdict in rules.items():
        word = {True: "guarded", False: "UNGUARDED", None: "not found"}[verdict]
        print(f"  {label:<28}: {word}")
    guarded = all(v is True for v in rules.values())
    print()

    head_files = set((git("ls-files") or "").split("\n"))
    deck = json.loads(subprocess.run(
        [sys.executable, "-m", "goc.cli", "--status", "all", "--json"],
        cwd=ROOT, capture_output=True, text=True,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin", "HOME": str(Path.home())},
    ).stdout)
    titles = [c["title"] for c in deck if c["status"] in ("open", "active")]

    findings, current_total = [], 0
    for title in titles:
        readme = DECK / title / "README.md"
        if not readme.exists():
            continue
        log = git("log", "--follow", "--format=@%H", "--name-only", "--", str(readme.relative_to(ROOT)))
        commits, sha = [], None
        for ln in (log or "").split("\n"):
            if ln.startswith("@"):
                sha = ln[1:].strip()
            elif ln.strip() and sha:
                commits.append((sha, ln.strip()))
                sha = None
        commits.reverse()
        texts = [git("show", f"{s}:{p}") or "" for s, p in commits]

        for lineno, token, path, start, end in in_scope_cites(readme):
            # Anchor = the commit that last WROTE this number (absent -> present).
            idx = None
            for i, t in enumerate(texts):
                if token in t and not (i and token in texts[i - 1]):
                    idx = i
            if idx is None:
                continue
            asha = commits[idx][0]
            tree = set((git("ls-tree", "-r", "--name-only", asha) or "").split("\n"))
            apath, hpath = resolve(path, tree), resolve(path, head_files)
            if not apath or not hpath:
                continue
            atxt, hpathp = git("show", f"{asha}:{apath}"), ROOT / hpath
            if atxt is None or not hpathp.exists():
                continue
            al = atxt.split("\n")
            hl = hpathp.read_text(encoding="utf-8", errors="replace").split("\n")
            at = lambda ls, n: ls[n - 1] if 1 <= n <= len(ls) else None
            pairs = [(at(al, start), at(hl, start))]
            if end:
                pairs.append((at(al, int(end)), at(hl, int(end))))
            if not all(a == h for a, h in pairs):
                continue                                     # defunct, not our case
            current_total += 1
            weak = [a for a, _ in pairs if trivial(a)]
            if weak:
                findings.append((title, token, weak[0] or ""))

    print("=== 2. what the shipped recipe verdicts over the open/active deck ===")
    print(f"  anchor matches HEAD at the cited offset  : {current_total}")
    print(f"  ...on a line the predicate refuses       : {len(findings)}"
          f"  over {len({f[0] for f in findings})} cards")
    if findings:
        print("\nEach line below matches its anchor on text the recipe's own predicate")
        print("calls unusable — a blank, a bare brace, a line under ~12 characters:\n")
        for title, token, anchor in sorted(findings)[:8]:
            print(f"  {token:<34} anchor={anchor.strip()!r:<14} {title}")
        if len(findings) > 8:
            print(f"  \u2026{len(findings) - 8} more")
    print()

    certified = 0 if guarded else len(findings)
    print(f"`current` verdicts resting on a trivial anchor : {certified}")
    if guarded:
        print("  the shipped recipe DECLINES them and reports them as residue")
        print('  ("trivial anchor, verdict undecidable"), so none is certified')
    else:
        print("  the shipped recipe certifies them, silently \u2014 no decline line,")
        print("  no residue row, nothing for a reader to notice")
    return 1 if certified else 0


if __name__ == "__main__":
    sys.exit(main())
