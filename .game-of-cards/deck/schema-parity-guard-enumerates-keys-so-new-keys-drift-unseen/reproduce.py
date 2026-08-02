#!/usr/bin/env python3
"""The schema-parity guard only compares an enumerated key list.

`tests/test_skill_schema_yaml_parity.py` claims in its module docstring that
"Drift in either file fails the test". It actually compares six named keys
(`schema_version`, `required_fields`, `optional_fields`, `title_pattern`,
`canonical_tags`, `human_gate_default`) plus every key whose name ends in
`_values`. Any other top-level key can differ between `goc/schema.yaml` and
`goc/templates/skills/card-schema/schema.yaml` in either direction while the
whole suite stays green.

This probe runs the REAL guard class against temp schema pairs: two controls
that must be caught, and two drift cases the guard cannot see.

Run: `uv run python .game-of-cards/deck/<title>/reproduce.py`
Exit 0 once the guard catches drift on every top-level key.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
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

GUARD_FILE = ROOT / "tests" / "test_skill_schema_yaml_parity.py"
ENGINE_SCHEMA = ROOT / "goc" / "schema.yaml"
SKILL_SCHEMA = ROOT / "goc" / "templates" / "skills" / "card-schema" / "schema.yaml"

# A realistic next schema extension. The open card
# `schema-yaml-omits-closed-at-conditional-requirement-for-terminal-status`
# proposes exactly this shape: a table of conditionally-required fields.
NEW_KEY_BLOCK = (
    'required_when:\n  closed_at: "status in [done, disproved, superseded]"\n'
)


def _load_guard():
    """Import the guard module by path — `tests/` ships no `__init__.py`."""
    spec = importlib.util.spec_from_file_location("_goc_schema_parity_guard", GUARD_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def guard_passes(engine_text: str, skill_text: str) -> bool:
    """Run the real guard class against a temp schema pair; True if it stays green."""
    guard = _load_guard()
    with tempfile.TemporaryDirectory() as tmp:
        engine_path = Path(tmp) / "engine.yaml"
        skill_path = Path(tmp) / "skill.yaml"
        engine_path.write_text(engine_text, encoding="utf-8")
        skill_path.write_text(skill_text, encoding="utf-8")
        # `_assert_equal` builds its message with `relative_to(ROOT)` eagerly —
        # on passing calls too — so ROOT must move with the schema paths, or
        # every test errors out and this probe misreads every drift as caught.
        guard.ENGINE_SCHEMA = engine_path
        guard.SKILL_SCHEMA = skill_path
        guard.ROOT = Path(tmp)
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(
            guard.SkillSchemaParityTest
        )
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return result.wasSuccessful()


def main() -> int:
    engine_text = ENGINE_SCHEMA.read_text(encoding="utf-8")
    skill_text = SKILL_SCHEMA.read_text(encoding="utf-8")

    print(f"engine schema: {ENGINE_SCHEMA.relative_to(ROOT)}")
    print(f"skill  schema: {SKILL_SCHEMA.relative_to(ROOT)}")
    print(f"byte-identical today: {engine_text == skill_text}")
    print()

    findings: list[str] = []

    # Control A — a covered key (`status_values`) must be caught.
    drifted = engine_text.replace(
        "status_values:        [open, active, blocked, done",
        "status_values:        [open, active, done",
    )
    assert drifted != engine_text, "control A mutation did not apply"
    passed = guard_passes(drifted, skill_text)
    print(f"[control] drop 'blocked' from status_values   -> guard green: {passed}")
    if passed:
        findings.append("control A failed: covered-key drift went unnoticed")

    # Control B — `canonical_tags` is covered in the reverse direction too.
    drifted = skill_text.replace("  - bug\n", "  - bug\n  - phantom-tag\n")
    assert drifted != skill_text, "control B mutation did not apply"
    passed = guard_passes(engine_text, drifted)
    print(f"[control] extra canonical tag in skill copy   -> guard green: {passed}")
    if passed:
        findings.append("control B failed: canonical_tags drift went unnoticed")

    # Case 1 — a NEW top-level key added to the engine schema only.
    passed = guard_passes(engine_text + NEW_KEY_BLOCK, skill_text)
    print(f"[case 1]  new key 'required_when', engine only -> guard green: {passed}")
    if passed:
        findings.append("engine-only key 'required_when' is invisible to the guard")

    # Case 2 — the same key added to the skill copy only.
    passed = guard_passes(engine_text, skill_text + NEW_KEY_BLOCK)
    print(f"[case 2]  new key 'required_when', skill only  -> guard green: {passed}")
    if passed:
        findings.append("skill-only key 'required_when' is invisible to the guard")

    print()
    if findings:
        print(f"DEFECT: {len(findings)} drift(s) the guard cannot see:")
        for finding in findings:
            print(f"  - {finding}")
        print()
        print(
            "The guard's docstring claims 'Drift in either file fails the test'. "
            "It enumerates six keys plus `*_values`; every other top-level key "
            "is unguarded in both directions."
        )
        return 1

    print("OK — the parity guard catches drift on every top-level key.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
