"""Regression guard: every `waiting_on` int-coercion mirror tracks yaml-lite.

`goc._vendor.yaml_lite._INT_RE` is the canonical "which bare scalar does the
parser coerce to `int`" predicate. Two SessionStart hook ports re-declare it
because they must reproduce `Card.waiting_on`'s `isinstance(v, str)` guard
without importing the package:

  * `goc/templates/hooks/deck_session_start.py` (Claude Code / Codex), and its
    byte-for-byte mirrors under `.claude/hooks/`, `claude-plugin/hooks/`,
    `codex-plugin/hooks/` (enforced by `test_plugin_mirror_parity`);
  * `openclaw-plugin/index.ts` and its committed esbuild output
    `openclaw-plugin/dist/index.js`.

When yaml-lite narrowed `_INT_RE` from `^-?\\d+$` to `^-?(0|[1-9][0-9]*)$` so
leading-zero runs stay strings, neither copy was swept. The result: a
hand-edited `waiting_on: 007` is a live reason to the engine (card impeded) but
an integer to the hooks (card announced as resumable) — the two surfaces
disagreeing in the unsafe direction.

The assertions below read the canonical pattern *from the engine* rather than
hard-coding it a fourth time, so the next change to `yaml_lite._INT_RE` turns
the build red instead of drifting silently.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402
from goc._vendor import yaml_lite  # noqa: E402

HOOK_TEMPLATE = ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py"
TS_ENTRY = ROOT / "openclaw-plugin" / "index.ts"
TS_BUNDLE = ROOT / "openclaw-plugin" / "dist" / "index.js"

CANONICAL = yaml_lite._INT_RE.pattern

CARD = """\
---
title: c
summary: s
status: active
stage: null
contribution: medium
created: 2026-01-01
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: []
waiting_on: {value}
definition_of_done: |
  - [ ] x
---

# c
"""

# Bare `waiting_on` tokens whose int-vs-string classification decides whether
# the card is impeded. The leading-zero runs are the regression; the rest are
# controls that must keep their existing verdict.
CASES = ("007", "00", "0123", "0", "-0", "42", "-7", "external")


def _load_hook():
    spec = importlib.util.spec_from_file_location("_goc_hook_under_test", HOOK_TEMPLATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class WaitingOnIntMirrorTest(unittest.TestCase):
    def test_python_hook_int_re_mirrors_yaml_lite(self) -> None:
        hook = _load_hook()
        self.assertEqual(
            hook._INT_RE.pattern,
            CANONICAL,
            msg=(
                f"{HOOK_TEMPLATE.relative_to(ROOT)}: _INT_RE must equal "
                f"yaml_lite._INT_RE ({CANONICAL!r}). A wider pattern coerces a "
                "hand-edited leading-zero waiting_on to absent and announces an "
                "impeded card as resumable."
            ),
        )

    def test_openclaw_entry_int_re_mirrors_yaml_lite(self) -> None:
        m = re.search(r"^const INT_RE = /(.+)/;$", TS_ENTRY.read_text(), re.MULTILINE)
        self.assertIsNotNone(
            m, msg=f"{TS_ENTRY.relative_to(ROOT)}: `const INT_RE = /.../;` not found"
        )
        self.assertEqual(
            m.group(1),
            CANONICAL,
            msg=(
                f"{TS_ENTRY.relative_to(ROOT)}: INT_RE must equal "
                f"yaml_lite._INT_RE ({CANONICAL!r})."
            ),
        )

    def test_openclaw_bundle_carries_the_current_int_re(self) -> None:
        """The committed esbuild output is what OpenClaw actually loads.

        Editing `index.ts` without `npm run build` ships the stale predicate,
        so pin the bundle too rather than trusting the source alone.
        """
        self.assertTrue(
            TS_BUNDLE.exists(), msg=f"{TS_BUNDLE.relative_to(ROOT)} is missing"
        )
        self.assertIn(
            f"var INT_RE = /{CANONICAL}/;",
            TS_BUNDLE.read_text(),
            msg=(
                f"{TS_BUNDLE.relative_to(ROOT)}: bundle carries a stale INT_RE — "
                "rebuild with `cd openclaw-plugin && npm ci && npm run build`."
            ),
        )

    def test_hook_impediment_verdict_matches_engine(self) -> None:
        hook = _load_hook()
        card_dir = Path(tempfile.mkdtemp()) / "c"
        card_dir.mkdir()
        readme = card_dir / "README.md"
        for value in CASES:
            with self.subTest(waiting_on=value):
                readme.write_text(CARD.format(value=value))
                expected = engine.waiting_impedes(engine.load_card(card_dir))
                self.assertEqual(
                    hook._is_impeded(readme),
                    expected,
                    msg=(
                        f"waiting_on: {value} — hook disagrees with "
                        "engine.waiting_impedes"
                    ),
                )

    def test_leading_zero_reason_is_a_live_impediment(self) -> None:
        """Anchor the specific regression, independent of the differential.

        If both the engine and the hook ever stopped impeding `007`, the
        differential above would pass while the contract silently changed.
        """
        card_dir = Path(tempfile.mkdtemp()) / "c"
        card_dir.mkdir()
        readme = card_dir / "README.md"
        readme.write_text(CARD.format(value="007"))
        card = engine.load_card(card_dir)
        self.assertEqual(card.waiting_on, "007")
        self.assertTrue(engine.waiting_impedes(card))
        self.assertTrue(_load_hook()._is_impeded(readme))


if __name__ == "__main__":
    unittest.main()
