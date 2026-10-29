"""Regression guard: mutation verbs refuse input they cannot act on as asked.

`mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success`
decided on strict-refuse: invalid input exits 2 with `ERROR:` on stderr and
writes nothing, emitted through one shared helper,
`engine._refuse_invalid_input`, while each verb keeps its own predicate
inline. These tests pin the helper's contract and each guarded verb's
refusal — exit 2, no success line, every card byte-identical — next to the
valid input the guard must still let through.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402


CARD = """---
title: {title}
summary: "Probe card for the invalid-input guard."
status: open
stage: null
contribution: medium
created: "2026-05-29T00:00:00Z"
closed_at: null
human_gate: {human_gate}
advances:{advances}
advanced_by:{advanced_by}
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: probe.
---

# {title}

Body.
"""

CONFIG = """workflow:
  auto_commit: false
"""


def _edges(refs: tuple[str, ...]) -> str:
    return "".join(f"\n  - {ref}" for ref in refs) if refs else " []"


def _marker_check(name: str) -> str:
    """A layer-2 closure check that leaves `<name>.ran` in the project root."""
    code = f"open('{name}.ran', 'w').close()"
    cmd = ", ".join(f'"{part}"' for part in (sys.executable, "-c", code))
    return f"  - name: {name}\n    kind: automated\n    cmd: [{cmd}]\n"


class RefuseInvalidInputHelperTest(unittest.TestCase):
    def test_exits_2_with_the_reason_on_stderr(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as raised:
            engine._refuse_invalid_input("probe reason")
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(err.getvalue(), "ERROR: probe reason\n")


class _ScratchDeckCliTest(unittest.TestCase):
    """Drives `goc` through the real CLI against a scratch deck.

    The cards are written by hand, so a precondition — a half-edge, an edge
    already in place — is set up without the verb under test.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.deck = self.root / ".game-of-cards" / "deck"
        self.deck.mkdir(parents=True)
        (self.root / ".game-of-cards" / "config.yaml").write_text(CONFIG)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(
        self,
        title: str,
        *,
        advances: tuple[str, ...] = (),
        advanced_by: tuple[str, ...] = (),
        human_gate: str = "none",
    ) -> None:
        card = self.deck / title
        card.mkdir()
        (card / "README.md").write_text(
            CARD.format(
                title=title,
                advances=_edges(advances),
                advanced_by=_edges(advanced_by),
                human_gate=human_gate,
            )
        )
        (card / "log.md").write_text("")

    def _goc(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        env.pop("GOC_WORKTREE_DECK", None)
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=str(self.root), env=env, text=True, capture_output=True, check=False,
        )

    def _snapshot(self) -> dict[str, bytes]:
        return {
            path.relative_to(self.deck).as_posix(): path.read_bytes()
            for path in sorted(self.deck.rglob("*"))
            if path.is_file()
        }

    def _edges_of(self, title: str) -> tuple[list[str], list[str]]:
        fm = engine.load_card(self.deck / title).frontmatter
        return fm["advances"], fm["advanced_by"]

    def _refused(self, *args: str, error: str) -> subprocess.CompletedProcess[str]:
        """Run `goc <args>`: exit 2, `ERROR: <error>`, no success line, nothing written."""
        before = self._snapshot()
        res = self._goc(*args)
        self.assertEqual(
            res.returncode, 2,
            msg=f"expected exit 2\nstdout: {res.stdout}\nstderr: {res.stderr}",
        )
        self.assertEqual(before, self._snapshot(), msg=f"the deck was written\nstderr: {res.stderr}")
        self.assertNotIn(f"{args[0]}:", res.stdout)
        self.assertIn(f"ERROR: {error}", res.stderr)
        return res


