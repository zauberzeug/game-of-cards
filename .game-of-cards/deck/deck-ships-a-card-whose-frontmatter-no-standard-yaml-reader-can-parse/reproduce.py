#!/usr/bin/env python3
"""Proof: this repo's deck currently holds a card no strict YAML reader accepts.

Two independent verdicts, because the repo deliberately ships no YAML
dependency (`drop-third-party-runtime-dependencies-from-goc`):

  Part 1 (dependency-free, always runs) — compares every already-double-quoted
  `summary:` line on disk against the line `goc.engine.emit_frontmatter` would
  write for the same parsed value. A quoted scalar goc itself would quote
  differently is a scalar whose quoting is malformed.

  Part 2 (needs PyYAML, skipped when absent) — runs PyYAML and the repo-local
  guard `scripts/check_card_frontmatter_yaml.py` side by side over the whole
  deck and reports the false-negative set. This is the calibration
  `tests/test_card_frontmatter_yaml.py`'s module docstring asserts is empty.

Exit status: 0 once the deck is clean, 1 while the defect stands.
"""

from __future__ import annotations

import importlib.util
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

from goc import engine  # noqa: E402


def _deck_dir() -> Path:
    return ROOT / ".game-of-cards" / "deck"


def _frontmatter_block(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    parts = text.split("---\n", 2)
    return parts[1] if len(parts) >= 3 else None


def _summary_line(block: str) -> str | None:
    for line in block.splitlines():
        if line.startswith("summary:"):
            return line
    return None


def part1() -> list[str]:
    """Quoted summaries whose on-disk quoting differs from the emitter's."""
    offenders = []
    quoted = 0
    for card_dir in sorted(_deck_dir().iterdir()):
        readme = card_dir / "README.md"
        if not readme.is_file():
            continue
        text = readme.read_text(encoding="utf-8")
        block = _frontmatter_block(text)
        if block is None:
            continue
        on_disk = _summary_line(block)
        if on_disk is None or not on_disk.split(":", 1)[1].strip().startswith('"'):
            continue
        quoted += 1
        fm, body = engine.parse_frontmatter(text)
        canonical_block = _frontmatter_block(engine.emit_frontmatter(fm, body=body))
        if _summary_line(canonical_block or "") != on_disk:
            offenders.append(card_dir.name)

    print(f"Part 1 — already-double-quoted summaries scanned: {quoted}")
    print(f"Part 1 — quoted summaries the emitter would write differently: {len(offenders)}")
    for name in offenders:
        print(f"    {name}")
    return offenders


def part2() -> list[tuple[str, str]] | None:
    """Guard-vs-PyYAML false negatives over the whole deck."""
    try:
        import yaml as pyyaml
    except ModuleNotFoundError:
        print("Part 2 — SKIPPED: PyYAML not importable in this interpreter.")
        print("         Re-run with an interpreter that has it, e.g. `python3 "
              f"{Path(__file__).relative_to(ROOT)}`.")
        return None

    spec = importlib.util.spec_from_file_location(
        "_goc_card_frontmatter_yaml_guard",
        ROOT / "scripts" / "check_card_frontmatter_yaml.py",
    )
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)

    false_negatives: list[tuple[str, str]] = []
    scanned = 0
    for card_dir in sorted(_deck_dir().iterdir()):
        readme = card_dir / "README.md"
        if not readme.is_file():
            continue
        block = _frontmatter_block(readme.read_text(encoding="utf-8"))
        if block is None:
            continue
        scanned += 1
        try:
            pyyaml.safe_load(block)
        except Exception as exc:  # noqa: BLE001 — any strict-YAML refusal counts
            if not guard.flag_frontmatter(block):
                false_negatives.append((card_dir.name, str(exc).splitlines()[0]))

    print(f"Part 2 — cards scanned: {scanned}")
    print(f"Part 2 — PyYAML refuses but the guard reports clean: {len(false_negatives)}")
    for name, reason in false_negatives:
        print(f"    {name}: {reason}")
    return false_negatives


def main() -> int:
    offenders = part1()
    false_negatives = part2()

    broken = bool(offenders) or bool(false_negatives)
    print()
    if broken:
        print("DEFECT STANDS: the deck holds frontmatter no strict YAML reader accepts,")
        print("and every check this repo runs reports it clean.")
        return 1
    print("CLEAN: every quoted summary is in emitter-canonical form"
          + ("" if false_negatives is None else " and PyYAML accepts every card"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
