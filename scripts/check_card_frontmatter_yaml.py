#!/usr/bin/env python3
"""Repo-local guard: every card's frontmatter must be readable by a strict YAML parser.

`goc/templates/skills/kickoff/SKILL.md` has the agent tell every new consuming
repo, verbatim, that "each card is a plain Markdown file with YAML frontmatter".
Nothing enforced the YAML half of that claim. goc reads cards through
`goc/_vendor/yaml_lite.py`, a parser deliberately scoped as "a superset of what
`emit_frontmatter` produces" (`replace-pyyaml-with-vendored-parser`), and
`engine.validate_card` checks parsed field *values* — enum membership, edge
symmetry, date shape — never whether the block it was handed is legal YAML. So
two hand-authored cards sat in this repo's deck reporting `OK` under
`goc validate` while PyYAML refused both outright.

## Why this lives in `scripts/`, not in the engine

`goc validate` ships to consumers, and a strict-YAML check inside it would need
a strict YAML parser — the dependency `drop-third-party-runtime-dependencies-from-goc`
deliberately removed and which `yaml_lite` exists to replace. Tightening
`yaml_lite` itself is a different question with a migration cost: it changes the
acceptance set every existing consumer deck is already parsed under.

So the guard is repo-local, matching how this repo settled the same placement
question twice before — `tests/test_skill_frontmatter_strict_yaml.py` for skill
frontmatter, and `scripts/check_card_language.py` for the English-only card
rule. Both enforced from the regression suite, neither shipped to a consumer.
This one follows `check_card_language.py`'s shape: standalone-runnable,
imported by `tests/test_card_frontmatter_yaml.py`, and wired into
`.pre-commit-config.yaml` so it fires on the filing path rather than only on
push.

## What it checks

Three hazard shapes, all specific to an **unquoted (plain) scalar** — the only
value form a hand-editor produces by accident, and the form both real offenders
took:

1. `NESTED_MAPPING_COLON` — a plain scalar containing `: ` (or ending in `:`).
   YAML reads the colon as a nested mapping key and refuses with
   `mapping values are not allowed here`. This is the shape that broke shipped
   `SKILL.md` frontmatter in `skill-frontmatter-descriptions-break-yaml-loading`.
2. `LEADING_INDICATORS` — a plain scalar opening with a YAML indicator
   character. `` ` `` and `@` are *reserved* and can never start a plain scalar
   (`found character '`' that cannot start any token`); the rest silently
   re-type the value as an anchor, alias, tag, comment, flow collection, or
   block scalar. `-`, `?` and `:` are indicators only when followed by a
   space — `-v` and `?query` are ordinary scalars — so they are checked
   separately. Both sets are imported from `goc.engine`, which derives them
   from YAML 1.2 §5.3's closed `c-indicator` list and consults the same sets
   when `emit_frontmatter` decides to quote — so this guard cannot ask for a
   form the emitter refuses to write.
3. A plain scalar containing a TAB. YAML admits no TAB anywhere in a plain
   scalar (`while scanning for the next token`), and a double-quoted scalar
   carries it through unchanged, so quoting is the fix here too.

A value that already opens with `"`, `'`, `[` or `{` is quoted or flow-structured
and is left alone: its legality is a question about quoting, which
`tests/test_skill_frontmatter_strict_yaml.py` covers on its own surface, and
including it here would flag every correctly-quoted summary in the deck.

`|` and `>` are exempt only as a *complete* block header — `|`, `>-`, `|2+` and
their peers — recognized by reusing the engine's own `_YAML_BLOCK_HEADER_RE`
rather than restating it, so the two cannot drift. Anything else after the
indicator (`summary: |block`) is not a header and YAML refuses it, so it falls
through to the indicator check like any other plain scalar.

Detection is calibrated, not asserted. The card's `reproduce.py` runs this
detector and PyYAML side by side over the whole deck and prints the
false-positive and false-negative sets; both were empty across 722 cards. That
cross-check is what lets a dependency-free guard stand in for a YAML parser.

Only top-level `key: value` lines are examined. Indented lines are block-scalar
or block-sequence continuations whose content is opaque to YAML's scalar rules,
and a `#` line is a comment.

Usage:
    python scripts/check_card_frontmatter_yaml.py           # report findings
    python scripts/check_card_frontmatter_yaml.py --check   # exit 1 on any finding
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from goc.engine import (  # noqa: E402
    FRONTMATTER_RE,
    _YAML_BLOCK_HEADER_RE,
    _YAML_INDICATOR_FIRST,
    _YAML_SPACE_BOUND_INDICATORS,
)

DECK_DIR = ROOT / ".game-of-cards" / "deck"

#: A plain scalar may not contain `: ` — nor end in a bare `:`.
NESTED_MAPPING_COLON = re.compile(r":(?:[ \t]|$)")

#: Indicator characters that are illegal or meaning-changing at position 0 of a
#: plain scalar, whatever follows them — imported from the engine's spec-derived
#: `c-indicator` set rather than restated, so this guard cannot demand a form
#: `emit_frontmatter` does not produce. Restating it is what let the emitter
#: write six shapes this guard rejects
#: (`goc-writes-card-summaries-a-standard-yaml-reader-cannot-parse`).
LEADING_INDICATORS = tuple(sorted(_YAML_INDICATOR_FIRST))

#: Indicators that only bind when followed by a space (or standing alone).
SPACE_BOUND_INDICATORS = tuple(sorted(_YAML_SPACE_BOUND_INDICATORS))

#: Value forms that are already quoted or flow-structured — not plain scalars.
#: `|` / `>` are deliberately absent: they are legal only as a complete block
#: header, which `_YAML_BLOCK_HEADER_RE` recognizes separately.
STRUCTURED_PREFIXES = ('"', "'", "[", "{")


def flag_frontmatter(block: str) -> list[tuple[int, str, str]]:
    """Return `(lineno, key, reason)` for each strict-YAML hazard in `block`.

    `block` is the raw text between the `---` delimiters. Line numbers are
    1-based within that block.
    """
    findings: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(block.splitlines(), start=1):
        if not line or line.startswith((" ", "\t", "#")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith(STRUCTURED_PREFIXES) or value in {"", "null"}:
            continue
        if _YAML_BLOCK_HEADER_RE.match(value):
            continue
        if value.startswith(LEADING_INDICATORS):
            findings.append(
                (lineno, key, f"plain scalar opens with YAML indicator {value[0]!r}")
            )
        elif value in SPACE_BOUND_INDICATORS or value.startswith(
            tuple(f"{c} " for c in SPACE_BOUND_INDICATORS)
        ):
            findings.append(
                (lineno, key, f"plain scalar opens with YAML indicator {value[0]!r}")
            )
        elif NESTED_MAPPING_COLON.search(value):
            findings.append((lineno, key, "plain scalar contains an unquoted ': '"))
        elif "\t" in value:
            findings.append((lineno, key, "plain scalar contains a TAB"))
    return findings


def scan_card(readme: Path) -> list[tuple[int, str, str]]:
    """Return hazards for one card README, or `[]` when it has no frontmatter.

    A file whose opening `---` has no closing delimiter yields no frontmatter
    block to check. That malformation is `goc validate`'s finding — it reports
    it per card and exits 1 — so this guard stays silent on it rather than
    failing the build twice with the wrong diagnostic, the same posture
    `scripts/check_card_language.py` takes.
    """
    match = FRONTMATTER_RE.match(readme.read_text(encoding="utf-8"))
    if not match:
        return []
    return flag_frontmatter(match.group(1) + match.group(2))


def scan_deck(deck_dir: Path = DECK_DIR) -> list[tuple[str, int, str, str]]:
    """Return `(card, lineno, key, reason)` for every hazard in the deck."""
    return [
        (readme.parent.name, lineno, key, reason)
        for readme in sorted(deck_dir.glob("*/README.md"))
        for lineno, key, reason in scan_card(readme)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 on any finding")
    args = parser.parse_args(argv)

    # Both reads resolve `DECK_DIR` at call time. Passing it explicitly rather
    # than leaning on `scan_deck`'s default keeps the count and the scan looking
    # at the same directory — a default argument is bound once at definition, so
    # the two would silently disagree for any caller that repoints the module
    # attribute (a test harness, or this guard's own end-to-end demo).
    scanned = len(list(DECK_DIR.glob("*/README.md")))
    findings = scan_deck(DECK_DIR)
    if not findings:
        print(f"Card frontmatter is strict-YAML clean ({scanned} cards scanned)")
        return 0
    for card, lineno, key, reason in findings:
        print(f"{card}/README.md: frontmatter line {lineno}: {key}: {reason}")
    sys.stdout.flush()  # keep the findings above the summary when both are piped
    print(
        f"\n{len(findings)} finding(s). goc reads cards through its permissive "
        "vendored parser, so these load fine under `goc validate` and fail for "
        "everyone reading the deck with a strict YAML parser. Quote the value, "
        "or re-emit the card through any goc verb: `emit_frontmatter` quotes "
        "every shape this guard flags — it consults the same indicator sets "
        "(`goc.engine._YAML_INDICATOR_FIRST`, `_YAML_SPACE_BOUND_INDICATORS`) "
        "and re-emits the quoted form, so a hand-added quote survives.",
        file=sys.stderr,
    )
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
