"""The standup skill's Section 2 Context block must span the same status
scope the engine's impediment view does.

`goc/templates/skills/standup/SKILL.md` Section 2 states that a card "may
appear here even while `status: active` — the overlay is orthogonal to the
progress status". A Context block that queries `--status open` makes that
impossible: `filter_cards` drops every active card before the block's own
`waiting_on` filter runs.

`goc --waiting` had exactly this defect and it was fixed engine-side by
auto-extending the default status to `all` and re-narrowing with
`live_impeded`'s two liveness conjuncts (non-terminal, non-draft). These
tests pin the same scope for the skill body, which cannot import the engine
and so runs the query through the CLI.

Scope only: every fixture below uses an open-ended `waiting_on` with no
`waiting_until`, the one cell where the block's hand-rolled truthiness test
and the engine's `waiting_impedes` matrix agree. The matrix drift itself is
`deck/standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits/`,
a separate decision-gated card — these tests must not start passing or
failing on its outcome.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "goc" / "templates" / "skills" / "standup" / "SKILL.md"

TERMINAL_STATUSES = ("done", "disproved", "superseded")


def section2_block() -> str:
    """The live `!`-block that feeds standup Section 2, read from the template."""
    for line in SKILL.read_text(encoding="utf-8").splitlines():
        if line.startswith("!`") and "impeded" in line:
            return line
    raise AssertionError("standup Section 2 Context block not found in SKILL.md")


def block_command(block: str) -> str:
    """The block's no-bootstrap arm, rewired to run the in-tree engine.

    The template's fallback arm (`else goc <args>; fi`) is what runs when no
    vendored `_goc-bootstrap.sh` is present; the tests have no `goc` on PATH,
    so the bare verb is replaced with the module invocation. Everything after
    it — the pipe, the `python3 -c` filter — is executed verbatim, which is
    the point: the predicate under test is the one the skill ships.
    """
    inner = block[2:].rstrip("`")
    inner = re.sub(r"^.*?;\s*else\s+goc\s+", "", inner, count=1)
    return f"{sys.executable} -m goc.cli " + inner.replace("; fi", "", 1)


class StandupImpededBlockScopeTest(unittest.TestCase):
    def env(self) -> dict:
        env = os.environ.copy()
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"
        return env

    def write_card(
        self,
        cwd: Path,
        title: str,
        status: str,
        waiting_on: str | None,
        *,
        draft: bool = False,
    ) -> None:
        card_dir = cwd / ".game-of-cards" / "deck" / title
        card_dir.mkdir(parents=True)
        overlay = f"waiting_on: {waiting_on}\n" if waiting_on is not None else ""
        if draft:
            overlay += "draft: true\n"
        closed = '"2026-05-10T00:00:00Z"' if status in TERMINAL_STATUSES else "null"
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            f"status: {status}\n"
            "stage: null\n"
            "contribution: low\n"
            'created: "2026-05-04T00:00:00Z"\n'
            f"closed_at: {closed}\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            f"{overlay}"
            "definition_of_done: |\n"
            "  - [ ] test card\n"
            "---\n\n"
            f"# {title}\n",
            encoding="utf-8",
        )
        (card_dir / "log.md").write_text("", encoding="utf-8")

    def block_titles(self, cwd: Path) -> set[str]:
        """Titles the Section 2 Context block reports for the deck at `cwd`."""
        out = subprocess.run(
            block_command(section2_block()),
            shell=True,
            cwd=cwd,
            env=self.env(),
            text=True,
            capture_output=True,
            check=False,
        ).stdout
        return {
            line.split(" [", 1)[0] for line in out.splitlines() if " [waiting_on:" in line
        }

    def waiting_titles(self, cwd: Path) -> set[str]:
        """Titles `goc --waiting` reports — the engine's impediment view."""
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "--waiting", "--json"],
            cwd=cwd,
            env=self.env(),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        return {c["title"] for c in json.loads(result.stdout or "[]")}

    def build_deck(self, cwd: Path) -> None:
        self.write_card(cwd, "open-impeded", "open", "external")
        self.write_card(cwd, "active-impeded", "active", "external")
        self.write_card(cwd, "open-clear", "open", None)
        self.write_card(cwd, "draft-impeded", "open", "external", draft=True)
        for term in TERMINAL_STATUSES:
            self.write_card(cwd, f"{term}-stale", term, "external")

    def test_block_reports_active_impeded_card(self) -> None:
        """The case Section 2's prose singles out must survive the query."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.build_deck(cwd)
            titles = self.block_titles(cwd)
            self.assertIn("active-impeded", titles)
            self.assertIn("open-impeded", titles)
            self.assertNotIn("open-clear", titles)

    def test_block_excludes_terminal_and_draft_cards(self) -> None:
        """Widening the scope must not start reporting stale overlays.

        Closing a card never clears `waiting_on` / `waiting_until`, and an
        unauthored scaffold is not actionable work — the two exclusions
        `live_impeded` applies on top of the widened status set.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.build_deck(cwd)
            titles = self.block_titles(cwd)
            for term in TERMINAL_STATUSES:
                self.assertNotIn(f"{term}-stale", titles)
            self.assertNotIn("draft-impeded", titles)

    def test_block_agrees_with_engine_waiting_view(self) -> None:
        """On open-ended waits the block and `goc --waiting` must agree exactly."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.build_deck(cwd)
            self.assertEqual(self.waiting_titles(cwd), self.block_titles(cwd))

    def test_block_query_is_not_narrowed_to_the_open_queue(self) -> None:
        """Static guard: the query itself must not re-narrow the status scope.

        The behavioural tests above catch a re-narrowing today, but only while
        a fixture happens to cover the dropped cell. This pins the query text
        so the regression cannot come back through a different status value.
        """
        block = section2_block()
        self.assertNotIn("--status open", block)
        self.assertIn("--status all", block)


if __name__ == "__main__":
    unittest.main()
