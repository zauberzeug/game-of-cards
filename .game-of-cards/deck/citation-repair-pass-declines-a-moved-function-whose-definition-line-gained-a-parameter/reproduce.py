#!/usr/bin/env python3
"""Cites the recipe declines even though the function they name is findable.

The recipe in `goc/templates/skills/refine-deck/reference.md` § "Citation
anchor check" relocates a defunct cite by exact full-line equality:

    look for the anchor text in HEAD and rewrite the number only when the
    match is UNIQUE and the line is NON-TRIVIAL

Exact equality makes the anchor line itself the unit of identity.  So an edit
*to that line* — a keyword-only parameter appended to a signature, a changed
return annotation, an argument list reflowed across two lines — turns a
function that is still present, still uniquely named, and still trivially
locatable into "anchor text absent", and the cite is declined on every pass
from then on.

This script reports every declined cite whose anchor line is a `def` or
`class` definition that a unique-name match locates in HEAD.  That subset is
the safely-relocatable one: a definition line is identified by its name, not
by its parameter list.

Exits 0 when no decline is recoverable this way.
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
DEFN = re.compile(r"^\s*(?:async\s+)?(def|class)\s+([A-Za-z_]\w*)\s*\(")


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


def relocatable_by_name(anchor: str, lines: list[str]) -> int | None:
    """A definition line is identified by its NAME, not by its parameter list."""
    m = DEFN.match(anchor)
    if not m:
        return None
    pat = re.compile(r"^\s*(?:async\s+)?" + m.group(1) + r"\s+" + re.escape(m.group(2)) + r"\s*\(")
    hits = [i + 1 for i, l in enumerate(lines) if pat.match(l)]
    return hits[0] if len(hits) == 1 else None


def main() -> int:
    head_files = set((git("ls-files") or "").split("\n"))
    deck = json.loads(subprocess.run(
        [sys.executable, "-m", "goc.cli", "--status", "all", "--json"],
        cwd=ROOT, capture_output=True, text=True,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin", "HOME": str(Path.home())},
    ).stdout)

    findings, declines = [], 0
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

        for _lineno, token, path, start, end in in_scope_cites(readme):
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
            atxt = git("show", f"{asha}:{apath}")
            hp = ROOT / hpath
            if atxt is None or not hp.exists():
                continue
            al = atxt.split("\n")
            hl = hp.read_text(encoding="utf-8", errors="replace").split("\n")
            at = lambda ls, n: ls[n - 1] if 1 <= n <= len(ls) else None

            for which, n in (("start", start), ("end", int(end) if end else None)):
                if n is None:
                    continue
                anchor, now = at(al, n), at(hl, n)
                if anchor is None or anchor == now:
                    continue                                 # current, not declined
                if anchor in hl and hl.count(anchor) == 1:
                    continue                                 # the recipe already repairs this
                declines += 1
                tgt = relocatable_by_name(anchor, hl)
                if tgt is not None and tgt != n:
                    findings.append((card, token, which, n, tgt, anchor.strip(), hl[tgt - 1].strip()))

    print(f"declines the exact-equality rule produces : {declines}")
    print(f"  ...whose anchor is a def/class line that a unique-name match locates : "
          f"{len(findings)}  over {len({f[0] for f in findings})} cards\n")
    for card, token, which, was, now, anchor, head in sorted(findings):
        print(f"  {token:<28} {which:<5} {was} -> {now}   {card[:46]}")
        print(f"      anchored: {anchor[:86]}")
        print(f"      in HEAD : {head[:86]}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
