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

A card whose frontmatter the parser cannot read (unterminated `---`, a missing
space after a colon, a duplicate key) is warned about on stderr and then
checked on its directory slug — the malformation is `goc validate`'s finding,
not this guard's, and one bad card must not cost every other card's verdict.

Detection is **precision-first**, in two layers:

1. `MARKER_WORDS` — words that are common in another European language and
   that an English engineering card has no reason to use. Homographs a card
   *would* use are deliberately absent: German `die`/`war`/`hat`/`tag`/`fast`,
   Spanish `con`/`sin`/`todo`, Italian `per`/`non`/`come`, French `pour`/`sans`
   and Portuguese `com` all read as ordinary English in a card and are NOT
   markers. So are `algo` (engineering shorthand for algorithm), `nada`, `tout`
   and `nouveau` (the Linux driver for NVIDIA GPUs), which were markers until a
   card showed each one blocking English prose. French/German `des` was removed
   because it lowercases the cipher acronym DES (and 3DES). The criterion is
   register, not the dictionary: some entries are dictionary English too, and
   "Known false positives" below names them.
2. `MARKER_SUFFIXES` — German derivational endings. Slug titles drop articles,
   so a purely content-word slug like the historical offender carries no
   function words at all; the suffix layer is what catches the nouns and verbs
   a function-word list alone would miss. Only `-ung` collides with native
   English, and that side is exempted by *derivation* rather than by
   enumeration — see `ENGLISH_UNG_STEMS`. The other endings meet English only
   in words borrowed from German and in names. One of those is everyday
   English, the temperature scale `fahrenheit`, and it is exempted by exact
   match (`ENGLISH_MARKER_SUFFIX_WORDS`).

Both layers read tokens through `_UMLAUT_FOLD`, which rewrites `ä ö ü ß` as the
ASCII digraphs the German marker block is spelled in, so German written with
umlauts and German written in transliteration get the same verdict.

The price of precision is recall, and two gaps are known:

- A non-English title built entirely from cognates
  ("konfiguration-migration-problem") carries no marker word and no marker
  suffix, so nothing fires. Detecting it needs a language classifier; this is
  not one and does not claim to be.
- The other four languages carry accented characters too (`é à ñ ç ì`) and their
  marker entries are spelled unaccented (`despues`, `porque`, `perche`), so
  `apres` does not match `après`. Folding does not reach them: there is no
  digraph convention to fold *into*, and matching accent-insensitively is a
  different mechanism (NFD plus combining-mark strip). German is this repo's
  actual exposure and the only language with a real incident, so the accented
  spellings of the other four stay out of scope until one slips through.

What this guard does is raise the floor from "nothing checks" to "the realistic
cases fail CI".

## Known false positives

Precision is not total either. Of the 128,165 distinct words hunspell's en_US
dictionary yields with its affix rules applied, the guard flags 47 — every one
of them in these two groups:

- marker entries whose English sense is archaic or specialist (`avoir`, `doit`,
  `muss`, `para`, `seine`, `tutti`), and names a slug splits into a marker
  token (Los Angeles, Las Vegas, the Oder);
- on the suffix layer, German loanwords (`gesundheit`, `gesellschaft`,
  `schlieren`, `weltanschauung`), Germanic names (Heimlich, Nibelung), and
  romanized Asian names ending in `-ung` (Samsung, Kaohsiung, `shantung`).

The reproduce.py of the card
`card-language-guard-still-flags-legitimate-english-its-docstring-rules-out`
re-runs that sweep (`--dictionary /usr/share/hunspell/en_US.dic`).

They stay flagged. The marker entries carry the French, Spanish and Portuguese
recall cases. A loanword or a name has no family to derive an exemption from,
and enumerating names is open-ended. A card that needs one of them in its
English sense is the real false positive that earns the word a place: a
homograph goes into the exclusion list above, a suffixed word into
`ENGLISH_MARKER_SUFFIX_WORDS`.

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

