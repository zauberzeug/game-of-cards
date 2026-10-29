"""Regression guard: state-touching verbs refuse closed cards.

`terminal-status-guard-missing-across-mutation-verbs` decided on one shared
guard, `engine._refuse_terminal_mutation`, which every verb that must not
write to a `done` / `disproved` / `superseded` card calls right after
`load_card_or_exit`. These tests pin the helper's contract and each guarded
verb's refusal: exit 2, the card byte-identical, and a message naming the
card, its status and a forward path that actually works.

`goc quality-pass` takes no title, so it skips closed cards rather than
refusing the run: they stay out of its LLM sample, and its two rewrite
helpers refuse any closed card that reaches them anyway. Its title rewrites
go through a `goc move` subprocess, so they inherit move's refusal.

`goc move` is the one guarded verb with an escape hatch: `--force` renames a
closed card anyway, for a deliberate correction of the record, and its
refusal names the flag.
"""

from __future__ import annotations

import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402


CARD = """---
title: {title}
summary: "Probe card for the terminal-status guard."
status: {status}
stage: null
contribution: medium
created: "2026-05-29T00:00:00Z"
closed_at: {closed_at}
human_gate: none
advances: []
advanced_by: []
{extra}tags: [bug]
definition_of_done: |
  - [x] MECHANICAL: probe.
---

# {title}

Body.
"""

# Checks every probe card passes, so an unguarded `goc attest` would write its
# block and exit 0 on a closed card rather than fail for an unrelated reason.
# Auto-commit is off here rather than per call: `attest` takes no `--no-commit`.
CONFIG = """layer_2_project_dod: []
layer_3_goc_dod:
  - name: advanced-by-closed
    kind: derived
  - name: dod-100-percent
    kind: derived
workflow:
  auto_commit: false
"""


def _card(title: str, status: str) -> engine.Card:
    return engine.Card(
        title=title,
        path=Path(title),
        frontmatter={"title": title, "status": status},
        body="",
        dod_open=0,
        dod_done=0,
    )


class RefuseTerminalMutationHelperTest(unittest.TestCase):
    def test_live_statuses_pass_through(self) -> None:
        for status in engine.STATUS_VALUES:
            if status in engine.TERMINAL_STATUSES:
                continue
            with self.subTest(status=status):
                self.assertIsNone(
                    engine._refuse_terminal_mutation(_card("live-card", status), "wait")
                )

    def test_terminal_statuses_exit_2_naming_card_status_verb_and_forward_path(self) -> None:
        for status in sorted(engine.TERMINAL_STATUSES):
            with self.subTest(status=status):
                err = io.StringIO()
                with redirect_stderr(err), self.assertRaises(SystemExit) as raised:
                    engine._refuse_terminal_mutation(_card("closed-card", status), "wait")
                self.assertEqual(raised.exception.code, 2)
                message = err.getvalue()
                self.assertIn("closed-card", message)
                self.assertIn(repr(status), message)
                self.assertIn("`goc wait`", message)
                self.assertIn("post-close amendment", message)

    def test_only_a_verb_with_an_override_is_told_of_one(self) -> None:
        for override in (None, "--force"):
            with self.subTest(override=override):
                err = io.StringIO()
                with redirect_stderr(err), self.assertRaises(SystemExit):
                    engine._refuse_terminal_mutation(
                        _card("closed-card", "done"), "move", override=override
                    )
                if override is None:
                    self.assertNotIn("overrides this refusal", err.getvalue())
                else:
                    self.assertIn(f"`{override}` overrides this refusal", err.getvalue())


