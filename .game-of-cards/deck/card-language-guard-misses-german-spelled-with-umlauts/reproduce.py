#!/usr/bin/env python3
"""The English-only card guard cannot see natively-spelled German.

`flag_text` tokenizes with `_TOKEN_RE = re.compile(r"[a-z]+")`. An umlaut is not
in `[a-z]`, so it acts as a token separator: `prüfen` yields `['pr', 'fen']`
rather than one word. Two consequences:

1. The eight German marker entries spelled in ASCII transliteration (`ueber`,
   `koennen`, `muessen`, `duerfen`, `aendern`, `loeschen`, `pruefen`,
   `moeglich`) can never match natively-spelled input.
2. The suffix layer degrades too: `Prüfung` becomes `pr` + `fung`, and `fung`
   is four characters, below `MIN_SUFFIX_TOKEN_LEN`.

The tell is a phrase pair — the same German text is caught in transliteration
and missed with its real spelling.

Exit 0 once every native spelling below is flagged.
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

# (transliterated marker entry, the spelling German actually uses)
MARKER_PAIRS = [
    ("ueber", "über"),
    ("koennen", "können"),
    ("muessen", "müssen"),
    ("duerfen", "dürfen"),
    ("aendern", "ändern"),
    ("loeschen", "löschen"),
    ("pruefen", "prüfen"),
    ("moeglich", "möglich"),
]

# Same German text twice: ASCII transliteration, then real spelling.
PHRASE_PAIRS = [
    ("pruefung schlaegt fehl", "prüfung schlägt fehl"),
    ("loeschen der eintraege", "löschen der einträge"),
    ("ueber die groesse", "über die größe"),
]

# Plausible German card titles as a German-speaking author would type them.
NATIVE_TITLES = [
    "pruefung-der-berechtigung-schlaegt-fehl".replace("ue", "ü").replace("ae", "ä"),
    "loeschen-entfernt-die-eintraege-nicht".replace("oe", "ö").replace("ae", "ä"),
]


def guard_tokens(text: str) -> list[str]:
    """The tokens `flag_text` iterates — the shattered fragments, or the folded word.

    `getattr` rather than a direct read so this script still runs against the
    pre-fix guard, which has no fold step: absent it the column shows the
    shattering that is the defect, present it shows the repair.
    """
    fold = getattr(guard, "_UMLAUT_FOLD", {})
    return guard._TOKEN_RE.findall(text.lower().translate(fold))


def main() -> int:
    print(f"tokenizer = {guard._TOKEN_RE.pattern!r}, "
          f"MIN_SUFFIX_TOKEN_LEN = {guard.MIN_SUFFIX_TOKEN_LEN}, "
          f"folds umlauts = {hasattr(guard, '_UMLAUT_FOLD')}\n")

    print(f"{'marker entry':12} {'native':10} {'tokens the guard sees':24} flagged?")
    dead = []
    for translit, native in MARKER_PAIRS:
        tokens = guard_tokens(native)
        hit = bool(guard.flag_text(native))
        if not hit:
            dead.append(translit)
        print(f"{translit:12} {native:10} {str(tokens):24} {hit}")
    print(f"\nmarker entries unreachable from native spelling: "
          f"{len(dead)}/{len(MARKER_PAIRS)}")
    print(f"  {dead}\n")

    print("same text, transliterated vs. natively spelled:")
    asymmetric = []
    for translit, native in PHRASE_PAIRS:
        a, b = bool(guard.flag_text(translit)), bool(guard.flag_text(native))
        if a and not b:
            asymmetric.append(native)
        print(f"  {translit!r:26} -> {a}")
        print(f"  {native!r:26} -> {b}")
    print(f"\nphrases caught only in transliteration: "
          f"{len(asymmetric)}/{len(PHRASE_PAIRS)}\n")

    print("native-spelling card titles:")
    missed_titles = [t for t in NATIVE_TITLES if not guard.flag_text(t)]
    for title in NATIVE_TITLES:
        print(f"  {title!r} -> {guard.flag_text(title) or 'CLEAN (missed)'}")
    print()

    ok = not dead and not asymmetric and not missed_titles
    print(f"native German is caught: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
