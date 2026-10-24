"""Regression guard: refine-deck re-checks parked cards against moved code.

A card at `human_gate: decision` is a claim about code, held until a human
reads it, and nothing used to re-evaluate the claim while it waited. Two
parked cards on this project's deck went on asserting a `goc --waiting`
defect for 61 days after a third card's fix had removed it, and nothing
surfaced them on purpose (card
`parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them`).

The decided remedy is a refine-deck category, so this guard pins two things.

The CONTRACT in the shipped core skill. The category must run before the
citation repair, because a repair moves numbers onto lines that exist and
erases the signal. It must anchor as filed. And it must re-run the
reproducer before writing anything, re-anchoring a live defect rather than
proposing it for retirement: a 2026-10-22 re-measurement found 37 of 38
anchor-stale gated cards still live, so an absent anchor alone would have
retired 37 real bug reports.

The SCAN, as shipped in the reference sibling, run against a fixture repo.
An empty candidate list reads the same whether nothing is stale or nothing
was scanned, so the fixture carries a known offender the scan must catch
beside a clean case it must clear. It also carries the case that decided
the anchoring rule, a card whose cite a repair pass already moved onto a
line that exists: anchored at its last write it reads as clean, anchored as
filed it is caught.
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
SKILL = ROOT / "goc" / "templates" / "skills" / "refine-deck" / "SKILL.md"
REFERENCE = ROOT / "goc" / "templates" / "skills" / "refine-deck" / "reference.md"


def _flat(text: str) -> str:
    """Collapse hard-wrapped prose so a phrase split by a line break still matches."""
    return re.sub(r"\s+", " ", text).lower()


def _section(text: str, heading: str, level: str) -> str:
    """One section, up to the next heading of its level or above.

    Fence-aware: the shipped scan carries `# ...` comments and the entry
    template a `## <ts> — Staleness re-check` line, neither a heading.
    """
    lines = text.split("\n")
    if f"{level} {heading}" not in lines:
        raise AssertionError(f"no '{level} {heading}' section")
    out, fence = [], False
    for line in lines[lines.index(f"{level} {heading}"):]:
        if out and not fence and re.match(rf"#{{1,{len(level)}}} \S", line):
            break
        if line.startswith("```"):
            fence = not fence
        out.append(line)
    return "\n".join(out)


def stale_parks_section() -> str:
    return _section(SKILL.read_text(encoding="utf-8"), "Stale parks (gated cards)", "###")


def shipped_scan() -> str:
    """The scan script exactly as the reference sibling ships it."""
    section = _section(REFERENCE.read_text(encoding="utf-8"), "Stale-parks scan", "##")
    match = re.search(r"<<'EOF'\n(.*?)\nEOF\n", section, re.S)
    if match is None:
        raise AssertionError("reference.md § Stale-parks scan no longer ships a heredoc scan")
    return match.group(1)


class StaleParksContractTest(unittest.TestCase):
    def test_category_runs_before_the_citation_repair(self) -> None:
        body = SKILL.read_text(encoding="utf-8")
        stale = body.find("### Stale parks (gated cards)")
        repair = body.find("### Defunct file:line citations")
        self.assertNotEqual(-1, stale, "refine-deck SKILL.md lost its stale-parks category")
        self.assertNotEqual(-1, repair, "refine-deck SKILL.md lost its citation repair")
        self.assertLess(
            stale, repair,
            "the stale-parks scan must precede the citation repair: the repair "
            "relocates numbers onto lines that exist and erases the signal",
        )
        self.assertIn("before the citation repair", _flat(stale_parks_section()))

    def test_category_anchors_as_filed(self) -> None:
        flat = _flat(stale_parks_section())
        self.assertIn("filing commit", flat)
        self.assertIn("human_gate", flat)
        self.assertIn("§ stale-parks scan", flat)

    def test_reproducer_runs_first_and_nothing_is_retired(self) -> None:
        flat = _flat(stale_parks_section())
        for phrase in (
            "a vanished anchor is not evidence of a fix",
            "re-run its `reproduce.py` first",
            "still reproduces → re-anchor its cites",
            "## <ts> — staleness re-check",
            "no longer reproduces → append that entry",
            "leave the card at its gate",
            "crashes, or none exists",
            "report the card for a human re-read",
            "never treat it as fixed",
            "never lower a gate",
        ):
            self.assertIn(phrase, flat, f"stale-parks category no longer states: {phrase!r}")

    def test_category_commits_before_the_repair_walk(self) -> None:
        flat = _flat(stale_parks_section())
        self.assertIn("commit before the repair below", flat)
        self.assertIn("git log", flat)

    def test_reference_routes_and_orders_the_long_form(self) -> None:
        self.assertIn("| Stale-parks scan |", SKILL.read_text(encoding="utf-8"))
        reference = REFERENCE.read_text(encoding="utf-8")
        self.assertLess(
            reference.find("## Stale-parks scan"),
            reference.find("## Citation anchor check"),
        )
        flat = _flat(_section(reference, "Stale-parks scan", "##"))
        self.assertIn("every candidate gets the entry", flat)
        self.assertIn("do not lower the gate", flat)


class StaleParksScanTest(unittest.TestCase):
    """Run the shipped scan over a fixture deck with known offenders."""

    DOOMED = "def doomed_helper_that_gets_removed(value):"
    SURVIVOR = "def surviving_helper_that_moves(value):"
    GONE_FILE = "def entry_point_of_a_deleted_module():"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.com")
        self.git("config", "user.name", "fixture")
        self.git("config", "commit.gpgsign", "false")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        env = {**os.environ, "PRE_COMMIT_ALLOW_NO_CONFIG": "1"}
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True,
            text=True, env=env,
        ).stdout

    def write(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def card(self, title: str, gate: str, cite: str) -> None:
        self.write(
            f".game-of-cards/deck/{title}/README.md",
            "---\n"
            f"title: {title}\n"
            'summary: "fixture card"\n'
            "status: open\n"
            "stage: null\n"
            "contribution: medium\n"
            'created: "2026-10-01T00:00:00Z"\n'
            "closed_at: null\n"
            f"human_gate: {gate}\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [ ] fixture\n"
            "---\n\n"
            f"# {title}\n\n`{cite}` is the code this card is about.\n",
        )

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def run_scan(self) -> str:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT) + (
            os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
        )
        cards = subprocess.run(
            [sys.executable, "-m", "goc.cli", "--status", "all", "--json"],
            cwd=self.repo, check=True, capture_output=True, text=True, env=env,
        ).stdout
        self.write("cards.json", cards)
        return subprocess.run(
            [sys.executable, "-", str(self.repo / "cards.json")],
            input=shipped_scan(), cwd=self.repo, check=True,
            capture_output=True, text=True,
        ).stdout

    def test_scan_catches_offenders_and_clears_the_clean_case(self) -> None:
        self.write(
            "src/widget.py",
            f"import os\n\n{self.DOOMED}\n    return value\n\n{self.SURVIVOR}\n"
            "    return value * 2\n",
        )
        self.write("src/legacy.py", f"{self.GONE_FILE}\n    pass\n")
        self.card("stale-card", "decision", "src/widget.py:3")
        self.card("clean-card", "decision", "widget.py:6")
        self.card("rechecked-card", "decision", "src/widget.py:3")
        self.write(
            ".game-of-cards/deck/rechecked-card/log.md",
            "## 2026-10-24T00:00:00Z — Staleness re-check\n\nVerdict: still live.\n",
        )
        self.card("ungated-card", "none", "src/widget.py:3")
        self.card("repaired-card", "decision", "src/widget.py:3")
        self.card("deleted-file-card", "session", "src/legacy.py:1")
        self.commit("file the cards")

        # Later work removes the doomed helper, pushes the survivor down by
        # three lines and deletes a module outright.
        self.write(
            "src/widget.py",
            "import os\nimport re\nimport sys\n\nPATTERN = re.compile('x')\n\n"
            f"{self.SURVIVOR}\n    return value * 2\n",
        )
        (self.repo / "src" / "legacy.py").unlink()
        self.commit("refactor widget, drop legacy")

        # A citation repair pass moves repaired-card's number onto a line
        # that exists. Anchored at that last write the cite looks current.
        readme = self.repo / ".game-of-cards/deck/repaired-card/README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8").replace("src/widget.py:3", "src/widget.py:7"),
            encoding="utf-8",
        )
        self.commit("hygiene pass: repair drifted cites")
        head_line = (self.repo / "src/widget.py").read_text(encoding="utf-8").split("\n")[6]
        self.assertEqual(self.SURVIVOR, head_line, "fixture: the repaired cite must resolve")

        out = self.run_scan()
        flagged = set(re.findall(r"^([a-z0-9-]+)  \[", out, re.M))
        self.assertEqual(
            {"stale-card", "repaired-card", "deleted-file-card"}, flagged,
            f"shipped stale-parks scan flagged the wrong cards:\n{out}",
        )
        self.assertIn("(1 already re-checked, skipped)", out)
        checked = int(re.search(r"as-filed anchors checked: (\d+)", out).group(1))
        self.assertGreaterEqual(checked, 4, f"the scan did not actually scan:\n{out}")
        self.assertIn(repr(self.DOOMED), out)


if __name__ == "__main__":
    unittest.main()
