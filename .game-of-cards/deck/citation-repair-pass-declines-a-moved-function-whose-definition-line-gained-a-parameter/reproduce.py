#!/usr/bin/env python3
"""Cites the recipe declines even though the function they name is findable.

The citation recipe in `goc/templates/skills/refine-deck/` relocates a
defunct cite by finding its anchor text in HEAD.  Exact full-line equality
makes the anchor LINE the unit of identity, which is right for a statement
inside a body and wrong for a definition line: append a keyword-only
parameter, widen a return annotation, reflow the argument list, and a
function that is still present, still uniquely named and still one grep
away is reported `anchor text absent` and declined — on this pass and on
every pass after, because nothing about the situation changes.

This script replays the SHIPPED recipe over the open and active deck.  It
reads the two surfaces an agent follows — `SKILL.md` step 4 and
`reference.md` § Citation anchor check — classifies whether they carry the
definition-name relocation rule, and runs the walk with that rule enabled
or disabled accordingly.  The finding it counts is the decline class the
card was filed for: an `anchor text absent` verdict whose anchor is a
`def`/`class` line that a unique-name match locates.

Declines from the OTHER rules are not findings.  An ambiguous occurrence,
a trivial anchor, an ambiguous match, an incoherent range pair — each is a
different rule's correct refusal, and the pair check in particular is
supposed to swallow a name-relocated start whose end stayed put.  Counting
those here would make the guard demand the recipe break its siblings.

Exits 0 when no absent-anchor decline is recoverable by name.
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
SKILL = ROOT / "goc" / "templates" / "skills" / "refine-deck" / "SKILL.md"
REFERENCE = ROOT / "goc" / "templates" / "skills" / "refine-deck" / "reference.md"

EXT = r"(?:py|ts|js|mjs|cjs|md|ya?ml|json|sh|toml|txt|cfg|ini|tsx)"
CITE = re.compile(
    r"(?<![\w/.-])([A-Za-z0-9_][A-Za-z0-9_./-]*\." + EXT + r"):(\d+)"
    r"(?:\s*[-–]\s*(\d+))?(?![\w.-])"
)
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
MIRROR = ("claude-plugin/", "codex-plugin/", "openclaw-plugin/", ".claude/", ".codex/", "goc/_vendor/")
DEFN = re.compile(r"^\s*(?:async\s+)?(def|class)\s+([A-Za-z_]\w*)\s*\(")
MAX_PLAUSIBLE_SPAN = 500

NAME_GUARDED = "definition-relocated-by-its-name"
EXACT_LINE_ONLY = "exact-full-line-equality"

AMBIG_OCC = "ambiguous occurrence"
TRIVIAL = "trivial anchor"
AMBIG = "ambiguous match"
ABSENT = "anchor text absent"
INCOHERENT = "incoherent range pair"
REASONS = (AMBIG_OCC, TRIVIAL, AMBIG, ABSENT, INCOHERENT)


def git(*args: str) -> str | None:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    return None if r.returncode else r.stdout.decode("utf-8", "replace")


def _flat(prose: str) -> str:
    return " ".join(prose.split()).lower()


def documented_definition_rule(prose: str) -> str | None:
    """Which relocation rule does this stretch of shipped prose prescribe?

    Three parts, all required: the retry on a unique `def <name>(` /
    `class <name>(`, the DECLINE when HEAD holds that name twice, and the
    subordination to the range pair check.  Prose that never relocates is
    not this rule and returns None.
    """
    flat = _flat(prose)
    if "relocate" not in flat and "look for the anchor text" not in flat:
        return None
    by_name = "def <name>(" in flat and "class <name>(" in flat
    ambiguity_declined = "definitions of that name" in flat and "decline" in flat
    pair_still_governs = "pair check still" in flat
    if by_name and ambiguity_declined and pair_still_governs:
        return NAME_GUARDED
    return EXACT_LINE_ONLY


def skill_step_four() -> str:
    section = re.search(
        r"^### Defunct file:line citations$.*?(?=^#{1,3} \S)",
        SKILL.read_text(encoding="utf-8"), re.S | re.M,
    ).group(0)
    return re.search(r"^4\. .*?(?=\n\n)", section, re.S | re.M).group(0)


def reference_anchor_section() -> str:
    return re.search(
        r"^## Citation anchor check$.*?(?=^## )",
        REFERENCE.read_text(encoding="utf-8"), re.S | re.M,
    ).group(0)


def resolve(path: str, universe: set[str]) -> str | None:
    if path in universe:
        return path
    cands = [f for f in universe if f.endswith("/" + path)]
    if not cands:
        return None
    pool = [c for c in cands if not c.startswith(MIRROR)] or cands
    return sorted(pool, key=lambda c: (c.count("/"), len(c)))[0]


def in_scope_cites(readme: Path):
    fence = False
    for lineno, ln in enumerate(readme.read_text(encoding="utf-8").split("\n"), 1):
        if FENCE.match(ln):
            fence = not fence
            continue
        for cm in CITE.finditer(ln):
            if ln[cm.end():].startswith(":"):
                continue                                     # grep-style record
            if fence and not re.search(r"(^|\s)(#|//)[^\n]*$", ln[: cm.start()]):
                continue                                     # fenced, not a label
            yield lineno, cm.group(0), cm.group(1), int(cm.group(2)), cm.group(3)


def trivial(line: str) -> bool:
    stripped = line.strip()
    return len(stripped) < 12 or bool(re.fullmatch(r"[{}()\[\],;:]+", stripped))


def by_name(anchor: str, lines: list[str]) -> int | None:
    """Where a DEFINITION went — identified by its name, not its signature."""
    m = DEFN.match(anchor)
    if not m:
        return None
    pat = re.compile(r"^\s*(?:async\s+)?" + m.group(1) + r"\s+" + re.escape(m.group(2)) + r"\s*\(")
    hits = [i + 1 for i, l in enumerate(lines) if pat.match(l)]
    return hits[0] if len(hits) == 1 else None


def map_endpoint(anchored: list[str], head: list[str], n: int, *, name_rule: bool):
    """One endpoint: (line-to-write, None) or (None, decline-reason)."""
    if n > len(anchored):
        return None, ABSENT
    anchor = anchored[n - 1]
    if trivial(anchor):
        return None, TRIVIAL
    if n <= len(head) and head[n - 1] == anchor:
        return n, None                                       # current
    hits = [i + 1 for i, l in enumerate(head) if l == anchor]
    if len(hits) == 1:
        return hits[0], None
    if hits:
        return None, AMBIG
    if name_rule:
        m = DEFN.match(anchor)
        if m:
            found = by_name(anchor, head)
            return (found, None) if found else (None, AMBIG if _name_hits(anchor, head) > 1 else ABSENT)
    return None, ABSENT


def _name_hits(anchor: str, head: list[str]) -> int:
    m = DEFN.match(anchor)
    if not m:
        return 0
    pat = re.compile(r"^\s*(?:async\s+)?" + m.group(1) + r"\s+" + re.escape(m.group(2)) + r"\s*\(")
    return sum(1 for l in head if pat.match(l))


def resolves_at_head(prose: str, path: str, n: int, head_files: set[str]) -> bool:
    """The recipe's belt-and-braces rule, run before the anchor walk.

    "If HEAD holds at the cited line the symbol the card's own prose names,
    the number is correct and no anchor can say otherwise."  Mechanized as
    narrowly as that reads: HEAD's cited line is a definition, and the
    card's text carries that definition's name.
    """
    hpath = resolve(path, head_files)
    if not hpath or not (ROOT / hpath).exists():
        return False
    lines = (ROOT / hpath).read_text(encoding="utf-8", errors="replace").split("\n")
    if n > len(lines):
        return False
    m = DEFN.match(lines[n - 1])
    return bool(m) and m.group(2) in prose


def coherent(start: int, end: int) -> bool:
    return start <= end and end - start <= MAX_PLAUSIBLE_SPAN


def walk(cards: list[str], *, name_rule: bool) -> dict:
    """Replay the recipe over every in-scope cite of every card."""
    head_files = set((git("ls-files") or "").split("\n"))
    out = {
        "cites": 0, "current": 0, "repairs": [], "unanchored": 0,
        "declines": {r: 0 for r in REASONS}, "recoverable": [],
    }
    for card in cards:
        readme = DECK / card / "README.md"
        if not readme.exists():
            continue
        prose = readme.read_text(encoding="utf-8")
        occurrences: dict[str, int] = {}
        for _l, token, *_ in in_scope_cites(readme):
            occurrences[token] = occurrences.get(token, 0) + 1

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
        tokens_at = [set(m.group(0) for m in CITE.finditer(t)) for t in texts]

        for _lineno, token, path, start, end in in_scope_cites(readme):
            out["cites"] += 1
            if occurrences[token] > 1:
                out["declines"][AMBIG_OCC] += 1
                continue
            if end is not None and not coherent(start, int(end)):
                out["declines"][INCOHERENT] += 1
                continue
            if resolves_at_head(prose, path, start, head_files):
                out["current"] += 1                          # belt-and-braces
                continue
            idx = None
            for i, present in enumerate(tokens_at):
                if token in present and not (i and token in tokens_at[i - 1]):
                    idx = i
            if idx is None:
                out["unanchored"] += 1
                continue
            asha = commits[idx][0]
            tree = set((git("ls-tree", "-r", "--name-only", asha) or "").split("\n"))
            apath, hpath = resolve(path, tree), resolve(path, head_files)
            if not apath or not hpath:
                out["unanchored"] += 1
                continue
            atxt = git("show", f"{asha}:{apath}")
            hp = ROOT / hpath
            if atxt is None or not hp.exists():
                out["unanchored"] += 1
                continue
            al = atxt.split("\n")
            hl = hp.read_text(encoding="utf-8", errors="replace").split("\n")

            cited = [start] + ([int(end)] if end is not None else [])
            mapped, reason = [], None
            for n in cited:
                got, why = map_endpoint(al, hl, n, name_rule=name_rule)
                if why:
                    reason = reason or why
                    if why == ABSENT and n <= len(al) and by_name(al[n - 1], hl):
                        out["recoverable"].append(
                            (card, token, n, by_name(al[n - 1], hl),
                             al[n - 1].strip(), hl[by_name(al[n - 1], hl) - 1].strip())
                        )
                else:
                    mapped.append(got)
            if reason:
                out["declines"][reason] += 1
                continue
            if len(mapped) == 2 and not coherent(*mapped):
                out["declines"][INCOHERENT] += 1
                continue
            if mapped == cited:
                out["current"] += 1
            else:
                new = str(mapped[0]) if len(mapped) == 1 else f"{mapped[0]}-{mapped[1]}"
                out["repairs"].append((card, token, f"{path}:{new}"))
    return out


def report(label: str, res: dict) -> None:
    print(f"\n{label}")
    print(f"  in-scope cites ......................... {res['cites']}")
    print(f"  current ................................ {res['current']}")
    print(f"  repairs the pass would apply ........... {len(res['repairs'])}")
    print(f"  no anchor commit in the card's history . {res['unanchored']}")
    print(f"  declines ............................... {sum(res['declines'].values())}")
    for reason in REASONS:
        print(f"    {reason:.<36} {res['declines'][reason]}")
    print(f"  absent-anchor declines a unique-name match locates : "
          f"{len(res['recoverable'])}  over {len({f[0] for f in res['recoverable']})} cards")


def main() -> int:
    verdicts = {
        "SKILL.md step 4": documented_definition_rule(skill_step_four()),
        "reference.md § Citation anchor check":
            documented_definition_rule(reference_anchor_section()),
    }
    for surface, verdict in verdicts.items():
        print(f"{surface:<40} {verdict}")
    shipped = set(verdicts.values()) == {NAME_GUARDED}

    deck = json.loads(subprocess.run(
        [sys.executable, "-m", "goc.cli", "--status", "all", "--json"],
        cwd=ROOT, capture_output=True, text=True,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin", "HOME": str(Path.home())},
    ).stdout)
    cards = [c["title"] for c in deck if c["status"] in ("open", "active")]

    res = walk(cards, name_rule=shipped)
    report("the recipe as shipped" + ("" if shipped else " (name rule NOT documented)"), res)
    for card, token, into in sorted(res["repairs"]):
        print(f"    REPAIR {token:<28} -> {into:<28} {card[:52]}")
    for card, token, was, now, anchor, head in sorted(res["recoverable"]):
        print(f"\n  {token:<28} line {was} -> {now}   {card[:52]}")
        print(f"      anchored: {anchor[:86]}")
        print(f"      in HEAD : {head[:86]}")

    if shipped:
        counterfactual = walk(cards, name_rule=False)
        report("under exact full-line equality — the rule this card replaced", counterfactual)
        for card, token, was, now, anchor, _h in sorted(counterfactual["recoverable"]):
            print(f"  {token:<28} line {was} -> {now}   {card[:52]}")
    return 1 if res["recoverable"] else 0


if __name__ == "__main__":
    sys.exit(main())
