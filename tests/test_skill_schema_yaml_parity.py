"""Regression guard: card-schema skill's bundled schema.yaml matches the engine schema.

`goc/schema.yaml` is the authoritative card schema loaded at runtime by
`engine.load_schema()`. The card-schema skill ships a sibling copy at
`goc/templates/skills/card-schema/schema.yaml` so cold readers (humans
and agents) consulting the skill see the same field list, enum values,
and canonical tags the runtime actually enforces.

Plugin-mirror parity (`engine.validate_plugin_mirror_parity`) already
guards the four downstream mirrors against the template; this test
closes the remaining gap between the template and the engine's
authoritative copy. Drift in either file fails the test.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc._vendor.yaml_lite import safe_load  # noqa: E402

ENGINE_SCHEMA = ROOT / "goc" / "schema.yaml"
SKILL_SCHEMA = ROOT / "goc" / "templates" / "skills" / "card-schema" / "schema.yaml"


class SkillSchemaParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = safe_load(ENGINE_SCHEMA.read_text(encoding="utf-8"))
        cls.skill = safe_load(SKILL_SCHEMA.read_text(encoding="utf-8"))

    def _assert_equal(self, key: str) -> None:
        self.assertEqual(
            self.engine.get(key),
            self.skill.get(key),
            f"{key} drift between {ENGINE_SCHEMA.relative_to(ROOT)} "
            f"and {SKILL_SCHEMA.relative_to(ROOT)}",
        )

    def test_schema_version(self) -> None:
        self._assert_equal("schema_version")

    def test_required_fields(self) -> None:
        self._assert_equal("required_fields")

    def test_optional_fields(self) -> None:
        self._assert_equal("optional_fields")

    def test_title_pattern(self) -> None:
        self._assert_equal("title_pattern")

    def test_canonical_tags(self) -> None:
        self._assert_equal("canonical_tags")

    def test_human_gate_default(self) -> None:
        self._assert_equal("human_gate_default")

    def test_all_enum_value_lists(self) -> None:
        engine_enum_keys = {k for k in self.engine if k.endswith("_values")}
        skill_enum_keys = {k for k in self.skill if k.endswith("_values")}
        self.assertEqual(
            engine_enum_keys,
            skill_enum_keys,
            "set of *_values enum keys diverges between engine and skill schema",
        )
        for key in sorted(engine_enum_keys):
            self._assert_equal(key)


if __name__ == "__main__":
    unittest.main()
