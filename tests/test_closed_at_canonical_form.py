"""Closure verbs write `closed_at` in the same canonical form the emitter would.

`mutate_frontmatter_field` is a raw line-substitution and does not apply YAML
quoting; the closure verbs (`goc done`, `goc done --bundle`,
`goc status X disproved|superseded`) therefore have to wrap their datetime
value in `_yaml_inline` so that the on-disk line is byte-identical to what
`emit_frontmatter` would produce on the next whole-frontmatter rewrite.
Without that wrap, every `goc decide` / `goc migrate-list-style` /
emitter-routed migration silently rewrites the `closed_at` line on every
closed card it touches, inflating diffs and hiding real changes.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc.engine import emit_frontmatter, parse_frontmatter  # noqa: E402


def _closed_at_line(readme: Path) -> str:
    for line in readme.read_text().splitlines():
        if line.startswith("closed_at:"):
            return line
    raise AssertionError(f"no closed_at line in {readme}")


def _emitter_closed_at_line(readme: Path) -> str:
    """What `emit_frontmatter` would emit for this card's closed_at value."""
    fm, body = parse_frontmatter(readme.read_text())
    reemitted = emit_frontmatter(fm, body=body)
    for line in reemitted.splitlines():
        if line.startswith("closed_at:"):
            return line
    raise AssertionError(f"emit_frontmatter produced no closed_at line for {readme}")


class ClosedAtCanonicalFormTest(unittest.TestCase):
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

    def write_card(self, cwd: Path, title: str, *, status: str = "active") -> Path:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            f"status: {status}\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-05-01\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [x] item\n"
            "---\n\n"
            f"# {title}\n"
        )
        (card_dir / "log.md").write_text("")
        return card_dir

    def test_done_writes_closed_at_matching_emitter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            card = self.write_card(cwd, "card-a")
            result = self.run_goc(cwd, "done", "card-a")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            readme = card / "README.md"
            self.assertEqual(_closed_at_line(readme), _emitter_closed_at_line(readme))

    def test_done_bundle_writes_closed_at_matching_emitter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            card_a = self.write_card(cwd, "card-a")
            card_b = self.write_card(cwd, "card-b")
            result = self.run_goc(cwd, "done", "--bundle", "card-a", "card-b")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            for card in (card_a, card_b):
                readme = card / "README.md"
                self.assertEqual(_closed_at_line(readme), _emitter_closed_at_line(readme))

    def test_status_disproved_writes_closed_at_matching_emitter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            card = self.write_card(cwd, "card-a", status="open")
            result = self.run_goc(cwd, "status", "card-a", "disproved")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            readme = card / "README.md"
            self.assertEqual(_closed_at_line(readme), _emitter_closed_at_line(readme))

    def test_status_superseded_writes_closed_at_matching_emitter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            old = self.write_card(cwd, "old-card", status="open")
            self.write_card(cwd, "new-card", status="open")
            result = self.run_goc(
                cwd, "status", "old-card", "superseded", "--by", "new-card"
            )
            self.assertEqual(0, result.returncode, msg=result.stderr)
            readme = old / "README.md"
            self.assertEqual(_closed_at_line(readme), _emitter_closed_at_line(readme))


if __name__ == "__main__":
    unittest.main()