class QualityPassRewriteHelperTest(unittest.TestCase):
    """`goc quality-pass`'s rewrite helpers refuse closed cards themselves.

    The verb keeps closed cards out of its LLM sample (see
    `GuardedVerbCliTest`); these guards hold for any caller that does not.
    """

    REWRITES = (
        ("summary", lambda card: engine._apply_summary_rewrite(card, "Rewritten summary.")),
        ("dod", lambda card: engine._apply_dod_rewrite(
            card, [{"idx": 0, "fix": "- [x] MECHANICAL: rewritten probe."}]
        )),
    )

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def _write(self, title: str, status: str) -> Path:
        card = self.root / title
        card.mkdir()
        closed_at = '"2026-05-30T00:00:00Z"' if status in engine.TERMINAL_STATUSES else "null"
        (card / "README.md").write_text(
            CARD.format(title=title, status=status, closed_at=closed_at, extra="")
        )
        return card

    def _assert_refused(self, card_dir: Path, card: engine.Card, rewrite) -> None:
        before = (card_dir / "README.md").read_bytes()
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as raised:
            rewrite(card)
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(before, (card_dir / "README.md").read_bytes())
        self.assertIn(f"ERROR: {card.title}: status is", err.getvalue())
        self.assertIn("`goc quality-pass`", err.getvalue())

    def test_closed_cards_are_refused(self) -> None:
        for status in sorted(engine.TERMINAL_STATUSES):
            card_dir = self._write(f"{status}-card", status)
            for name, rewrite in self.REWRITES:
                with self.subTest(status=status, rewrite=name):
                    self._assert_refused(card_dir, engine.load_card(card_dir), rewrite)

    def test_a_card_closed_after_the_caller_loaded_it_is_refused(self) -> None:
        # quality-pass loads its sample before the LLM call and the prompts, so
        # the guard must read the card as it is now, not the caller's copy.
        card_dir = self._write("stale-card", "open")
        stale = engine.load_card(card_dir)
        readme = card_dir / "README.md"
        readme.write_text(
            readme.read_text()
            .replace("status: open", "status: done")
            .replace("closed_at: null", 'closed_at: "2026-05-30T00:00:00Z"')
        )
        self.assertEqual(stale.status, "open")
        for name, rewrite in self.REWRITES:
            with self.subTest(rewrite=name):
                self._assert_refused(card_dir, stale, rewrite)

    def test_live_cards_are_still_rewritten(self) -> None:
        card_dir = self._write("live-card", "open")
        for name, rewrite in self.REWRITES:
            with self.subTest(rewrite=name):
                rewrite(engine.load_card(card_dir))
        text = (card_dir / "README.md").read_text()
        self.assertIn("summary: Rewritten summary.", text)
        self.assertIn("- [x] MECHANICAL: rewritten probe.", text)


