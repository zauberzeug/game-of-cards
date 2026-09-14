#!/usr/bin/env python3
"""Cites the citation-repair recipe calls `current` on the strength of a brace.

The recipe in `goc/templates/skills/refine-deck/reference.md` § "Citation
anchor check" decides in two steps.  Step 3 asks whether the cite is defunct:
"Anchor text != the text at that line in HEAD -> defunct."  Step 4 then
relocates a defunct cite, and *only there* does the recipe guard on substance
— "rewrite the number only when the match is UNIQUE and the line is
NON-TRIVIAL: skip blanks, bare braces, and anything under roughly 12
characters, which match everywhere."

Step 3 carries no such guard.  A cite whose anchor line is `}` is therefore
verdicted `current` whenever HEAD also holds `}` at that offset, which in a
brace-dense or blank-line-dense file is the common case rather than the
exceptional one.  The recipe's own words say why that is not evidence: those
lines "match everywhere".

This script reports every cite in an open or active card whose `current`
verdict rests on such a line.  It does not repair anything — the point is
that the pass currently cannot tell these apart from real matches, so it
reports nothing at all.

Exits 0 when no `current` verdict rests on a trivial anchor line.
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
    """The recipe's own step-4 predicate: blanks, bare braces, under ~12 chars."""
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


def main() -> int:
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

    print(f"`current` verdicts over open/active cards : {current_total}")
    print(f"  ...resting on a trivial anchor line     : {len(findings)}"
          f"  over {len({f[0] for f in findings})} cards")
    if findings:
        print("\nEach line below is a cite the pass reports as verified, on the strength")
        print("of an anchor the recipe's own step-4 guard calls unusable:\n")
        for title, token, anchor in sorted(findings):
            print(f"  {token:<34} anchor={anchor.strip()!r:<14} {title}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