from goc.engine import FrontmatterError, parse_frontmatter  # noqa: E402

DECK_DIR = ROOT / ".game-of-cards" / "deck"

# Frontmatter fields that must be English prose. Bodies are excluded — see the
# module docstring.
SCANNED_FIELDS = ("title", "summary", "definition_of_done")

# Words common in another European language that an English engineering card has
# no reason to use. Every entry is a bet that its appearance in a card is a
# language slip; a homograph that card prose does use belongs in the docstring's
# exclusion list, not here. The bet is on register, not on the dictionary —
# hunspell lists `doit`, `seine` and `tutti`, and `los` opens Los Angeles — and
# the docstring's "Known false positives" names the entries known to lose it.
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
        les une dans avec mais tous toute toutes cette ces sont etre avoir
        faire peut doit quand parce ainsi aussi alors chaque aucun leur notre
        votre celui comme toujours jamais rien quelque plusieurs erreur fichier
        ancien
    """,
    "Spanish or Portuguese": """
        los las una unos unas para por pero sobre entre cuando donde porque
        siempre nunca cada muy este esta esto esos aquel hacer tiene
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

# German derivational endings. Only `-ung` collides with native English, and
# `_is_english_ung_word` handles that side; the other eight meet English only in
# German loanwords and in names (module docstring, "Known false positives"). The
# length floor keeps the shortest English `-ung` words ("sung", "rung", "flung")
# out of reach without needing the stem check at all.
MARKER_SUFFIXES = ("ungen", "ierung", "ung", "keit", "heit", "schaft", "lich", "isch", "ieren")
MIN_SUFFIX_TOKEN_LEN = 6

# English words that end in a marker suffix and belong to no family a rule could
# derive. Matched exactly, never as a tail: German `Unerfahrenheit`
# (inexperience) ends in `fahrenheit`.
ENGLISH_MARKER_SUFFIX_WORDS = frozenset({"fahrenheit"})

# The English side of the `-ung` collision. These are a *family*, not a list: a
# strong-verb participle stem (or `dung`, `lung`, `young`), optionally preceded
# by a prefix or a compounding word. The predecessor guard enumerated members
# instead of deriving the rule, and so exempted `unsprung`, `unstrung`,
# `restrung` and `highstrung` while still flagging `sprung` and `strung` — the
# bare stems those four are built from — plus `unhung`, `unslung`, `resprung`,
# `overhung`, `overstrung`, `outflung` and `upswung`. English has no productive
# `-ung` suffix, so the stem set is closed in a way a word list is not.
#
# The first elements are not closed (`hamstrung`, `underslung`), and only some
# stems can take an arbitrary one. Nine stems also end German `-ung` nouns —
# `Regelung` ends in `lung`, `Änderung` in `rung`, `Lösung` in `sung`,
# `Bildung` in `dung`, `Beziehung` in `hung`, `Leistung` in `stung`,
# `Verzweiflung` in `flung`, `Abwechslung` in `slung`, `Ursprung` in `sprung` —
# so exempting them as a tail would exempt those nouns too. They take only a
# listed first element, and `ENGLISH_UNG_PREFIXES` carries every one hunspell's
# en_US dictionary attests on them. An English compound on an unlisted element
# is still a false positive there; adding the element costs no recall, because
# the remainder must still be an exact stem. The other five,
# `TAIL_SAFE_UNG_STEMS`, end no German noun: one would need a verb stem ending
# in `cl`, `str`, `sw`, `wr` or `yo`, and German has none (an `-ern` verb keeps
# its `e`, as in `Polsterung`). They take any first element, so on them no
# future compound can become a false positive.
ENGLISH_UNG_STEMS = frozenset({
    "hung", "rung", "sung", "dung", "lung", "clung", "flung", "slung",
    "stung", "strung", "sprung", "swung", "wrung", "young",
})
TAIL_SAFE_UNG_STEMS = ("clung", "strung", "swung", "wrung", "young")
ENGLISH_UNG_PREFIXES = ("un", "re", "over", "under", "out", "up", "down", "high", "aqua")


