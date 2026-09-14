#!/usr/bin/env python3
"""Cites whose anchor commit is decided by a *different* cite's history.

The recipe in `goc/templates/skills/refine-deck/reference.md` § "Citation
anchor check" locates a cite's anchor commit by walking the card's own history
and taking "the newest commit at which the exact cite token turns from absent
to present".  The token is the whole identity: nothing ties it to the
occurrence being repaired.  Two ways that breaks inside one card —

  1. **substring collision** — `path:N` occurs inside `path:N-M`, so the
     single-line cite reads as "already present" at every commit the range
     existed, and inherits the range's older anchor;
  2. **convergence** — a repair pass moves cite A onto the number cite B
     already held, so from then on A inherits B's anchor.

Either way the cite is anchored on text it never named, verdicted defunct
when it is correct, and "repaired" onto a wrong line.

This script runs the walk twice — once as written (substring test over the
README text) and once occurrence-aware (the token must appear in the version's
own extracted cite set, and a cite that already resolves at HEAD is left
alone) — and reports every cite where the two disagree about the anchor.

Exits 0 when the two walks agree everywhere.
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


def resolve(path: str, universe: set[str]) -> str | None:
    if path in universe:
        return path
    cands = [f for f in universe if f.endswith("/" + path)]
    if not cands:
        return None
    pool = [c for c in cands if not c.startswith(MIRROR)] or cands
    return sorted(pool, key=lambda c: (c.count("/"), len(c)))[0]


def in_scope_cites(text: str):
    fence = False
    for ln in text.split("\n"):
        if FENCE.match(ln):
            fence = not fence
            continue
        for cm in CITE.finditer(ln):
            if ln[cm.end():].startswith(":"):
                continue
            if fence and not re.search(r"(^|\s)(#|//)[^\n]*$", ln[: cm.start()]):
                continue
            yield cm.group(0), cm.group(1), int(cm.group(2)), cm.group(3)


def main() -> int:
    head_files = set((git("ls-files") or "").split("\n"))
    deck = json.loads(subprocess.run(
        [sys.executable, "-m", "goc.cli", "--status", "all", "--json"],
        cwd=ROOT, capture_output=True, text=True,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin", "HOME": str(Path.home())},
    ).stdout)

    findings, repeated = [], {}
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

        here = [t for t, _p, _s, _e in in_scope_cites(readme.read_text(encoding="utf-8"))]
        dup = {t for t in here if here.count(t) > 1}
        if dup:
            repeated[card] = sorted(dup)

        for token, path, start, end in in_scope_cites(readme.read_text(encoding="utf-8")):
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

    print(f"cites whose two walks disagree about the anchor commit: {len(findings)}"
          f"  over {len({f[0] for f in findings})} cards\n")
    for card, token, cl, cs, al, asx, hd in sorted(findings):
        verdict = "would be 'repaired' onto a wrong line" if al != hd else "harmless here"
        print(f"  {token:<26} {card[:52]}")
        print(f"      token walk  -> {cl}  anchor {al.strip()[:60]!r}")
        print(f"      occurrence  -> {cs}  anchor {asx.strip()[:60]!r}")
        print(f"      HEAD line   ->            {hd.strip()[:60]!r}   ({verdict})")

    print(f"\npopulation at risk — cards holding one in-scope cite token at two or more")
    print(f"occurrences, where the walk cannot give the occurrences different anchors")
    print(f"even in principle: {len(repeated)}")
    print("(benign while both occurrences mean the same line; a repair that moves one")
    print(" onto the other's number is what turns the shape into the defect above)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
