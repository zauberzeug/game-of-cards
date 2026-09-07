#!/usr/bin/env python3
"""Reproduce: the citation-repair recipe has no rule for cites inside fenced blocks.

Two checks, both read-only:

1. The shipped recipe — `refine-deck/SKILL.md` § "Defunct file:line citations"
   and `refine-deck/reference.md` § "Citation anchor check" — is searched for
   any mention of a fenced/code block. The defect fires while neither names
   the case, because a pass then has to invent its own rule.

2. The deck is censused for `file:line` cites that sit inside a fenced block
   on an open card, classified by the shape they actually take. The two shapes
   need opposite treatment, which is what makes the silence in (1) a defect
   rather than an omission nobody can trip over.

Exits 0 either way; the verdict is printed.
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

CITE = re.compile(
    r"((?:[\w.@-]+/)*[\w.@-]+\.(?:py|md|yaml|yml|json|ts|sh|toml|txt|js)):~?(\d+)(?:-~?(\d+))?"
)
FENCE = re.compile(r"^(`{3,}|~{3,})")

# ---------------------------------------------------------------- check 1
print("=== 1. does the shipped recipe mention fenced/code blocks? ===")
sources = {
    "SKILL.md § Defunct file:line citations": (
        ROOT / "goc/templates/skills/refine-deck/SKILL.md",
        "### Defunct file:line citations",
    ),
    "reference.md § Citation anchor check": (
        ROOT / "goc/templates/skills/refine-deck/reference.md",
        "## Citation anchor check",
    ),
}
silent = True
for label, (path, heading) in sources.items():
    text = path.read_text(encoding="utf-8")
    start = text.index(heading)
    # Stop at the next heading of the same or higher level, so the slice is
    # this subsection only — not the sibling categories after it, which carry
    # fences of their own.
    level = len(heading) - len(heading.lstrip("#"))
    end = len(text)
    for m in re.finditer(r"^#{1,%d} \S" % level, text[start + len(heading):], re.MULTILINE):
        end = start + len(heading) + m.start()
        break
    section = text[start:end]
    hits = re.findall(r"fenced|code block|code-block|transcript|```", section)
    print(f"  {label}: {len(hits)} mention(s) of a fenced/code block")
    if hits:
        silent = False
print(f"  -> recipe is {'SILENT (defect fires)' if silent else 'explicit (defect fixed)'}")

# ---------------------------------------------------------------- check 2
print()
print("=== 2. census: cites inside fenced blocks on open cards ===")
out = subprocess.run(
    [sys.executable, "-m", "goc.cli", "--status", "open", "--json"],
    cwd=ROOT, capture_output=True, text=True, env={**__import__("os").environ,
                                                   "PYTHONPATH": str(ROOT)},
)
titles = [c["title"] for c in json.loads(out.stdout)] if out.returncode == 0 else []

label_kind, output_kind, cards = 0, 0, set()
for t in titles:
    p = DECK / t / "README.md"
    if not p.exists():
        continue
    lines = p.read_text(encoding="utf-8").split("\n")
    infence, marker = False, None
    for line in lines:
        m = FENCE.match(line.strip())
        if m:
            tok = m.group(1)[0]
            if not infence:
                infence, marker = True, tok
            elif marker == tok:
                infence, marker = False, None
            continue
        if not infence:
            continue
        cm = CITE.search(line)
        if not cm:
            continue
        cards.add(t)
        comment = re.search(r"(#|//)", line)
        if comment and line.index(cm.group(0)) > comment.start():
            label_kind += 1
        else:
            output_kind += 1

print(f"  comment-label cites (`# path:line` above/beside quoted code): {label_kind}")
print(f"  pasted-tool-output cites (`path:line:content`, no comment marker): {output_kind}")
print(f"  spread over {len(cards)} open cards")
print()
print("The two shapes need opposite treatment: a comment label addresses code")
print("as it is now and must be repaired; pasted output is a dated record and")
print("rewriting it fabricates a result the command never produced. The recipe")
print("distinguishes neither, so each pass picks one and applies it to both.")
