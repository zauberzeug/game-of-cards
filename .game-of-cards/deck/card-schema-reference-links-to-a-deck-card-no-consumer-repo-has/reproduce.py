#!/usr/bin/env python3
"""Prove the shipped card-schema reference links to a card no consumer has.

Three independent demonstrations, each printed with its verdict:

1. **Source tree** — resolve the link's relative target from the
   source-of-truth template. It lands in `goc/.game-of-cards/`, which does
   not exist: the link is broken in the file that ships it.
2. **Consumer install** — run `goc install --claude --local-skills` into a
   scratch repo and resolve the link from the installed skill. It lands
   inside the consumer's own deck, at a card the fresh deck has never
   contained.
3. **Shipped surface sweep** — every markdown link under the shipped skill
   trees whose target points into a `.game-of-cards/deck/` path. This is the
   set the fix must empty, and the set the regression guard pins.

Exits 0 once no shipped skill body links into a deck, non-zero while the
offender is present.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
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

# The source of truth plus every mirror `goc install` / the plugin payloads
# actually hand to a reader.
SHIPPED_SKILL_TREES = (
    "goc/templates/skills",
    ".claude/skills",
    ".codex/skills",
    "claude-plugin/skills",
    "codex-plugin/skills",
    "openclaw-plugin/skills",
)

# A markdown link whose target routes through a `.game-of-cards/deck/` path.
# Same predicate as `tests/test_skill_template_deck_links.py`, which is where it
# is enforced from CI; a URL is not a filesystem promise and stays out of scope.
DECK_LINK_RE = re.compile(r"\]\(([^)\s]*\.game-of-cards/deck/[^)\s]*)\)")
_URL_SCHEME_RE = re.compile(r"\A[a-z][a-z0-9+.-]*:", re.IGNORECASE)


def deck_links(text: str) -> list[str]:
    """Return every markdown link target in `text` that points into a deck."""
    return [t for t in DECK_LINK_RE.findall(text) if not _URL_SCHEME_RE.match(t)]


def sweep(root: Path) -> list[tuple[Path, int, str]]:
    """Return (path, line, target) for every deck link in the shipped trees."""
    hits: list[tuple[Path, int, str]] = []
    for tree in SHIPPED_SKILL_TREES:
        base = root / tree
        if not base.is_dir():
            continue
        for md in sorted(base.rglob("*.md")):
            for lineno, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
                for target in deck_links(line):
                    hits.append((md.relative_to(root), lineno, target))
    return hits


def demo_source_tree(hits: list[tuple[Path, int, str]]) -> None:
    print("1. Source-of-truth template — does the relative target resolve?")
    template_hits = [h for h in hits if str(h[0]).startswith("goc/templates/skills/")]
    if not template_hits:
        print("   (no deck link in goc/templates/skills/ — nothing to resolve)\n")
        return
    for path, lineno, target in template_hits:
        resolved = (ROOT / path).parent.joinpath(target).resolve()
        print(f"   {path}:{lineno}")
        print(f"     target   {target}")
        print(f"     resolves {resolved}")
        print(f"     exists   {resolved.exists()}")
    print()


def demo_consumer_install(hits: list[tuple[Path, int, str]]) -> None:
    print("2. Fresh `goc install --claude --local-skills` — what does a consumer get?")
    if not hits:
        print("   (no deck link ships — nothing to check)\n")
        return
    if shutil.which("git") is None:
        print("   SKIPPED: git not available\n")
        return
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "consumer"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
        install = subprocess.run(
            [sys.executable, "-m", "goc.cli", "install", "--claude", "--local-skills"],
            cwd=repo,
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin", "HOME": tmp},
        )
        if install.returncode != 0:
            print(f"   SKIPPED: install failed: {install.stderr.strip().splitlines()[-1:]}\n")
            return
        installed = repo / ".claude" / "skills" / "card-schema" / "reference.md"
        if not installed.exists():
            print("   SKIPPED: card-schema reference not installed\n")
            return
        deck = repo / ".game-of-cards" / "deck"
        print(f"   consumer deck contents: {sorted(p.name for p in deck.iterdir())}")
        for target in deck_links(installed.read_text(encoding="utf-8")):
            resolved = installed.parent.joinpath(target).resolve()
            print(f"     link target  {target}")
            print(f"     resolves     {resolved}")
            print(f"     exists       {resolved.exists()}")
    print()


def demo_sweep(hits: list[tuple[Path, int, str]]) -> None:
    print("3. Deck links across every shipped skill tree:")
    if not hits:
        print("   none — the shipped skill bodies link to no deck path.")
    for path, lineno, target in hits:
        resolved = (ROOT / path).parent.joinpath(target).resolve()
        mark = "resolves-here" if resolved.exists() else "BROKEN-here"
        print(f"   {path}:{lineno}  [{mark}]")
    print()


def main() -> int:
    hits = sweep(ROOT)
    demo_source_tree(hits)
    demo_consumer_install(hits)
    demo_sweep(hits)

    if hits:
        print(
            f"FAIL: {len(hits)} shipped skill line(s) link into a `.game-of-cards/deck/` "
            "path. A consuming repo has none of goc's own cards, so every one of these "
            "is dead on install."
        )
        return 1
    print("PASS: no shipped skill body links into a deck path.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
