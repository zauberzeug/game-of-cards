"""Count banners in goc/engine.py must agree with themselves on "1 <noun>".

Regression for two cards. The first,
`deck-count-messages-print-1-cards-instead-of-1-card`, swept seven
`{len(...)} cards` interpolations onto a helper so a one-result view stopped
reading "Quality pass over 1 cards". The second,
`count-banners-outside-the-cards-sweep-print-1-boxes-instead-of-1-box`, found
nine more that the first sweep's scan — `\\{len\\(...\\)\\}\\s+cards?\\b` —
structurally could not express, and therefore neither fixed nor guarded:

1. **A non-card noun** — `boxes`, `titles`, `summaries`, `items`, `lines`.
   `goc done`'s refusal message, the most-read error string in the tool, read
   "1 unchecked DoD boxes".
2. **An adjective between the count and the noun** — `{len(cluster)} blocked
   cards` is a *card* banner the bare-`cards` regex never matched.

So the guard below scans for an interpolation followed by an optional adjective
run and any countable noun, and `GuardCatchesBothMissedClassesTest` pins that
reach: it re-runs the scanner over synthetic source carrying one offender of
each class and asserts the scanner names both. A guard that under-reports is
worse than no guard, because it converts an open defect into a claim of
completeness.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ENGINE_SRC = (ROOT / "goc" / "engine.py").read_text(encoding="utf-8")

# The countable nouns this engine reports on. An explicit vocabulary keeps the
# scan precise — a bare `\w+s` pattern also matches verbs ("has", "contains",
# "differs") and buries the signal in false positives. Extend it when a banner
# starts counting something new.
COUNTABLE_NOUNS = (
    "cards", "titles", "summaries", "boxes", "lines", "items", "files",
    "skills", "checks", "edges", "entries", "warnings", "errors", "hooks",
    "verbs", "tags",
)
# An interpolation, then up to two adjective words, then a plural noun. The
# adjective run is what the first sweep's pattern could not express; the open
# `\{[^{}]+\}` (rather than `\{len\(...\)\}`) is what let `{t.dod_open}` and
# `{applied_count['title']}` slip past it. `card(s)` — the `migrate` paths'
# form — is the other accepted convention and stays allowed.
HARDCODED_PLURAL = re.compile(
    r"\{[^{}]+\}\s+((?:[a-zA-Z][\w-]*\s+){0,2}(?:" + "|".join(COUNTABLE_NOUNS) + r"))\b(?!\(s\))"
)
# An f-string fragment opening a line: `f"`, `rf"`, or a bare continuation `"`.
FRAGMENT_OPEN = re.compile(r'^([rf]{0,2})"')


def logical_lines(source: str) -> list[tuple[int, str]]:
    """Physical lines with implicitly-concatenated string fragments spliced.

    A count and its noun can straddle two fragments of one expression —
    `f"{n} blocked "` on one line, `f"cards rooted here"` on the next. Scanning
    raw physical lines would miss that split the same way the first sweep's
    regex missed an adjective, so fragments are joined and the hit is
    attributed to the line the count sits on. A wrong splice can only ever
    produce a loud false positive, never the silent false negative this guard
    exists to prevent.
    """
    raw = source.splitlines()
    spliced: list[tuple[int, str]] = []
    i = 0
    while i < len(raw):
        text = raw[i].rstrip()
        start = i
        while text.endswith('"') and i + 1 < len(raw):
            match = FRAGMENT_OPEN.match(raw[i + 1].strip())
            if match is None:
                break
            text = text[:-1] + raw[i + 1].strip()[match.end():]
            i += 1
        spliced.append((start + 1, text))
        i += 1
    return spliced


def hardcoded_plural_offenders(source: str, path: str = "goc/engine.py") -> list[str]:
    """Every count banner in `source` whose noun is a hardcoded plural."""
    offenders: list[str] = []
    for lineno, line in logical_lines(source):
        if 'f"' not in line:
            continue
        for match in HARDCODED_PLURAL.finditer(line):
            phrase = match.group(1).strip()
            if "card(s)" in line:
                continue
            offenders.append(f"{path}:{lineno}  [{phrase}]  {line.strip()[:96]}")
    return offenders


CARD = """\
---
title: solo-card
summary: the only card in this scratch deck
status: open
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: []
definition_of_done: |
  - [ ] TDD: criteria
---

# solo-card