class UnadvanceCliTest(_ScratchDeckCliTest):
    """`goc unadvance <title> --by <advancer>` removes the edge advancer → title."""

    def _assert_refused(self, title: str, advancer: str) -> subprocess.CompletedProcess[str]:
        return self._refused(
            "unadvance", title, "--by", advancer,
            error=f"cannot remove {advancer} → {title}: no such edge",
        )

    def test_refuses_an_edge_neither_card_lists(self) -> None:
        self._write("alpha")
        self._write("beta")
        res = self._assert_refused("alpha", "beta")
        self.assertNotIn("other way", res.stderr)

    def test_refuses_once_the_edge_is_gone(self) -> None:
        # The re-run case: the first call removes the edge, so the second has
        # nothing left to remove and must not report a removal again.
        self._write("alpha", advanced_by=("beta",))
        self._write("beta", advances=("alpha",))
        first = self._goc("unadvance", "alpha", "--by", "beta")
        self.assertEqual(first.returncode, 0, msg=first.stderr)
        self._assert_refused("alpha", "beta")

    def test_names_the_reversed_command_when_the_edge_runs_the_other_way(self) -> None:
        # alpha advances beta, so the edge is removed by `unadvance beta --by
        # alpha`; the swapped spelling must not pass for a removal.
        self._write("alpha", advances=("beta",))
        self._write("beta", advanced_by=("alpha",))
        res = self._assert_refused("alpha", "beta")
        self.assertIn("the edge runs the other way (alpha → beta)", res.stderr)
        self.assertIn("`goc unadvance beta --by alpha`", res.stderr)

    def test_still_removes_a_real_edge(self) -> None:
        self._write("alpha", advanced_by=("beta",))
        self._write("beta", advances=("alpha",))
        res = self._goc("unadvance", "alpha", "--by", "beta")
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertIn("unadvance: alpha.advanced_by -= beta; beta.advances -= alpha", res.stdout)
        self.assertEqual(self._edges_of("alpha"), ([], []))
        self.assertEqual(self._edges_of("beta"), ([], []))

    def test_still_removes_either_dangling_half_of_an_edge(self) -> None:
        # A hand edit can leave one half of an edge behind; `unadvance` is how
        # it gets removed, so one listed half is enough for the guard.
        self._write("child-half", advanced_by=("parent-a",))
        self._write("parent-a")
        self._write("child-b")
        self._write("parent-half", advances=("child-b",))
        for title, advancer in (("child-half", "parent-a"), ("child-b", "parent-half")):
            with self.subTest(title=title, advancer=advancer):
                res = self._goc("unadvance", title, "--by", advancer)
                self.assertEqual(res.returncode, 0, msg=res.stderr)
                self.assertEqual(self._edges_of(title), ([], []))
                self.assertEqual(self._edges_of(advancer), ([], []))


class AdvanceCliTest(_ScratchDeckCliTest):
    """`goc advance <title> --by <advancer>` adds the edge advancer → title."""

    def _assert_refused(self, title: str, advancer: str) -> subprocess.CompletedProcess[str]:
        return self._refused(
            "advance", title, "--by", advancer,
            error=f"cannot add {advancer} → {title}: the edge already exists",
        )

    def test_refuses_an_edge_both_cards_already_list(self) -> None:
        self._write("alpha", advanced_by=("beta",))
        self._write("beta", advances=("alpha",))
        self._assert_refused("alpha", "beta")

    def test_refuses_once_the_edge_is_in_place(self) -> None:
        # The re-run case: the first call adds the edge, so the second has
        # nothing left to add and must not report an addition again.
        self._write("alpha")
        self._write("beta")
        first = self._goc("advance", "alpha", "--by", "beta")
        self.assertEqual(first.returncode, 0, msg=first.stderr)
        self._assert_refused("alpha", "beta")

    def test_names_an_existing_edge_inside_a_cycle_as_existing(self) -> None:
        # alpha and beta advance each other, a cycle only a hand edit can
        # build. Re-adding beta → alpha adds nothing, so the refusal names the
        # edge already in place, not a cycle the call would not create.
        self._write("alpha", advances=("beta",), advanced_by=("beta",))
        self._write("beta", advances=("alpha",), advanced_by=("alpha",))
        res = self._assert_refused("alpha", "beta")
        self.assertNotIn("cycle", res.stderr)

    def test_still_refuses_the_reversed_edge_as_a_cycle(self) -> None:
        # alpha advances beta, so beta → alpha is a new edge the other way:
        # the cycle guard refuses it, and it is not mistaken for the edge
        # already in place.
        self._write("alpha", advances=("beta",))
        self._write("beta", advanced_by=("alpha",))
        res = self._refused(
            "advance", "alpha", "--by", "beta",
            error="adding beta → alpha would create a cycle in the advances graph",
        )
        self.assertNotIn("already exists", res.stderr)

    def test_still_adds_a_new_edge(self) -> None:
        self._write("alpha")
        self._write("beta")
        res = self._goc("advance", "alpha", "--by", "beta")
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertIn("advance: alpha.advanced_by += beta; beta.advances += alpha", res.stdout)
        self.assertEqual(self._edges_of("alpha"), ([], ["beta"]))
        self.assertEqual(self._edges_of("beta"), (["alpha"], []))

    def test_still_completes_either_dangling_half_of_an_edge(self) -> None:
        # A hand edit can leave one half of an edge behind; `advance` is one
        # way to complete it, so only both listed halves trip the guard.
        self._write("child-half", advanced_by=("parent-a",))
        self._write("parent-a")
        self._write("child-b")
        self._write("parent-half", advances=("child-b",))
        for title, advancer in (("child-half", "parent-a"), ("child-b", "parent-half")):
            with self.subTest(title=title, advancer=advancer):
                res = self._goc("advance", title, "--by", advancer)
                self.assertEqual(res.returncode, 0, msg=res.stderr)
                self.assertEqual(self._edges_of(title), ([], [advancer]))
                self.assertEqual(self._edges_of(advancer), ([title], []))


