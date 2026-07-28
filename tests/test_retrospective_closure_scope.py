"""Regression guard: closure-history surfaces span every terminal status.

A closure is any card in `engine.TERMINAL_STATUSES` — `done`,
`disproved`, *or* `superseded`. The `retrospective` skill used to gather
its history with `goc --status done --json` at all three of its query
sites, so the two other terminal statuses were structurally invisible to
it even though its own Step 3 instructs the agent to look for "Cards
closed with `disproved` or `superseded`". Step 5's velocity line
inherited the same scope and under-reported throughput.

`--status` accepts one status or `all`, so "closures" can only be
expressed as `--closed-since <window>` (which auto-extends the status
scope to `all` and filters on `closed_at`) or as `--status all` plus a
client-side terminal-status filter. This guard pins both halves: no
closure query may narrow to a single status, and the terminal set the
skill body hand-lists must equal the engine's, so adding a fourth
terminal status turns this test red instead of silently re-opening the
gap.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc.engine import TERMINAL_STATUSES  # noqa: E402

TEMPLATE_SKILLS = ROOT / "goc" / "templates" / "skills"
RETROSPECTIVE = TEMPLATE_SKILLS / "retrospective" / "SKILL.md"
DECK_SKILL = TEMPLATE_SKILLS / "deck" / "SKILL.md"

# Every `goc <flags> --json` invocation on one line, stopping at the first
# shell separator so a `; else goc ...` / `| python3` tail is not swallowed.
# `\b` keeps `_goc-bootstrap.sh` from matching.
_QUERY_RE = re.compile(r"\bgoc ([^|;\n]*?--json)")

# The `TERMINAL = {...}` literal the skill body's inline Python filters on.
_TERMINAL_LITERAL_RE = re.compile(r"^TERMINAL = \{([^}]*)\}$", re.MULTILINE)


class RetrospectiveClosureScopeTest(unittest.TestCase):
    def test_closure_queries_do_not_narrow_to_a_single_status(self) -> None:
        body = RETROSPECTIVE.read_text()
        queries = [m.group(1).split() for m in _QUERY_RE.finditer(body)]
        self.assertTrue(
            queries,
            msg=(
                f"{RETROSPECTIVE.relative_to(ROOT)}: no `goc ... --json` query "
                "found — the retrospective must read closure history from the deck."
            ),
        )
        for argv in queries:
            if "--status" not in argv:
                # A `--closed-since` window query: the engine auto-extends the
                # status scope to `all`, so every terminal status is in range.
                self.assertIn(
                    "--closed-since",
                    argv,
                    msg=(
                        f"{RETROSPECTIVE.relative_to(ROOT)}: `goc {' '.join(argv)}` "
                        "neither sets a status scope nor windows on closed_at, so it "
                        "returns the open queue rather than closure history."
                    ),
                )
                continue
            scope = argv[argv.index("--status") + 1]
            self.assertEqual(
                "all",
                scope,
                msg=(
                    f"{RETROSPECTIVE.relative_to(ROOT)}: `goc {' '.join(argv)}` "
                    f"scopes closure history to `--status {scope}`, which hides "
                    f"{', '.join(sorted(TERMINAL_STATUSES - {scope}))}. Use "
                    "`--status all` with a terminal-status filter, or "
                    "`--closed-since <window>`."
                ),
            )

    def test_hand_listed_terminal_set_matches_the_engine(self) -> None:
        body = RETROSPECTIVE.read_text()
        literals = _TERMINAL_LITERAL_RE.findall(body)
        self.assertTrue(
            literals,
            msg=(
                f"{RETROSPECTIVE.relative_to(ROOT)}: no `TERMINAL = {{...}}` literal "
                "found. A `--status all` closure query needs a client-side terminal "
                "filter, otherwise open and active cards land in the retrospective."
            ),
        )
        for raw in literals:
            listed = {tok.strip().strip("'\"") for tok in raw.split(",") if tok.strip()}
            self.assertEqual(
                set(TERMINAL_STATUSES),
                listed,
                msg=(
                    f"{RETROSPECTIVE.relative_to(ROOT)}: the skill body filters on "
                    f"{sorted(listed)} but engine.TERMINAL_STATUSES is "
                    f"{sorted(TERMINAL_STATUSES)}. Keep the two in lockstep so a "
                    "status added to the engine cannot silently drop out of the "
                    "retrospective."
                ),
            )

    def test_deck_skill_closure_row_is_not_done_only(self) -> None:
        for line in DECK_SKILL.read_text().splitlines():
            if "closed cards" not in line.lower():
                continue
            self.assertNotIn(
                "--status done",
                line,
                msg=(
                    f"{DECK_SKILL.relative_to(ROOT)}: the verb row \"{line.strip()}\" "
                    "labels a `done`-only command as closed cards. `--since` is welded "
                    "to `--done` (engine `_cmd_default`), so point the row at "
                    "`--closed-since` instead."
                ),
            )


if __name__ == "__main__":
    unittest.main()