class GuardedVerbCliTest(unittest.TestCase):
    """Drives the guarded verbs through the real CLI against a scratch deck."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.deck = self.root / ".game-of-cards" / "deck"
        self._write("live-card", "open")
        for status in sorted(engine.TERMINAL_STATUSES):
            # Each closed card carries the overlay it was impeded by while
            # live, so `--clear` has something it could wipe.
            extra = "waiting_on: external\n"
            if status == "superseded":
                extra = "superseded_by:\n  - live-card\n" + extra
            self._write(f"{status}-card", status, extra)
        (self.root / ".game-of-cards" / "config.yaml").write_text(CONFIG)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, title: str, status: str, extra: str = "") -> None:
        card = self.deck / title
        card.mkdir(parents=True)
        closed_at = '"2026-05-30T00:00:00Z"' if status in engine.TERMINAL_STATUSES else "null"
        (card / "README.md").write_text(
            CARD.format(title=title, status=status, closed_at=closed_at, extra=extra)
        )
        (card / "log.md").write_text("")

    def _goc(self, *args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        env.pop("GOC_WORKTREE_DECK", None)
        env.update(extra_env or {})
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=str(self.root), env=env, text=True, capture_output=True, check=False,
        )

    def _snapshot(self, title: str | None = None) -> dict[str, bytes]:
        """Every file of card `title`, or of the whole deck when omitted."""
        root = self.deck if title is None else self.deck / title
        return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}

    def _assert_refused(self, title: str, verb: str, *flags: str) -> subprocess.CompletedProcess[str]:
        # The whole deck, not just the card: `goc move` would rename the card
        # AND rewrite every reference to it in the other cards.
        before = self._snapshot()
        res = self._goc(verb, title, *flags)
        self.assertEqual(
            res.returncode, 2,
            msg=f"expected exit 2\nstdout: {res.stdout}\nstderr: {res.stderr}",
        )
        self.assertEqual(before, self._snapshot(), msg=f"the deck was mutated\nstderr: {res.stderr}")
        self.assertIn(f"ERROR: {title}: status is", res.stderr)
        self.assertIn(f"`goc {verb}`", res.stderr)
        return res

    def _link_from_live_card(self, *titles: str) -> None:
        readme = self.deck / "live-card" / "README.md"
        readme.write_text(readme.read_text() + "".join(f"\nSee [{t}](../{t}/).\n" for t in titles))

    @staticmethod
    def _summary_and_dod_rewrites(titles: list[str]) -> list[dict]:
        """Verdicts proposing a summary and a DoD rewrite for each of `titles`."""
        return [
            {
                "title": title,
                "title_verdict": {"ok": True},
                "summary_verdict": {"ok": False, "reason": "probe", "rewrite": f"Rewritten {title}."},
                "dod_issues": [{"idx": 0, "issue": "probe", "fix": f"- [x] MECHANICAL: rewritten {title}."}],
            }
            for title in titles
        ]

    def _fake_claude(self, verdicts: list[dict], *, before_reply: str = "") -> dict[str, str]:
        """Put a `claude` on PATH that records its argv and replies with
        `verdicts`, closed cards included. `before_reply` is a shell command
        the stub runs first — how a test changes the deck while the LLM call
        is in flight."""
        reply = self.root / "claude-reply.json"
        reply.write_text(json.dumps({"result": json.dumps(verdicts)}))
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        stub = bin_dir / "claude"
        stub.write_text(
            f'#!/bin/sh\nprintf "%s\\n" "$@" > "$FAKE_CLAUDE_ARGV"\n{before_reply}\ncat "$FAKE_CLAUDE_REPLY"\n'
        )
        stub.chmod(0o755)
        return {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "FAKE_CLAUDE_ARGV": str(self.root / "claude-argv.txt"),
            "FAKE_CLAUDE_REPLY": str(reply),
        }

    def test_wait_refuses_every_terminal_status_setters_and_clear_alike(self) -> None:
        shapes = (
            ("--reason", "external", "--until", "2027-01-01"),
            ("--until", "2027-01-01"),
            ("--clear",),
        )
        for status in sorted(engine.TERMINAL_STATUSES):
            for flags in shapes:
                with self.subTest(status=status, flags=flags):
                    self._assert_refused(f"{status}-card", "wait", *flags)

    def test_wait_still_sets_the_overlay_on_a_live_card(self) -> None:
        res = self._goc("wait", "live-card", "--reason", "external")
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertIn("waiting_on: external", (self.deck / "live-card" / "README.md").read_text())

    def test_attest_refuses_every_terminal_status(self) -> None:
        for status in sorted(engine.TERMINAL_STATUSES):
            with self.subTest(status=status):
                res = self._assert_refused(f"{status}-card", "attest", "--non-interactive")
                # The guard runs before the checks, so attest never tells the
                # caller to `goc done` a card that is already closed.
                self.assertNotIn("Next: goc done", res.stdout)

    def test_attest_still_records_a_verification_block_on_a_live_card(self) -> None:
        res = self._goc("attest", "live-card", "--non-interactive")
        self.assertEqual(res.returncode, 0, msg=res.stdout + res.stderr)
        self.assertIn("## Closure verification", (self.deck / "live-card" / "log.md").read_text())
        self.assertIn("Next: goc done live-card", res.stdout)

    def test_quality_pass_llm_keeps_closed_cards_out_of_the_llm_sample(self) -> None:
        closed = [f"{status}-card" for status in sorted(engine.TERMINAL_STATUSES)]
        extra_env = self._fake_claude(self._summary_and_dod_rewrites(["live-card", *closed]))
        before = {title: self._snapshot(title) for title in closed}
        res = self._goc("quality-pass", "--status", "all", "--llm", "--yes", extra_env=extra_env)
        self.assertEqual(res.returncode, 0, msg=res.stdout + res.stderr)
        for title in closed:
            with self.subTest(title=title):
                self.assertEqual(before[title], self._snapshot(title), msg=f"{title} was mutated")
        # Layer 1 still reports on every selected card; only Layer 2 skips.
        self.assertIn("Quality pass over 4 cards (status=all)", res.stdout)
        self.assertIn("skipping 3 closed cards", res.stdout)
        prompt = (self.root / "claude-argv.txt").read_text()
        self.assertIn("live-card", prompt)
        for title in closed:
            self.assertNotIn(title, prompt)
        live = (self.deck / "live-card" / "README.md").read_text()
        self.assertIn("summary: Rewritten live-card.", live)
        self.assertIn("- [x] MECHANICAL: rewritten live-card.", live)

    def test_quality_pass_llm_over_only_closed_cards_never_calls_the_llm(self) -> None:
        extra_env = self._fake_claude(self._summary_and_dod_rewrites(["done-card"]))
        before = self._snapshot("done-card")
        res = self._goc("quality-pass", "--status", "done", "--llm", "--yes", extra_env=extra_env)
        self.assertEqual(res.returncode, 0, msg=res.stdout + res.stderr)
        self.assertEqual(before, self._snapshot("done-card"))
        self.assertIn("skipping 1 closed card", res.stdout)
        self.assertFalse((self.root / "claude-argv.txt").exists(), msg="the LLM was called")

    def test_move_refuses_every_terminal_status_unless_forced(self) -> None:
        closed = [f"{status}-card" for status in sorted(engine.TERMINAL_STATUSES)]
        self._link_from_live_card(*closed)
        for title in closed:
            # The guard runs ahead of the checks on the new title and of
            # --dry-run: no title gets a closed card past it, and the preview
            # does not list a rename the real run would refuse.
            for args in ((f"renamed-{title}",), (f"renamed-{title}", "--dry-run"), ("Not_A_Slug",)):
                with self.subTest(title=title, args=args):
                    res = self._assert_refused(title, "move", *args)
                    self.assertIn("`--force` overrides this refusal", res.stderr)
                    self.assertEqual("", res.stdout)

    def test_move_still_renames_a_live_card(self) -> None:
        res = self._goc("move", "live-card", "renamed-live-card")
        self.assertEqual(res.returncode, 0, msg=res.stdout + res.stderr)
        self.assertFalse((self.deck / "live-card").exists())
        self.assertIn("title: renamed-live-card", (self.deck / "renamed-live-card" / "README.md").read_text())

    def test_move_force_renames_a_closed_card_and_rewrites_its_references(self) -> None:
        closed = [f"{status}-card" for status in sorted(engine.TERMINAL_STATUSES)]
        self._link_from_live_card(*closed)
        for title in closed:
            with self.subTest(title=title):
                res = self._goc("move", title, f"renamed-{title}", "--force")
                self.assertEqual(res.returncode, 0, msg=res.stdout + res.stderr)
                self.assertFalse((self.deck / title).exists())
                renamed = self.deck / f"renamed-{title}"
                self.assertIn(f"title: renamed-{title}", (renamed / "README.md").read_text())
                self.assertIn(f"renamed from {title}", (renamed / "log.md").read_text())
                self.assertIn(
                    f"[renamed-{title}](../renamed-{title}/)",
                    (self.deck / "live-card" / "README.md").read_text(),
                )

    def test_quality_pass_retitle_of_a_card_closed_mid_run_is_refused_by_move(self) -> None:
        # quality-pass loads its sample before the LLM call, so a card closed
        # while the call is in flight reaches the apply step as live. Its title
        # rewrite runs `goc move` in a subprocess that never passes --force,
        # so move's own guard refuses it and nothing is renamed.
        readme = self.deck / "live-card" / "README.md"
        closed = self.root / "live-card-closed-mid-run.md"
        closed.write_text(
            readme.read_text()
            .replace("status: open", "status: done")
            .replace("closed_at: null", 'closed_at: "2026-05-30T00:00:00Z"')
        )
        retitle = [{
            "title": "live-card",
            "title_verdict": {"ok": False, "reason": "probe", "rewrite": "renamed-live-card"},
            "summary_verdict": {"ok": True},
            "dod_issues": [],
        }]
        extra_env = self._fake_claude(
            retitle, before_reply=f"cp {shlex.quote(str(closed))} {shlex.quote(str(readme))}"
        )
        res = self._goc("quality-pass", "--llm", "--yes", extra_env=extra_env)
        self.assertEqual(res.returncode, 0, msg=res.stdout + res.stderr)
        self.assertFalse((self.deck / "renamed-live-card").exists(), msg=res.stdout + res.stderr)
        self.assertEqual(closed.read_bytes(), readme.read_bytes())
        self.assertEqual("", (self.deck / "live-card" / "log.md").read_text())
        self.assertIn("move failed: ERROR: live-card: status is 'done' (terminal)", res.stderr)
        self.assertIn("Applied: 0 titles", res.stdout)

    def test_the_forward_path_offered_is_not_the_refused_supersede_command(self) -> None:
        # `goc status <old> superseded --by <new>` reads like the way to retire
        # a closed card, but `_cmd_status` refuses every terminal card — so the
        # guard must not offer it. If supersession of closed cards ever becomes
        # legal, this test fails and the helper's message can say so again.
        res = self._goc("status", "done-card", "superseded", "--by", "live-card")
        self.assertEqual(res.returncode, 2, msg=res.stdout + res.stderr)
        refusal = self._goc("wait", "done-card", "--clear").stderr
        self.assertNotIn("superseded --by", refusal)
        self.assertIn("log.md", refusal)


if __name__ == "__main__":
    unittest.main()
