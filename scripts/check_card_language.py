#!/usr/bin/env python3
"""Repo-local guard for AGENTS.md § "Card authoring rules" — the English-only rule.

AGENTS.md requires every card in this repo to be written in English, because
cards are read cold by future agents and contributors who may not share the
language of the conversation that motivated them. Nothing enforced that rule:
`goc new`, `goc move` and `goc quality-pass` all route through
`engine._check_title_antipatterns`, whose eight `TITLE_ANTIPATTERNS` are jargon
shapes and character classes. A well-formed lower-kebab ASCII slug in German is
indistinguishable from one in English to that predicate, which is how
`openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session` sat in the deck
for nine days while `goc quality-pass` reported "Title antipatterns: clean".

## Why this lives in `scripts/`, not in the engine

English-only is *this repo's* authoring convention, not goc semantics. A team
running goc on a German codebase is entitled to a German deck. Putting a
language rule in `TITLE_ANTIPATTERNS` would ship that policy to every consumer;
putting it behind an opt-in config key would add a consumer-facing surface for
a one-instance project-local rule. So the guard is repo-local: no engine
change, no template, no plugin mirror. It is enforced from the regression suite
(`tests/test_card_authoring_rules.py`), which runs in CI on every push — so a
non-English card fails the build on the commit that files it rather than
waiting for somebody to happen to read it.

## What it checks, and what it deliberately does not

Scanned fields: `title`, `summary` and `definition_of_done` — the three
authored-prose frontmatter fields. Card *bodies* are excluded on purpose: they
legitimately quote non-English identifiers, upstream error strings, and (in
several cards) the historical offending title itself, so scanning them would
report the deck's own record of this bug as a violation.

Detection is **precision-first**, in two layers:

1. `MARKER_WORDS` — words that are common in another European language and are
   not English words, English acronyms, or technical tokens. Ambiguous
   homographs are deliberately absent: German `die`/`war`/`hat`/`tag`/`fast`,
   Spanish `con`/`sin`/`todo`, Italian `per`/`non`/`come`, French `pour`/`sans`
   and Portuguese `com` all read as ordinary English in a card and are NOT
   markers.
2. `MARKER_SUFFIXES` — German derivational endings with no English collision.
   Slug titles drop articles, so a purely content-word slug like the historical
   offender carries no function words at all; the suffix layer is what catches
   the nouns and verbs a function-word list alone would miss.

The price of precision is recall: a non-English title built entirely from
cognates ("konfiguration-migration-problem") can still slip through. This guard
raises the floor from "nothing checks" to "the realistic cases fail CI"; it is
not a language classifier and does not claim to be.

Usage:
    python scripts/check_card_language.py           # report findings
    python scripts/check_card_language.py --check   # exit 1 on any finding
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from goc.engine import parse_frontmatter  # noqa: E402

DECK_DIR = ROOT / ".game-of-cards" / "deck"

# Frontmatter fields that must be English prose. Bodies are excluded — see the
# module docstring.
SCANNED_FIELDS = ("title", "summary", "definition_of_done")

# Words common in another European language that are NOT English words, English
# acronyms, or technical tokens. Every entry is a claim that its appearance in a
# card is a language slip and never legitimate English — homographs belong in
# the docstring's exclusion list, not here.
MARKER_WORDS_BY_LANGUAGE = {
    "German": """
        und oder nicht kein keine keinen keiner auch noch schon sehr mehr
        mehrfach mehrere immer wieder ohne gegen zwischen durch nach beim zum
        zur vom eine einen einem eines sind waren wird werden wurde wurden
        haben hatte hatten kann koennen muss muessen soll sollen sollte darf
        duerfen sich seine ihre unser unsere jeder jede jedes alle alles etwas
        nichts hier dort wenn weil dass damit sondern aber bereits jetzt dabei
        deshalb trotzdem jedoch sowie erzwingen erzwingt fehler fehlt fehlen
        funktioniert ueber unter aendern loeschen erstellen anzeigen pruefen
        aufrufen ausgeben schreiben lesen zeigen machen geben nehmen bleiben
        gehen kommen sehen wissen sagen neue neuen neuer alte alten grosse
        kleine schnell langsam richtig falsch moeglich notwendig wichtig
    """,
    "French": """
        les des une dans avec mais tout tous toute toutes cette ces sont etre
        avoir faire peut doit quand parce ainsi aussi alors chaque aucun leur
        notre votre celui comme toujours jamais rien quelque plusieurs erreur
        fichier nouveau ancien
    """,
    "Spanish or Portuguese": """
        los las una unos unas para por pero sobre entre cuando donde porque
        siempre nunca cada algo nada muy este esta esto esos aquel hacer tiene
        tienen puede pueden debe deben archivo arquivo fallo erro nuevo nueva
        novo antiguo despues tambien uma nao tudo
    """,
    "Italian": """
        gli della delle degli nella sono essere questo questa quello anche
        perche sempre ogni tutto tutti niente molto errore
    """,
    "Dutch": """
        het een niet maar ook deze zijn worden wordt moet kunnen geen veel
        altijd nooit elke fout bestand nieuw
    """,
}

MARKER_WORDS = {
    word: language
    for language, block in MARKER_WORDS_BY_LANGUAGE.items()
    for word in block.split()
}

# German derivational endings with no English collision. Measured against every
# distinct token in the deck's scanned fields: zero matches. The length floor
# keeps short English words ("sung", "rung", "flung") out of reach of `-ung`.
MARKER_SUFFIXES = ("ungen", "ierung", "ung", "keit", "heit", "schaft", "lich", "isch", "ieren")
MIN_SUFFIX_TOKEN_LEN = 6

# The English words long enough to clear the length floor and still end in a
# marker suffix. All of them are `-ung`; the other eight endings have no English
# collision at any length.
SUFFIX_EXCEPTIONS = frozenset({"unsung", "unsprung", "unstrung", "restrung", "highstrung"})

_TOKEN_RE = re.compile(r"[a-z]+")


def flag_text(text: str) -> list[str]:
    """Return sorted reasons why `text` looks non-English; empty if it reads clean."""
    if not text:
        return []
    reasons: set[str] = set()
    for token in _TOKEN_RE.findall(text.lower()):
        language = MARKER_WORDS.get(token)
        if language:
            reasons.add(f"{language} marker word {token!r}")
            continue
        if len(token) < MIN_SUFFIX_TOKEN_LEN or token in SUFFIX_EXCEPTIONS:
            continue
        for suffix in MARKER_SUFFIXES:
            if token.endswith(suffix):
                reasons.add(f"German '-{suffix}' ending on token {token!r}")
                break
    return sorted(reasons)


def scan_card(readme: Path) -> list[tuple[str, str]]:
    """Return `(field, reason)` pairs for one card README."""
    frontmatter, _body = parse_frontmatter(readme.read_text(encoding="utf-8"))
    # The directory name is the title of record; fall back to it so a card whose
    # frontmatter the parser cannot read is still checked on its slug.
    frontmatter.setdefault("title", readme.parent.name)
    findings: list[tuple[str, str]] = []
    for field in SCANNED_FIELDS:
        value = frontmatter.get(field)
        if not isinstance(value, str):
            continue
        findings.extend((field, reason) for reason in flag_text(value))
    return findings


def scan_deck(deck_dir: Path = DECK_DIR) -> list[tuple[str, str, str]]:
    """Return `(card, field, reason)` triples for every non-English finding."""
    return [
        (readme.parent.name, field, reason)
        for readme in sorted(deck_dir.glob("*/README.md"))
        for field, reason in scan_card(readme)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 on any finding")
    args = parser.parse_args(argv)

    scanned = len(list(DECK_DIR.glob("*/README.md")))
    findings = scan_deck()
    if not findings:
        print(f"English-only: clean ({scanned} cards scanned)")
        return 0
    for card, field, reason in findings:
        print(f"{card}: {field}: {reason}")
    sys.stdout.flush()  # keep the findings above the summary when both are piped
    print(
        f"\n{len(findings)} finding(s). AGENTS.md § 'Card authoring rules' requires "
        "English titles, summaries and DoD items — cards are read cold by people who "
        "do not share the language of the conversation that motivated them.",
        file=sys.stderr,
    )
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
