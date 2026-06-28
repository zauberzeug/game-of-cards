"""Regression guard: every optional field is documented in the card-schema skill body.

The `card-schema` skill advertises itself as the canonical reference for
field semantics, and its bundled `schema.yaml` declares the authoritative
list of optional fields. This test closes the class of bug where a field
is declared in the schema but left undocumented in the SKILL.md body
(the original gap was `worker`, which had a schema entry and a full engine
implementation but no field-reference section).

A bare word-grep is too weak: an incidental prose mention (e.g. "an
autonomous pull-card worker halts") would mask a missing field-reference
section. So "documented" here means the field appears in a Markdown
*heading* or as a *leading backticked definition* (`field` at the start
of a line or bullet) — the shape every real optional-field section uses,
and the shape the incidental prose line does not.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc._vendor.yaml_lite import safe_load  # noqa: E402

SKILL_DIR = ROOT / "goc" / "templates" / "skills" / "card-schema"
SKILL_BODY = SKILL_DIR / "SKILL.md"
SKILL_SCHEMA = SKILL_DIR / "schema.yaml"


def _is_documented(field: str, lines: list[str]) -> bool:
    """A field is documented if it anchors a heading or a leading backticked definition."""
    token = re.escape(field)
    heading = re.compile(rf"^#{{1,4}}\s+.*\b{token}\b", re.IGNORECASE)
    definition = re.compile(rf"^[-*]?\s*`{token}`")
    return any(heading.search(line) or definition.search(line) for line in lines)


class SkillDocumentsOptionalFieldsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.optional_fields = safe_load(SKILL_SCHEMA.read_text(encoding="utf-8")).get(
            "optional_fields", []
        )
        cls.lines = SKILL_BODY.read_text(encoding="utf-8").splitlines()

    def test_optional_fields_present(self) -> None:
        self.assertTrue(self.optional_fields, "schema.yaml declares no optional_fields")

    def test_every_optional_field_documented(self) -> None:
        undocumented = [f for f in self.optional_fields if not _is_documented(f, self.lines)]
        self.assertEqual(
            undocumented,
            [],
            f"optional field(s) declared in {SKILL_SCHEMA.relative_to(ROOT)} but lacking a "
            f"field-reference heading or definition in {SKILL_BODY.relative_to(ROOT)}: "
            f"{undocumented}",
        )


if __name__ == "__main__":
    unittest.main()
