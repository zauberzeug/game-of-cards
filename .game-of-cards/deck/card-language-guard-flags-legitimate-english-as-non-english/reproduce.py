#!/usr/bin/env python3
"""The English-only card guard flags legitimate English words as non-English.

Two independent false-positive sites in `scripts/check_card_language.py`:

1. The suffix layer's `SUFFIX_EXCEPTIONS` set is a flat hand-enumeration of
   English words that end in `-ung` and clear `MIN_SUFFIX_TOKEN_LEN`. English
   `-ung` words are an open family — a strong-verb participle stem, optionally
   carrying a prefix — so enumerating members instead of deriving the rule
   leaves siblings behind. It captured four prefixed forms (`unstrung`,
   `restrung`, `unsprung`, `highstrung`) and the bare `unsung`, but not the two
   stems those prefixes attach to, nor any other prefix.

2. The marker-word layer lists `des` under French. `DES` is the Data Encryption
   Standard — an English technical acronym. The module's own comment says every
   entry "is a claim that its appearance in a card is a language slip and never
   legitimate English"; the docstring names "English acronyms" as a category
   that must stay out.

Exit 0 once neither site fires on English and the German recall set still fails
the guard.
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

_spec = importlib.util.spec_from_file_location(
    "_guard", ROOT / "scripts" / "check_card_language.py"
)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

# English words ending in a `MARKER_SUFFIXES` ending: the participle/adjective
# stems, plus the prefixed forms built from them. Every one is English and must
# not be flagged.
ENGLISH_UNG_WORDS = [
    "hung", "rung", "sung", "dung", "lung", "clung", "flung", "slung",
    "stung", "swung", "wrung", "young", "sprung", "strung",
    "unhung", "unsung", "unslung", "unstrung", "unsprung",
    "restrung", "resprung", "overhung", "overstrung", "outflung", "upswung",
    "highstrung",
]

# English prose/titles that must pass. `des` is DES/3DES, the cipher.
ENGLISH_PHRASES = [
    "retry-loop-has-sprung-a-leak",
    "requests-are-strung-together-without-a-budget",
    "des-cipher-fallback-is-still-enabled",
    "triple-des-key-rotation-is-skipped",
]

# German `-ung` nouns: the recall the suffix layer exists for. These must keep
# firing, so the fix cannot be "delete the suffix layer" or "raise the floor".
GERMAN_UNG_NOUNS = [
    "berechtigung", "aenderung", "pruefung", "loesung", "ordnung", "warnung",
    "rechnung", "regelung", "reinigung", "unterbrechung", "untersuchung",
    "umstellung", "buchung", "sammlung", "meinung",
]


def main() -> int:
    false_positives = [(w, guard.flag_text(w)) for w in ENGLISH_UNG_WORDS]
    false_positives = [(w, r) for w, r in false_positives if r]

    phrase_hits = [(p, guard.flag_text(p)) for p in ENGLISH_PHRASES]
    phrase_hits = [(p, r) for p, r in phrase_hits if r]

    recall_misses = [n for n in GERMAN_UNG_NOUNS if not guard.flag_text(n)]

    # Named differently before and after the fix: a flat `SUFFIX_EXCEPTIONS`
    # enumeration, versus the derived `ENGLISH_UNG_STEMS` + prefixes rule. Report
    # whichever this checkout carries so the probe runs on both.
    if hasattr(guard, "ENGLISH_UNG_STEMS"):
        print(f"exemption rule         = derived ({len(guard.ENGLISH_UNG_STEMS)} stems "
              f"x {len(guard.ENGLISH_UNG_PREFIXES)} prefixes + bare)")
    else:
        print(f"exemption rule         = enumerated {sorted(guard.SUFFIX_EXCEPTIONS)}")
    print(f"MIN_SUFFIX_TOKEN_LEN   = {guard.MIN_SUFFIX_TOKEN_LEN}")
    print(f"'des' in MARKER_WORDS  = {'des' in guard.MARKER_WORDS}")
    print()

    print(
        f"English -ung words falsely flagged: "
        f"{len(false_positives)}/{len(ENGLISH_UNG_WORDS)}"
    )
    for word, reasons in false_positives:
        print(f"  {word!r}: {reasons[0]}")
    print()

    print(f"English card titles falsely flagged: {len(phrase_hits)}/{len(ENGLISH_PHRASES)}")
    for phrase, reasons in phrase_hits:
        print(f"  {phrase}: {reasons[0]}")
    print()

    print(f"German -ung nouns no longer caught (recall regression): {len(recall_misses)}")
    for noun in recall_misses:
        print(f"  {noun}")
    print()

    ok = not false_positives and not phrase_hits and not recall_misses
    print(f"guard accepts every English case: {not false_positives and not phrase_hits}")
    print(f"guard still rejects every German case: {not recall_misses}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
