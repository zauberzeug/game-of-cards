"""Regression tests for the SessionStart hook frontmatter parser.

The bug (pre-fix): the hook substring-matched `status: active` against the
full README, so a closed card whose body *mentioned* that string was falsely
reported as active.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("deck_session_start", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SessionStartHookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def _readme(self, content: str) -> Path:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        )
        tmp.write(content)
        tmp.flush()
        return Path(tmp.name)

    def test_active_frontmatter_detected(self):
        p = self._readme("---\nstatus: active\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_status(p), "active")

    def test_done_frontmatter_not_active(self):
        p = self._readme("---\nstatus: done\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_status(p), "done")

    def test_body_mention_does_not_fool_parser(self):
        """Regression: a closed card whose body contains `status: active` must not be flagged."""
        p = self._readme(
            "---\nstatus: done\ntitle: t\n---\n"
            "Parallel agents use `status: active` as a soft lock.\n"
            "```yaml\nstatus: active\n```\n"
        )
        self.assertNotEqual(self.hook._card_status(p), "active")
        self.assertEqual(self.hook._card_status(p), "done")

    def test_open_card_not_active(self):
        p = self._readme("---\nstatus: open\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_status(p), "open")

    def test_missing_frontmatter_returns_none(self):
        p = self._readme("no frontmatter here\nstatus: active\n")
        self.assertIsNone(self.hook._card_status(p))

    def test_original_status_key_not_matched(self):
        """A line like `original_status: active` must not satisfy the check."""
        p = self._readme("---\noriginal_status: active\nstatus: done\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_status(p), "done")

    def test_human_gate_default_none_when_absent(self):
        p = self._readme("---\nstatus: active\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_human_gate(p), "none")

    def test_human_gate_decision_parsed(self):
        p = self._readme("---\nstatus: active\nhuman_gate: decision\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_human_gate(p), "decision")

    def test_human_gate_session_parsed(self):
        p = self._readme("---\nstatus: active\nhuman_gate: session\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_human_gate(p), "session")

    def test_human_gate_empty_value_normalized_to_none(self):
        p = self._readme("---\nstatus: active\nhuman_gate: \ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_human_gate(p), "none")


class SessionStartHookInlineCommentTest(unittest.TestCase):
    """The four frontmatter readers must strip a trailing YAML `# comment`.

    Regression for the latent defect where hand-authored inline comments on
    `status`, `human_gate`, `waiting_on`, or `waiting_until` would leak into
    the parsed value and silently misclassify the card.
    """

    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def _readme(self, content: str) -> Path:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        )
        tmp.write(content)
        tmp.flush()
        return Path(tmp.name)

    def test_status_strips_trailing_comment(self):
        p = self._readme("---\nstatus: active # resumable note\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_status(p), "active")

    def test_human_gate_strips_trailing_comment(self):
        p = self._readme(
            "---\nstatus: active\nhuman_gate: decision # parked\ntitle: t\n---\nbody\n"
        )
        self.assertEqual(self.hook._card_human_gate(p), "decision")

    def test_waiting_on_strips_trailing_comment(self):
        p = self._readme(
            "---\nstatus: active\nwaiting_on: external # see GH-123\ntitle: t\n---\nbody\n"
        )
        self.assertEqual(self.hook._card_waiting_on(p), "external")

    def test_waiting_until_strips_trailing_comment(self):
        p = self._readme(
            "---\nstatus: active\nwaiting_until: 2026-06-05 # deferred\ntitle: t\n---\nbody\n"
        )
        self.assertEqual(self.hook._card_waiting_until(p), "2026-06-05")

    def test_hash_inside_bare_value_is_preserved(self):
        """YAML: `#` terminates a value only when preceded by whitespace.

        A `#` glued to a non-whitespace character is part of the scalar — the
        helper must not amputate `foo#bar` into `foo`.
        """
        p = self._readme("---\nstatus: foo#bar\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_status(p), "foo#bar")

    def test_quoted_then_comment_unwraps_to_inner_value(self):
        p = self._readme(
            '---\nstatus: "active" # quoted then commented\ntitle: t\n---\nbody\n'
        )
        self.assertEqual(self.hook._card_status(p), "active")


class SessionStartHookGatedActiveCardsTest(unittest.TestCase):
    """The hook must not label `human_gate != none` active cards as resumable.

    Fixture deck contains three active cards: one each at human_gate `none`,
    `decision`, `session`. The expected output puts the `none` card under the
    `resume or close` line and the two gated cards under a distinct
    `awaiting human / agent cannot resume` line.
    """

    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def _make_card(self, deck_dir: Path, name: str, status: str, human_gate: str) -> None:
        card = deck_dir / name
        card.mkdir(parents=True)
        body = (
            f"---\nstatus: {status}\nhuman_gate: {human_gate}\ntitle: {name}\n---\nbody\n"
        )
        (card / "README.md").write_text(body, encoding="utf-8")

    def _run_hook(self, project_dir: Path) -> str:
        buf = io.StringIO()
        stdin = io.StringIO(json.dumps({"cwd": str(project_dir)}))
        with mock.patch.object(sys, "stdin", stdin), redirect_stdout(buf):
            rc = self.hook.main()
        self.assertEqual(rc, 0)
        return buf.getvalue()

    def test_three_active_cards_partitioned_by_human_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            deck = project / ".game-of-cards" / "deck"
            deck.mkdir(parents=True)
            self._make_card(deck, "ready-card", "active", "none")
            self._make_card(deck, "decision-card", "active", "decision")
            self._make_card(deck, "session-card", "active", "session")
            out = self._run_hook(project)

        resumable_lines = [
            line for line in out.splitlines() if "resume or close" in line
        ]
        self.assertEqual(len(resumable_lines), 1, out)
        self.assertIn("ready-card", resumable_lines[0])
        self.assertNotIn("decision-card", resumable_lines[0])
        self.assertNotIn("session-card", resumable_lines[0])

        parked_lines = [
            line for line in out.splitlines() if "agent cannot resume" in line
        ]
        self.assertEqual(len(parked_lines), 1, out)
        self.assertIn("decision-card", parked_lines[0])
        self.assertIn("session-card", parked_lines[0])
        self.assertNotIn("ready-card", parked_lines[0])

    def test_only_gated_active_cards_emits_only_parked_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            deck = project / ".game-of-cards" / "deck"
            deck.mkdir(parents=True)
            self._make_card(deck, "decision-card", "active", "decision")
            out = self._run_hook(project)
        self.assertNotIn("resume or close", out)
        self.assertIn("agent cannot resume", out)
        self.assertIn("decision-card", out)

    def test_only_resumable_active_cards_emits_only_resumable_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            deck = project / ".game-of-cards" / "deck"
            deck.mkdir(parents=True)
            self._make_card(deck, "ready-card", "active", "none")
            out = self._run_hook(project)
        self.assertIn("resume or close", out)
        self.assertNotIn("agent cannot resume", out)
        self.assertIn("ready-card", out)

    def test_no_active_cards_emits_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            deck = project / ".game-of-cards" / "deck"
            deck.mkdir(parents=True)
            self._make_card(deck, "done-card", "done", "none")
            out = self._run_hook(project)
        self.assertEqual(out, "")


class SessionStartHookWaitingOnTest(unittest.TestCase):
    """The hook must not label `waiting_on`/`waiting_until`-impeded active cards as resumable.

    Three-axis stuck model from AGENTS.md: `human_gate` (decision/session) and
    the `waiting_on` impediment overlay compose. A `status: active,
    human_gate: none` card with `waiting_on: external|resource|deferred` (or a
    future `waiting_until`) is impeded and not agent-resumable, even though
    the prior partition only checked `human_gate`.
    """

    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def _write_card(self, deck_dir: Path, name: str, frontmatter: str) -> None:
        card = deck_dir / name
        card.mkdir(parents=True)
        body = f"---\n{frontmatter.strip()}\n---\nbody\n"
        (card / "README.md").write_text(body, encoding="utf-8")

    def _run_hook(self, project_dir: Path) -> str:
        buf = io.StringIO()
        stdin = io.StringIO(json.dumps({"cwd": str(project_dir)}))
        with mock.patch.object(sys, "stdin", stdin), redirect_stdout(buf):
            rc = self.hook.main()
        self.assertEqual(rc, 0)
        return buf.getvalue()

    def test_waiting_on_reader_returns_none_when_absent(self):
        p = Path(tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name)
        p.write_text("---\nstatus: active\n---\nbody\n", encoding="utf-8")
        self.assertIsNone(self.hook._card_waiting_on(p))

    def test_waiting_on_reader_returns_value(self):
        p = Path(tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name)
        p.write_text(
            "---\nstatus: active\nwaiting_on: external\n---\nbody\n", encoding="utf-8"
        )
        self.assertEqual(self.hook._card_waiting_on(p), "external")

    def test_waiting_until_reader_strips_quotes(self):
        p = Path(tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name)
        p.write_text(
            '---\nstatus: active\nwaiting_until: "2099-01-01"\n---\nbody\n',
            encoding="utf-8",
        )
        self.assertEqual(self.hook._card_waiting_until(p), "2099-01-01")

    def test_is_impeded_true_for_each_waiting_on_value(self):
        for value in ("external", "resource", "deferred"):
            p = Path(
                tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name
            )
            p.write_text(
                f"---\nstatus: active\nwaiting_on: {value}\n---\nbody\n",
                encoding="utf-8",
            )
            self.assertTrue(self.hook._is_impeded(p), f"waiting_on: {value}")

    def test_is_impeded_true_for_future_waiting_until(self):
        p = Path(tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name)
        p.write_text(
            "---\nstatus: active\nwaiting_until: 2099-01-01\n---\nbody\n",
            encoding="utf-8",
        )
        self.assertTrue(self.hook._is_impeded(p))

    def test_is_impeded_false_for_past_waiting_until_without_waiting_on(self):
        p = Path(tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name)
        p.write_text(
            "---\nstatus: active\nwaiting_until: 2000-01-01\n---\nbody\n",
            encoding="utf-8",
        )
        # Elapsed wait re-enters the queue (engine.waiting_impedes contract).
        self.assertFalse(self.hook._is_impeded(p))

    def test_is_impeded_false_for_waiting_on_with_elapsed_waiting_until(self):
        """Case A of the four-cell matrix: reason set + elapsed date → not impeded.

        Engine contract (`goc.engine.waiting_impedes`, AGENTS.md three-axis
        stuck model): an elapsed `waiting_until` resurfaces the card even
        when `waiting_on` is also set. The hook must agree with the engine
        on this cell; otherwise an agent-resumable card is misframed as
        `Impeded active card(s) — agent cannot resume` at session start.
        """
        for value in ("external", "resource", "deferred"):
            p = Path(
                tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name
            )
            p.write_text(
                f"---\nstatus: active\nwaiting_on: {value}\n"
                "waiting_until: 2000-01-01\n---\nbody\n",
                encoding="utf-8",
            )
            self.assertFalse(
                self.hook._is_impeded(p),
                f"waiting_on: {value} + elapsed waiting_until should resurface",
            )

    def test_case_a_card_appears_under_resumable_not_impeded(self):
        """End-to-end: a `status: active, human_gate: none, waiting_on: external,
        waiting_until: <past>` card must be partitioned under the resumable
        line, not the impediment line.
        """
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            deck = project / ".game-of-cards" / "deck"
            deck.mkdir(parents=True)
            self._write_card(
                deck,
                "case-a-elapsed",
                "status: active\nhuman_gate: none\n"
                "waiting_on: external\nwaiting_until: 2000-01-01",
            )
            out = self._run_hook(project)
        resumable_lines = [
            line for line in out.splitlines() if "resume or close" in line
        ]
        self.assertEqual(len(resumable_lines), 1, out)
        self.assertIn("case-a-elapsed", resumable_lines[0])
        impeded_lines = [
            line for line in out.splitlines() if "waiting_on" in line
        ]
        self.assertEqual(impeded_lines, [], out)

    def test_is_impeded_true_for_bare_deferral_with_malformed_waiting_until(self):
        """Engine `until_unparseable` backstop: a present-but-unparseable
        `waiting_until` with no `waiting_on` must be treated as impeded.

        `goc.engine.waiting_impedes` errs on the side of hiding when the
        date is unreadable (covered by `validate_waiting_overlay` upstream,
        but `waiting_impedes` runs on pre-validate / hand-edited decks).
        Without this mirror in the hook, the engine hides the card from
        queues while the hook frames it as resumable — see the prior fix
        `waiting-impedes-treats-malformed-waiting-until-as-no-impediment`
        for the engine half.
        """
        p = Path(tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name)
        p.write_text(
            "---\nstatus: active\nwaiting_until: 2026-99-99\n---\nbody\n",
            encoding="utf-8",
        )
        self.assertTrue(self.hook._is_impeded(p))

    def test_is_impeded_false_when_no_overlay(self):
        p = Path(tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name)
        p.write_text("---\nstatus: active\n---\nbody\n", encoding="utf-8")
        self.assertFalse(self.hook._is_impeded(p))

    def test_is_impeded_true_for_non_canonical_waiting_on(self):
        """Sibling cell to the canonical-enum cases: a hand-edited or typo'd
        `waiting_on` reason (any string outside {external, resource, deferred})
        must still impede, mirroring the engine's `reason is not None` gate.

        `goc.engine.waiting_impedes` falls through to "any non-None reason →
        impeded" at `engine.py:1793-1795`. The validator at `engine.py:1232`
        rejects non-canonical values at load time, but the hook runs on
        pre-validate / hand-edited decks (it reads README.md directly with
        its own mini-frontmatter parser, bypassing the loader).
        """
        for value, until in (
            ("externl", None),
            ("customer-call", '"not-a-date"'),
        ):
            p = Path(
                tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name
            )
            front = f"status: active\nwaiting_on: {value}\n"
            if until is not None:
                front += f"waiting_until: {until}\n"
            p.write_text(f"---\n{front}---\nbody\n", encoding="utf-8")
            self.assertTrue(
                self.hook._is_impeded(p),
                f"non-canonical waiting_on={value!r} must still impede",
            )

    def test_coerced_bool_int_waiting_on_resolves_to_none(self):
        """Opposite cell to the non-canonical-string case: a `waiting_on`
        token the yaml-lite parser coerces away from `str` (`false` / `true`
        / `yes` / `no` / `42`) must read as None — matching the engine's
        `isinstance(v, str)` guard in `Card.waiting_on`. The reader, not the
        shared `_scalar_or_none`, drops the coerced token (the sibling
        `waiting_until` reader keeps the engine's no-isinstance contract).
        """
        for value in ("false", "true", "yes", "no", "42"):
            p = self._readme_path(f"status: active\nwaiting_on: {value}")
            self.assertIsNone(
                self.hook._card_waiting_on(p),
                f"coerced waiting_on={value!r} must resolve to None",
            )

    def test_coerced_bool_int_waiting_on_not_impeded_agrees_with_engine(self):
        """A coerced bool/int `waiting_on` with no `waiting_until` must NOT
        impede, mirroring `engine.waiting_impedes` (which sees `waiting_on`
        as None after the `isinstance` guard). Before the fix the hook
        over-fired `_is_impeded=True` while the engine reported resumable.
        """
        from goc import engine  # local import: engine on sys.path via ROOT

        sys.path.insert(0, str(ROOT))
        for value in ("false", "true", "yes", "no", "42"):
            with tempfile.TemporaryDirectory() as tmp:
                card_dir = Path(tmp)
                readme = card_dir / "README.md"
                readme.write_text(
                    "---\ntitle: demo\nstatus: active\ncontribution: medium\n"
                    f"human_gate: none\nwaiting_on: {value}\ntags: []\n---\n"
                    "# Demo\n\n## Definition of Done\n- [ ] x\n",
                    encoding="utf-8",
                )
                card = engine.load_card(card_dir)
                self.assertFalse(
                    engine.waiting_impedes(card),
                    f"engine must treat coerced waiting_on={value!r} as resumable",
                )
                self.assertFalse(
                    self.hook._is_impeded(readme),
                    f"hook must agree: coerced waiting_on={value!r} is resumable",
                )

    def _readme_path(self, frontmatter: str) -> Path:
        p = Path(
            tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name
        )
        p.write_text(f"---\n{frontmatter}\n---\nbody\n", encoding="utf-8")
        return p

    def test_four_card_matrix_only_a_appears_under_resumable(self):
        """DoD fixture: (a) plain active, (b) waiting_on: external,
        (c) waiting_on: deferred + future waiting_until, (d) human_gate: decision.
        Only (a) is framed as resumable.
        """
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            deck = project / ".game-of-cards" / "deck"
            deck.mkdir(parents=True)
            self._write_card(deck, "a-plain", "status: active\nhuman_gate: none")
            self._write_card(
                deck,
                "b-external",
                "status: active\nhuman_gate: none\nwaiting_on: external",
            )
            self._write_card(
                deck,
                "c-deferred-future",
                "status: active\nhuman_gate: none\n"
                "waiting_on: deferred\nwaiting_until: 2099-01-01",
            )
            self._write_card(
                deck, "d-gated", "status: active\nhuman_gate: decision"
            )
            out = self._run_hook(project)

        resumable_lines = [
            line for line in out.splitlines() if "resume or close" in line
        ]
        self.assertEqual(len(resumable_lines), 1, out)
        self.assertIn("a-plain", resumable_lines[0])
        self.assertNotIn("b-external", resumable_lines[0])
        self.assertNotIn("c-deferred-future", resumable_lines[0])
        self.assertNotIn("d-gated", resumable_lines[0])

        # b and c are impeded; d is gate-parked. Both kinds get "agent cannot resume."
        not_resumable = "\n".join(
            line for line in out.splitlines() if "agent cannot resume" in line
        )
        self.assertIn("b-external", not_resumable)
        self.assertIn("c-deferred-future", not_resumable)
        self.assertIn("d-gated", not_resumable)

    def test_same_day_future_datetime_waiting_until_is_impeded(self):
        """Same-day future `waiting_until: <today>THH:MM:SSZ` is impeded.

        The engine compares `waiting_until` at full UTC timestamp precision
        (`engine._waiting_until_instant`); the hook must agree. A date-level
        truncation would round a 23:59:59Z timestamp to "today" and clear
        the wait early. Both sides of the boundary (future instant vs.
        elapsed start-of-day instant) are pinned against a fixed `now`
        injected through `datetime.now` so the test does not rot at midnight.
        """
        # Pin the clock to a known UTC instant well after midnight so the
        # `<today>T00:00:00Z` case is unambiguously elapsed.
        pinned_now = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)
        today_iso = pinned_now.date().isoformat()
        future_same_day = f"{today_iso}T23:59:59Z"
        elapsed_today_start = f"{today_iso}T00:00:00Z"

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):  # type: ignore[override]
                if tz is None:
                    return pinned_now.replace(tzinfo=None)
                return pinned_now.astimezone(tz)

        with mock.patch.object(self.hook, "datetime", FrozenDateTime):
            future_card = Path(
                tempfile.NamedTemporaryFile(
                    mode="w", suffix=".md", delete=False
                ).name
            )
            future_card.write_text(
                "---\nstatus: active\nhuman_gate: none\n"
                f"waiting_on: external\nwaiting_until: {future_same_day}\n"
                "---\nbody\n",
                encoding="utf-8",
            )
            self.assertTrue(
                self.hook._is_impeded(future_card),
                "same-day future datetime waiting_until must be impeded "
                "(engine compares at full UTC timestamp precision)",
            )

            elapsed_card = Path(
                tempfile.NamedTemporaryFile(
                    mode="w", suffix=".md", delete=False
                ).name
            )
            elapsed_card.write_text(
                "---\nstatus: active\nhuman_gate: none\n"
                f"waiting_on: external\nwaiting_until: {elapsed_today_start}\n"
                "---\nbody\n",
                encoding="utf-8",
            )
            self.assertFalse(
                self.hook._is_impeded(elapsed_card),
                "elapsed same-day datetime waiting_until must resurface "
                "(engine contract: elapsed instant clears the wait)",
            )

    def test_impeded_bucket_distinct_from_gate_bucket(self):
        """When both kinds of parked cards exist, they emit distinct lines.

        Diagnostic granularity matches the engine's elsewhere distinction
        between awaiting-human and impediment-overlay reasons.
        """
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            deck = project / ".game-of-cards" / "deck"
            deck.mkdir(parents=True)
            self._write_card(
                deck, "gated", "status: active\nhuman_gate: decision"
            )
            self._write_card(
                deck,
                "impeded",
                "status: active\nhuman_gate: none\nwaiting_on: external",
            )
            out = self._run_hook(project)
        gate_lines = [line for line in out.splitlines() if "awaiting human" in line]
        impeded_lines = [line for line in out.splitlines() if "waiting_on" in line]
        self.assertEqual(len(gate_lines), 1, out)
        self.assertEqual(len(impeded_lines), 1, out)
        self.assertIn("gated", gate_lines[0])
        self.assertNotIn("impeded", gate_lines[0])
        self.assertIn("impeded", impeded_lines[0])
        self.assertNotIn("gated", impeded_lines[0])

    def test_explicit_yaml_null_waiting_fields_are_not_an_impediment(self):
        """Explicit YAML null literals in `waiting_on`/`waiting_until` read as absent.

        The engine parses frontmatter through `yaml_lite`, whose `_NULL_SET`
        ({null, Null, NULL, ~}) resolves those literals to None, so
        `engine.waiting_impedes` returns False for `waiting_on: null`. The hook
        re-implements the parse with its own mini-frontmatter reader; before the
        fix it returned the raw token `"null"`, which `_is_impeded` mistook for a
        live reason — framing a resumable active card as
        `Impeded active card(s) — agent cannot resume` at session start.

        Pin the hook against `engine.waiting_impedes` so the two never drift.
        Reachability is the hand-edit / external-tool / pre-validate path the
        rest of this hook family already accepts (the engine never emits an
        explicit-null overlay).
        """
        import goc.engine as engine

        for field in ("waiting_on", "waiting_until"):
            for literal in ("null", "Null", "NULL", "~"):
                frontmatter = f"status: active\n{field}: {literal}"
                p = Path(
                    tempfile.NamedTemporaryFile(
                        mode="w", suffix=".md", delete=False
                    ).name
                )
                p.write_text(f"---\n{frontmatter}\n---\nbody\n", encoding="utf-8")

                card_dir = Path(tempfile.mkdtemp())
                (card_dir / "README.md").write_text(
                    f"---\n{frontmatter}\n---\nbody\n", encoding="utf-8"
                )
                engine_view = engine.waiting_impedes(engine.load_card(card_dir))

                self.assertFalse(
                    self.hook._is_impeded(p),
                    f"{field}: {literal} is an explicit YAML null, not an impediment",
                )
                self.assertEqual(
                    self.hook._is_impeded(p),
                    engine_view,
                    f"hook must agree with engine for {field}: {literal}",
                )

        # Control: a real reason still impedes (and agrees with the engine).
        p = Path(
            tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False).name
        )
        p.write_text(
            "---\nstatus: active\nwaiting_on: external\n---\nbody\n", encoding="utf-8"
        )
        self.assertTrue(self.hook._is_impeded(p))