class DecideCliTest(_ScratchDeckCliTest):
    """`goc decide <title> --decision <what> --because <why>` lowers a raised gate."""

    def setUp(self) -> None:
        super().setUp()
        self._write("parked", human_gate="decision")

    def _assert_refused(self, decision: str, because: str, *, blank: str) -> None:
        res = self._refused(
            "decide", "parked", "--decision", decision, "--because", because,
            error=f"parked: --decision and --because must be non-empty (blank: {blank})",
        )
        self.assertNotIn("decision recorded", res.stdout)

    def test_refuses_a_blank_decision(self) -> None:
        self._assert_refused("", "The reasoning.", blank="--decision")

    def test_refuses_a_blank_because(self) -> None:
        self._assert_refused("The decision.", "", blank="--because")

    def test_refuses_both_blank(self) -> None:
        self._assert_refused("", "", blank="--decision, --because")

    def test_refuses_whitespace_only_values(self) -> None:
        # Whitespace renders as nothing in the `## Decision` block and the
        # log entry, so it is as blank there as an empty string.
        self._assert_refused("   ", "\t\n", blank="--decision, --because")

    def test_still_records_a_real_decision(self) -> None:
        res = self._goc("decide", "parked", "--decision", "Option A.", "--because", "It is simpler.")
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertIn("parked: decision recorded; gate decision → none", res.stdout)
        card = engine.load_card(self.deck / "parked")
        self.assertEqual(card.human_gate, "none")
        self.assertIn("Option A.", card.body)
        self.assertIn("It is simpler.", card.body)


class AttestCliTest(_ScratchDeckCliTest):
    """`goc attest <title> --skip <name>` records a configured check as SKIPPED.

    Each configured check leaves a marker file when it runs, so a refusal can
    show that no check ran — not even the one a typo meant to skip, which is
    what the defect did — beside the deck staying byte-identical.
    """

    CHECKS = ("lint", "unit-tests")

    def setUp(self) -> None:
        super().setUp()
        (self.root / ".game-of-cards" / "config.yaml").write_text(
            CONFIG
            + "layer_2_project_dod:\n"
            + "".join(_marker_check(name) for name in self.CHECKS)
            + "layer_3_goc_dod: []\n"
        )
        self._write("probe")

    def _ran(self) -> set[str]:
        return {name for name in self.CHECKS if (self.root / f"{name}.ran").exists()}

    def _assert_refused(self, *skips: str, unknown: str) -> subprocess.CompletedProcess[str]:
        res = self._refused(
            "attest", "probe", *(arg for name in skips for arg in ("--skip", name)),
            error=f"probe: unknown --skip {unknown} — the configured closure checks are: lint, unit-tests",
        )
        self.assertEqual(self._ran(), set(), msg="a check ran before the refusal")
        return res

    def test_refuses_a_name_no_configured_check_has(self) -> None:
        self._assert_refused("lnt", unknown="name 'lnt'")

    def test_refuses_an_unknown_name_beside_a_valid_one(self) -> None:
        # The valid skip must not carry the typo through: pre-fix this ran
        # unit-tests, the check the typo meant to skip, and exited 0.
        self._assert_refused("lint", "unit-test", unknown="name 'unit-test'")

    def test_names_each_unknown_name_once_in_the_order_given(self) -> None:
        self._assert_refused("tests", "lnt", "tests", unknown="names 'tests', 'lnt'")

    def test_refuses_a_typo_ahead_of_the_all_skipped_guard(self) -> None:
        # Every configured check is skipped too, but the typo is the input
        # error to report first: fixing it may be all the call needed.
        res = self._assert_refused("lint", "unit-tests", "lnit", unknown="name 'lnit'")
        self.assertNotIn("every configured closure check was skipped", res.stderr)

    def test_still_skips_a_configured_check(self) -> None:
        res = self._goc("attest", "probe", "--skip", "lint", "--non-interactive")
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertIn("[~] lint — SKIPPED", res.stdout)
        self.assertIn("Attestation OK.", res.stdout)
        self.assertEqual(self._ran(), {"unit-tests"})
        log = (self.deck / "probe" / "log.md").read_text()
        self.assertIn("- [~] lint SKIPPED", log)
        self.assertIn("- [x] unit-tests", log)


