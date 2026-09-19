"""The standup skill's Section 4 command must span the same status scope the
human gate does.

`goc/templates/skills/standup/SKILL.md` Section 4 promises "all cards with
`human_gate: decision` or `human_gate: session`". A command that queries
`--status open` cannot keep that promise: `filter_cards` drops every `active`
card before the block's own gate predicate runs — and a card claimed, worked,
and *then* parked behind a raised gate is the ordinary Andon-cord shape, not
an edge case.

Section 2 of the same file carried the identical narrowing for the
`waiting_on` overlay and was fixed by widening to `--status all` and
re-narrowing with two liveness conjuncts (non-terminal, non-draft);
`tests/test_standup_impeded_block_scope.py` pins that. These tests pin the
same scope for the gate, which needs the same two exclusions for its own
reasons: closing a card never lowers its gate, and `goc new` gates at
`decision` by default, so every unauthored scaffold carries one.

The skill body cannot import the engine — it runs as a shell pipeline on a
host with no installed package — so the block is executed verbatim here
rather than compared against a predicate.
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
SKILL = ROOT / "goc" / "templates" / "skills" / "standup" / "SKILL.md"

TERMINAL_STATUSES = ("done", "disproved", "superseded")


def section4_block() -> str:
    """The fenced command block under `## Section 4`, read from the template."""
    after = SKILL.read_text(encoding="utf-8").split("## Section 4", 1)
    if len(after) != 2:
        raise AssertionError("standup Section 4 heading not found in SKILL.md")
    fence = re.search(r"```bash\n(.*?)```", after[1], re.DOTALL)
    if not fence:
        raise AssertionError("standup Section 4 command fence not found in SKILL.md")
    return fence.group(1)


def block_command(block: str) -> str:
    """The shipped block, with the bare `goc` verb pointed at the in-tree engine.

    The tests have no `goc` on PATH, so the leading verb is rewritten to the
    module invocation. Everything after it — the pipe, the `python3 -c` filter,
    the gate and liveness predicates — runs verbatim, which is the point: the
    block under test is the one the skill ships.
    """
    return re.sub(r"(?m)^goc ", f"{sys.executable} -m goc.cli ", block, count=1)


class StandupWaitingOnYouBlockScopeTest(unittest.TestCase):
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
        gate: str,
        *,
        draft: bool = False,
    ) -> None:
        card_dir = cwd / ".game-of-cards" / "deck" / title
        card_dir.mkdir(parents=True)
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
            f"human_gate: {gate}\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            + ("draft: true\n" if draft else "")
            + "definition_of_done: |\n"
            "  - [ ] test card\n"
            "---\n\n"
            f"# {title}\n",
            encoding="utf-8",
        )
        (card_dir / "log.md").write_text("", encoding="utf-8")

    def block_titles(self, cwd: Path) -> set[str]:
        """Titles the Section 4 block reports for the deck at `cwd`."""
        out = subprocess.run(
            block_command(section4_block()),
            shell=True,
            cwd=cwd,
            env=self.env(),
            text=True,
            capture_output=True,
            check=False,
        ).stdout
        return {line.split(" [", 1)[0] for line in out.splitlines() if " [" in line}

    def build_deck(self, cwd: Path) -> None:
        self.write_card(cwd, "open-decision", "open", "decision")
        self.write_card(cwd, "open-session", "open", "session")
        self.write_card(cwd, "active-decision", "active", "decision")
        self.write_card(cwd, "active-session", "active", "session")
        self.write_card(cwd, "active-ungated", "active", "none")
        self.write_card(cwd, "open-ungated", "open", "none")
        self.write_card(cwd, "draft-decision", "open", "decision", draft=True)
        for term in TERMINAL_STATUSES:
            self.write_card(cwd, f"{term}-stale-gate", term, "decision")

    def test_block_reports_cards_parked_after_being_claimed(self) -> None:
        """The Andon-cord shape the section exists for must survive the query."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.build_deck(cwd)
            titles = self.block_titles(cwd)
            self.assertIn("active-decision", titles)
            self.assertIn("active-session", titles)
            self.assertIn("open-decision", titles)
            self.assertIn("open-session", titles)

    def test_block_excludes_ungated_cards(self) -> None:
        """Widening the status scope must not widen the gate predicate."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.build_deck(cwd)
            titles = self.block_titles(cwd)
            self.assertNotIn("active-ungated", titles)
            self.assertNotIn("open-ungated", titles)

    def test_block_excludes_terminal_and_draft_cards(self) -> None:
        """The two classes `--status all` adds that are not waiting on anybody.

        Closing a card never lowers its gate, so a terminal card can carry a
        stale one; `goc new` gates at `decision` by default, so every
        unauthored scaffold is gated and would otherwise flood the section.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.build_deck(cwd)
            titles = self.block_titles(cwd)
            for term in TERMINAL_STATUSES:
                self.assertNotIn(f"{term}-stale-gate", titles)
            self.assertNotIn("draft-decision", titles)

    def test_block_query_is_not_narrowed_to_the_open_queue(self) -> None:
        """Static guard: the query itself must not re-narrow the status scope.

        The behavioural tests above catch a re-narrowing only while a fixture
        happens to cover the dropped cell. This pins the query text so the
        regression cannot return through a different status value.
        """
        block = section4_block()
        self.assertNotIn("--status open", block)
        self.assertIn("--status all", block)


if __name__ == "__main__":
    unittest.main()