Body.
"""

ONE_OPEN_BOX_CARD = CARD.replace("status: open", "status: active").replace(
    "human_gate: decision", "human_gate: none"
)


class PluralTest(unittest.TestCase):
    def test_singular_only_for_exactly_one(self) -> None:
        from goc.engine import _plural

        self.assertEqual("card", _plural(1, "card"))
        for plural in (0, 2, 7, 100):
            self.assertEqual("cards", _plural(plural, "card"))

    def test_plural_defaults_to_bare_s(self) -> None:
        from goc.engine import _plural

        self.assertEqual("title", _plural(1, "title"))
        self.assertEqual("titles", _plural(2, "title"))

    def test_explicit_plural_covers_irregular_nouns(self) -> None:
        from goc.engine import _plural

        self.assertEqual("box", _plural(1, "box", "boxes"))
        self.assertEqual("boxes", _plural(0, "box", "boxes"))
        self.assertEqual("summary", _plural(1, "summary", "summaries"))
        self.assertEqual("summaries", _plural(3, "summary", "summaries"))


class NoHardcodedPluralTest(unittest.TestCase):
    def test_engine_has_no_hardcoded_plural_count_banner(self) -> None:
        offenders = hardcoded_plural_offenders(ENGINE_SRC)
        self.assertEqual(
            [],
            offenders,
            "count banners must pluralize via _plural() (or the `card(s)` "
            "form) so a one-result view reads '1 card':\n" + "\n".join(offenders),
        )


class GuardCatchesBothMissedClassesTest(unittest.TestCase):
    """The falsification proof: the scanner must SEE what the first sweep didn't.

    `NoHardcodedPluralTest` passing is only evidence if the scanner it runs can
    actually fail. These cases reintroduce one offender of each missed class
    and assert the scanner reports it *and names it*.
    """

    def test_non_card_noun_is_caught(self) -> None:
        source = '''
        print(f"ERROR: {title}: {t.dod_open} unchecked DoD boxes; will not mark done")
'''
        offenders = hardcoded_plural_offenders(source)
        self.assertEqual(1, len(offenders), offenders)
        self.assertIn("[unchecked DoD boxes]", offenders[0])
        self.assertIn(":2", offenders[0])

    def test_adjective_between_count_and_noun_is_caught(self) -> None:
        source = '''
        warnings.append(f"{len(cluster)} blocked cards rooted here")
'''
        offenders = hardcoded_plural_offenders(source)
        self.assertEqual(1, len(offenders), offenders)
        self.assertIn("[blocked cards]", offenders[0])

    def test_noun_split_across_string_fragments_is_caught(self) -> None:
        source = '''
        warnings.append(
            f"{len(cluster)} blocked "
            f"cards rooted here"
        )
'''
        offenders = hardcoded_plural_offenders(source)
        self.assertEqual(1, len(offenders), offenders)
        self.assertIn("[blocked cards]", offenders[0])

    def test_pluralized_and_card_s_forms_are_not_flagged(self) -> None:
        source = '''
        print(f"{n} unchecked DoD {_plural(n, 'box', 'boxes')}; will not mark done")
        print(f"{len(cluster)} blocked {_plural(len(cluster), 'card')} rooted here")
        print(f"Applied: {n} {_plural(n, 'title')}, {m} {_plural(m, 'summary', 'summaries')}.")
        print(f"migrated {len(hits)} card(s)")
'''
        self.assertEqual([], hardcoded_plural_offenders(source))


class OneCardDeckOutputTest(unittest.TestCase):
    """End-to-end on the surfaces a human reads when the count is exactly one."""

    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_deck(self, repo: Path, title: str, body: str) -> None:
        card_dir = repo / ".game-of-cards" / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(body, encoding="utf-8")
        (card_dir / "log.md").write_text("", encoding="utf-8")

    def test_single_card_surfaces_read_singular(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_deck(repo, "solo-card", CARD)

            quality = self.run_goc(repo, "quality-pass", "--no-llm")
            triage = self.run_goc(repo, "triage")

        for label, proc in (("quality-pass", quality), ("triage", triage)):
            out = proc.stdout + proc.stderr
            self.assertNotIn("1 cards", out, f"goc {label} printed '1 cards':\n{out}")

        self.assertIn("Quality pass over 1 card (status=open):", quality.stdout)
        self.assertIn("## Waiting on you (gate ≠ none) — 1 card", triage.stdout)

    def test_done_refusal_reads_one_unchecked_dod_box(self) -> None:
        """`goc done`'s refusal is the most-read count banner in the tool."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_deck(repo, "one-open-box", ONE_OPEN_BOX_CARD)

            result = self.run_goc(repo, "done", "one-open-box")

        self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
        self.assertIn("1 unchecked DoD box; will not mark done", result.stderr)
        self.assertNotIn("1 unchecked DoD boxes", result.stderr)


if __name__ == "__main__":
    unittest.main()