class WaitCliTest(_ScratchDeckCliTest):
    """`goc wait <title> --until <date>` hides a card from the queue until the date.

    `waiting_impedes` reads an `--until` that has already elapsed as no wait at
    all, so the verb refuses one instead of writing it under a success line
    while the card stays in the queue. Dates are set relative to the clock with
    an hour or more of margin, so no run lands on the boundary.
    """

    def setUp(self) -> None:
        super().setUp()
        self._write("probe")
        self.now = datetime.now(tz=timezone.utc)

    def _instant(self, delta: timedelta) -> str:
        return (self.now + delta).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _queued(self) -> tuple[bool, bool]:
        """Whether `probe` is listed by `--ready` and by `--waiting`."""
        listed = []
        for query in ("--ready", "--waiting"):
            res = self._goc(query, "--no-color")
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            listed.append("probe" in res.stdout)
        return listed[0], listed[1]

    def _assert_refused(self, *args: str, until: str, bare_date: bool) -> None:
        note = " (a bare date is midnight UTC at the start of that day)" if bare_date else ""
        res = self._refused(
            "wait", "probe", *args, "--until", until,
            error=(
                f"probe: --until {until!r} has already elapsed{note}, so the wait would not "
                "hide probe from the queue"
            ),
        )
        self.assertEqual(res.stdout, "")

    def _assert_set(self, until: str) -> None:
        # The output a future --until always produced: the guard adds nothing.
        res = self._goc("wait", "probe", "--until", until)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertEqual(res.stderr, "")
        self.assertEqual(
            res.stdout,
            f"probe: waiting_on=None waiting_until={until!r} (no reason set; implied 'deferred')\n",
        )
        self.assertEqual(self._queued(), (False, True))

    def test_refuses_today_as_a_bare_date(self) -> None:
        # Midnight UTC at the start of today has passed at every moment of the
        # day it names: the everyday form of the defect.
        self._assert_refused(until=self.now.date().isoformat(), bare_date=True)
        self.assertEqual(self._queued(), (True, False))

    def test_refuses_a_long_past_date(self) -> None:
        self._assert_refused("--reason", "external", until="2020-01-01", bare_date=True)

    def test_refuses_a_datetime_already_past(self) -> None:
        self._assert_refused(until=self._instant(-timedelta(hours=1)), bare_date=False)

    def test_refusal_leaves_a_live_wait_in_place(self) -> None:
        live = self._goc("wait", "probe", "--reason", "external", "--until", self._instant(timedelta(days=7)))
        self.assertEqual(live.returncode, 0, msg=live.stderr)
        self._assert_refused(until="2020-01-01", bare_date=True)
        self.assertEqual(self._queued(), (False, True))

    def test_still_sets_a_future_date(self) -> None:
        self._assert_set((self.now + timedelta(days=30)).date().isoformat())

    def test_still_sets_a_future_datetime(self) -> None:
        self._assert_set(self._instant(timedelta(hours=1)))

    def test_judges_only_the_until_this_call_passes(self) -> None:
        # A stale date already on the card is not this guard's input: whether a
        # bare --reason should refresh it is the open question of
        # goc-wait-does-not-clear-stale-elapsed-waiting-until.
        readme = self.deck / "probe" / "README.md"
        readme.write_text(
            readme.read_text().replace("human_gate: none\n", 'human_gate: none\nwaiting_until: "2020-01-01"\n')
        )
        res = self._goc("wait", "probe", "--reason", "external")
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertNotIn("has already elapsed", res.stderr)


if __name__ == "__main__":
    unittest.main()
