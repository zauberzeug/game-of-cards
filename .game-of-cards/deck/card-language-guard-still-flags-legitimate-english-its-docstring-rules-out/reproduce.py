#!/usr/bin/env python3
"""The card-language guard flags English its own docstrings promise it accepts.

Three claims in `scripts/check_card_language.py`, seven English words:

1. Every `MARKER_WORDS` entry was documented as "never legitimate English",
   yet the lists carried `tout`, `nouveau`, `algo` and `nada`.
2. Eight of the nine `MARKER_SUFFIXES` were documented as having "no English
   collision at any length", yet `-heit` matches `fahrenheit`.
3. The `-ung` exemption was documented as closed against "any future prefix
   combination", yet it composed seven listed prefixes, so `hamstrung` and
   `underhung` fired.

Exit 0 once none of the seven is flagged AND German recall is intact. The
German side is chosen to fail the two tempting over-fixes: every noun in
`GERMAN_TAIL_WITNESSES` ends in an English `-ung` stem, so "exempt any token
ending in a known English stem" cannot pass; `unerfahrenheit` ends in
`fahrenheit`, so a tail match on the new exemption cannot pass either.

`--dictionary PATH` additionally sweeps a hunspell `.dic` file (affix rules from
the sibling `.aff`) and prints every dictionary form the guard still flags —
the measurement behind the guard's "Known false positives" docstring section.
It is informational and does not affect the exit code.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections import defaultdict
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

# The seven words from the card's Hypothesis section, each in a phrase that
# shows it in ordinary English use.
ENGLISH_CASES = [
    ("hamstrung", "retry budget is hamstrung by a fixed cap"),
    ("underhung", "underhung rotor"),
    ("fahrenheit", "convert fahrenheit to celsius"),
    ("tout", "the docs tout a flag that was removed"),
    ("nouveau", "art nouveau styling in the site"),
    ("algo", "the algo is fine"),
    ("nada", "nada happens"),
]

# German nouns ending in an English `-ung` stem (Regelung in `lung`, Bildung in
# `dung`, ...): what a tail rule over the whole stem set would wrongly exempt.
GERMAN_TAIL_WITNESSES = [
    "regelung", "aenderung", "loesung", "bildung", "beziehung", "leistung",
    "verzweiflung", "abwechslung", "ursprung", "untersuchung", "sammlung",
]

# German `-heit` nouns, one of which ends in the new exact-match exemption.
GERMAN_HEIT_NOUNS = ["unerfahrenheit", "sicherheit", "freiheit", "einheit"]


def _expand_hunspell(dic: Path) -> dict[str, set[str]]:
    """Every form a hunspell dictionary generates, keyed by its lowercase."""
    rules: dict[str, list[tuple[str, str, str, re.Pattern[str]]]] = defaultdict(list)
    for line in dic.with_suffix(".aff").read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[0] not in ("PFX", "SFX") or parts[2] in ("Y", "N"):
            continue
        kind, flag, strip, add = parts[:4]
        cond = parts[4] if len(parts) > 4 else "."
        strip = "" if strip == "0" else strip
        add = "" if add == "0" else add.split("/")[0]
        anchored = f"^{cond}" if kind == "PFX" else f"{cond}$"
        rules[flag].append((kind, strip, add, re.compile(anchored)))

    forms: dict[str, set[str]] = defaultdict(set)
    for entry in dic.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        word, _, flags = entry.partition("/")
        word = word.strip()
        if not word:
            continue
        derived = {word}
        for f in flags:
            for kind, strip, add, cond in rules.get(f, []):
                if kind == "SFX" and word.endswith(strip) and cond.search(word):
                    derived.add(word[: len(word) - len(strip)] + add)
        unprefixed = set(derived)  # hunspell applies at most one prefix
        for f in flags:
            for kind, strip, add, cond in rules.get(f, []):
                if kind == "PFX" and word.startswith(strip) and cond.search(word):
                    derived |= {add + d[len(strip) :] for d in unprefixed}
        for d in derived:
            if re.fullmatch(r"[A-Za-z]+", d):
                forms[d.lower()].add(d)
    return forms


def sweep(dic: Path) -> None:
    forms = _expand_hunspell(dic)
    flagged = {tok: guard.flag_text(tok) for tok in sorted(forms)}
    flagged = {tok: reasons for tok, reasons in flagged.items() if reasons}
    print(f"\n{dic}: {len(forms)} distinct forms, {len(flagged)} flagged by the guard")
    for tok, reasons in flagged.items():
        print(f"  {tok:20} {sorted(forms[tok])}  {reasons[0]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dictionary", type=Path, help="hunspell .dic file to sweep")
    args = parser.parse_args(argv)

    english_hits = [(w, p, guard.flag_text(p)) for w, p in ENGLISH_CASES]
    english_hits = [(w, p, r) for w, p, r in english_hits if r]
    print(f"English words still flagged: {len(english_hits)}/{len(ENGLISH_CASES)}")
    for word, phrase, reasons in english_hits:
        print(f"  {word!r} in {phrase!r}: {reasons}")

    german = GERMAN_TAIL_WITNESSES + GERMAN_HEIT_NOUNS
    missed = [n for n in german if not guard.flag_text(n)]
    print(f"German nouns no longer caught (recall regression): {len(missed)}/{len(german)}")
    for noun in missed:
        print(f"  {noun}")

    if args.dictionary:
        sweep(args.dictionary)

    ok = not english_hits and not missed
    print(f"\nguard accepts all seven English words: {not english_hits}")
    print(f"guard still rejects every German noun: {not missed}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