def _is_english_ung_word(token: str) -> bool:
    """True iff `token` is an English `-ung` word rather than a German noun.

    A token ending in a `TAIL_SAFE_UNG_STEMS` stem is English whatever precedes
    the stem. For any other stem, the remainder after an optional prefix must
    be an *exact* member of `ENGLISH_UNG_STEMS`, which is what preserves German
    recall: `Regelung` splits to `re` + `gelung` and `Rechnung` to `re` +
    `chnung`, neither of which is a stem, so both still fire. Only `-ung` has a
    family to derive; `ENGLISH_MARKER_SUFFIX_WORDS` covers the other endings.
    """
    if token in ENGLISH_UNG_STEMS or token.endswith(TAIL_SAFE_UNG_STEMS):
        return True
    return any(
        token.startswith(prefix) and token[len(prefix) :] in ENGLISH_UNG_STEMS
        for prefix in ENGLISH_UNG_PREFIXES
    )

_TOKEN_RE = re.compile(r"[a-z]+")

# German as a German keyboard writes it. `_TOKEN_RE` is `[a-z]+`, so without
# this an umlaut is not merely unmatched — it *separates* tokens and shatters the
# word around it (`prüfen` -> `pr` + `fen`), which matches no marker entry and
# drops the pieces below `MIN_SUFFIX_TOKEN_LEN` so the suffix layer goes quiet
# too. Folding to the ASCII digraphs the German marker block is already written
# in makes one entry cover both spellings; the alternative — widening `_TOKEN_RE`
# and giving every umlaut entry a second spelling — re-enumerates an open family,
# and the entry somebody forgets to double is a silent miss. Applied after
# `.lower()`, so `Ä`/`Ö`/`Ü` need no entries of their own. Precision is safe by
# construction: English carries none of these characters, so folding cannot
# change the shape of an English token.
_UMLAUT_FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def flag_text(text: str) -> list[str]:
    """Return sorted reasons why `text` looks non-English; empty if it reads clean."""
    if not text:
        return []
    reasons: set[str] = set()
    for token in _TOKEN_RE.findall(text.lower().translate(_UMLAUT_FOLD)):
        language = MARKER_WORDS.get(token)
        if language:
            reasons.add(f"{language} marker word {token!r}")
            continue
        if (
            len(token) < MIN_SUFFIX_TOKEN_LEN
            or token in ENGLISH_MARKER_SUFFIX_WORDS
            or _is_english_ung_word(token)
        ):
            continue
        for suffix in MARKER_SUFFIXES:
            if token.endswith(suffix):
                reasons.add(f"German '-{suffix}' ending on token {token!r}")
                break
    return sorted(reasons)


def scan_card(readme: Path) -> list[tuple[str, str]]:
    """Return `(field, reason)` pairs for one card README."""
    try:
        frontmatter, _body = parse_frontmatter(readme.read_text(encoding="utf-8"))
    except FrontmatterError as exc:
        # `parse_frontmatter` returns ({}, text) only for "no opening `---` at
        # all"; when the opener IS there and the document is unparseable it
        # RAISES — an unterminated `---`, `status:open` with no space, a
        # duplicate key. Letting that escape costs this card's slug check AND,
        # because `scan_deck` is one comprehension, every other card's verdict
        # in the same run. Warn and continue, the posture
        # `engine.load_all_cards` takes; the malformation itself belongs to
        # `goc validate`, which reports it per card and exits 1
        # (`engine.validate_deck_directories`). Exit code here stays
        # language-only, so a bad card fails the build once, with the right
        # diagnostic, instead of twice with the wrong one.
        print(f"WARNING: {readme.parent.name}: {exc}", file=sys.stderr)
        frontmatter = {}
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
