"""Regression guard: each plugin README's skill catalogue must describe the
payload that README actually ships.

`claude-plugin/README.md` and `openclaw-plugin/README.md` are the
consumer-facing listings a prospective installer reads in the host's plugin
browser — nothing in the engine, the skill bodies, or the test suite reads
them, so a wrong claim there is only ever caught by a human. Both the skill
table and its `**N skills**` headline restate a fact derived from the
`skills/` tree, and neither payload README is auto-synced
(`scripts/sync_plugin_assets.py` mirrors the *skill directories*, not the
prose about them). So when a new skill ships, the tree grows and the prose
does not.

That is exactly how `claude-plugin/README.md` came to advertise "14 skills"
while shipping 16, omitting `claude-kickoff` (2026-05-09) and `upgrade`
(2026-05-30) — see
`claude-code-plugin-readme-undercounts-its-skills-and-still-requires-uv`.
This test pins the catalogue to the shipped set so the next added skill
turns CI red instead of rotting the listing.

Modelled on `tests/test_readme_hook_catalogue_parity.py`, which does the same
for the deck README's workflow-hook table.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# `| `skill-name` | Purpose |` — first cell of a catalogue table row.
_TABLE_ROW = re.compile(r"^\|\s*`([a-z0-9][a-z0-9-]*)`\s*\|", re.MULTILINE)
_BOLD_COUNT = re.compile(r"\*\*(\d+) skills\*\*")

# Payload README → the skills tree whose contents it describes.
_PAYLOADS = (
    ("claude-plugin", ROOT / "claude-plugin"),
    ("openclaw-plugin", ROOT / "openclaw-plugin"),
)


def _shipped_skills(payload_root: Path) -> set[str]:
    skills_dir = payload_root / "skills"
    return {p.name for p in skills_dir.iterdir() if (p / "SKILL.md").is_file()}


def _catalogued_skills(text: str) -> set[str]:
    """Slugs in the skill table that follows the `**N skills**` headline.

    Scoped to that section rather than the whole file: a payload README may
    carry other backtick-slug tables (OpenClaw documents its registered `goc`
    tool in one), and those rows are not skills.
    """
    match = _BOLD_COUNT.search(text)
    if match is None:
        return set()
    section = text[match.end():]
    end = section.find("\n## ")
    if end != -1:
        section = section[:end]
    return set(_TABLE_ROW.findall(section))


class PluginReadmeSkillCatalogueParityTest(unittest.TestCase):
    def test_catalogue_table_lists_every_shipped_skill(self) -> None:
        for name, payload_root in _PAYLOADS:
            with self.subTest(payload=name):
                shipped = _shipped_skills(payload_root)
                catalogued = _catalogued_skills(
                    (payload_root / "README.md").read_text()
                )
                self.assertEqual(
                    shipped,
                    catalogued,
                    msg=(
                        f"The skill table in {name}/README.md is out of sync with "
                        f"the skills shipped in {name}/skills/. This README is "
                        f"consumer-facing and not auto-synced — update it by hand.\n"
                        f"  shipped but not catalogued: {sorted(shipped - catalogued)}\n"
                        f"  catalogued but not shipped: {sorted(catalogued - shipped)}"
                    ),
                )

    def test_headline_count_matches_shipped_skill_total(self) -> None:
        for name, payload_root in _PAYLOADS:
            with self.subTest(payload=name):
                shipped = _shipped_skills(payload_root)
                text = (payload_root / "README.md").read_text()
                claims = [int(n) for n in _BOLD_COUNT.findall(text)]
                self.assertTrue(
                    claims,
                    msg=(
                        f"{name}/README.md no longer states a `**N skills**` count. "
                        f"Either restore the headline claim or drop this assertion "
                        f"deliberately — silently losing it removes the guard."
                    ),
                )
                for claimed in claims:
                    self.assertEqual(
                        len(shipped),
                        claimed,
                        msg=(
                            f"{name}/README.md advertises **{claimed} skills** but "
                            f"{name}/skills/ ships {len(shipped)}: "
                            f"{sorted(shipped)}"
                        ),
                    )


if __name__ == "__main__":
    unittest.main()
