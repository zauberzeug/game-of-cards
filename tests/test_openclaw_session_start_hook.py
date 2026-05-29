"""Regression tests for the openclaw-plugin `isImpeded` predicate.

The TypeScript port of `goc.engine.waiting_impedes` lives in
`openclaw-plugin/index.ts` and was drifting from the engine's
malformed-`waiting_until` safety backstop: for a bare deferral
(no `waiting_on`) with an unparseable `waiting_until`, the engine
returns True (err on the side of impeding) while the hook was
returning False — so a card hidden from the queue would still be
announced as resumable at session start.

This test extracts the relevant TS source from `index.ts` and runs
it under Node's built-in test runner with `--experimental-strip-types`
to remove TS annotations at load time. The extraction avoids needing
`npm install` (openclaw + typebox would otherwise need to resolve)
and keeps the test pinned to the actual production source.

Skipped if `node` is unavailable or the runtime is too old to support
`--experimental-strip-types`.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_TS = ROOT / "openclaw-plugin" / "index.ts"


def _extract_const_line(src: str, name: str) -> str:
    pattern = rf"^const {re.escape(name)} = [^\n]+;$"
    m = re.search(pattern, src, re.MULTILINE)
    if not m:
        raise RuntimeError(f"const {name} not found in {INDEX_TS}")
    return m.group(0)


def _extract_top_level_function(src: str, name: str) -> str:
    """Capture a top-level `function NAME(...)` block ending at the first
    line that is exactly `}` at column 0 — matches the formatting in
    openclaw-plugin/index.ts. Regenerate this extractor if the file's
    indentation convention changes.
    """
    pattern = rf"^function {re.escape(name)}\b.*?(?=^\}}$)\}}$"
    m = re.search(pattern, src, re.DOTALL | re.MULTILINE)
    if not m:
        raise RuntimeError(f"function {name} not found in {INDEX_TS}")
    return m.group(0)


def _node_supports_strip_types() -> bool:
    if shutil.which("node") is None:
        return False
    probe = subprocess.run(
        ["node", "--experimental-strip-types", "-e", "const x: number = 1;"],
        capture_output=True,
    )
    return probe.returncode == 0


# Pinned to a fixed UTC instant so the test does not rot at midnight. Same
# fixed-clock pattern as `tests/test_session_start_hook.py`'s
# `test_same_day_future_datetime_waiting_until_is_impeded`.
PINNED_NOW_ISO = "2026-05-29T12:00:00Z"

ASSERTIONS_TS = f"""
import {{ test }} from "node:test";
import assert from "node:assert/strict";

const NOW = new Date("{PINNED_NOW_ISO}");

// Bare deferral matrix — the cell the engine fix card patched.
test("bare deferral with no waiting_until is NOT impeded", () => {{
  assert.strictEqual(isImpeded("", "", NOW), false);
}});

test("bare deferral with future waiting_until is impeded", () => {{
  assert.strictEqual(isImpeded("", "2099-01-01", NOW), true);
}});

test("bare deferral with elapsed waiting_until is NOT impeded", () => {{
  assert.strictEqual(isImpeded("", "2000-01-01", NOW), false);
}});

test("bare deferral with malformed waiting_until is impeded (engine backstop)", () => {{
  // The cell the prior engine fix patched (waiting-impedes-treats-malformed-
  // waiting-until-as-no-impediment) and that this hook fix mirrors. Engine
  // err-on-the-side-of-hiding contract for pre-validate / hand-edited decks.
  assert.strictEqual(isImpeded("", "2026-99-99", NOW), true);
}});

// waiting_on-set matrix — should match the prior behavior, unaffected by this fix.
test("waiting_on=external with no waiting_until is impeded", () => {{
  assert.strictEqual(isImpeded("external", "", NOW), true);
}});

test("waiting_on=external with future waiting_until is impeded", () => {{
  assert.strictEqual(isImpeded("external", "2099-01-01", NOW), true);
}});

test("waiting_on=external with elapsed waiting_until is NOT impeded (resurfaces)", () => {{
  assert.strictEqual(isImpeded("external", "2000-01-01", NOW), false);
}});

test("waiting_on=external with malformed waiting_until is impeded", () => {{
  // Already correct pre-fix via the IMPEDED_WAITING_ON branch; pinned here to
  // detect any regression that would weaken that branch.
  assert.strictEqual(isImpeded("external", "2026-99-99", NOW), true);
}});
"""


@unittest.skipUnless(
    _node_supports_strip_types(),
    "node with --experimental-strip-types not available",
)
class OpenclawIsImpededMatrixTest(unittest.TestCase):
    """Run the TS `isImpeded` across the (waiting_on × waiting_until) matrix.

    The bare-deferral + malformed-waiting_until cell is the regression the
    fix targets; the rest of the matrix is pinned so a future change to
    the predicate doesn't silently widen the impede/no-impede boundary.
    """

    def test_isimpeded_matrix(self) -> None:
        src = INDEX_TS.read_text(encoding="utf-8")
        extracted = "\n\n".join(
            [
                _extract_const_line(src, "IMPEDED_WAITING_ON"),
                _extract_const_line(src, "ISO_DATE_RE"),
                _extract_const_line(src, "ISO_DATETIME_UTC_RE"),
                _extract_top_level_function(src, "parseWaitingUntil"),
                _extract_top_level_function(src, "isImpeded"),
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            test_ts = Path(tmp) / "is-impeded.test.ts"
            test_ts.write_text(extracted + "\n\n" + ASSERTIONS_TS, encoding="utf-8")
            result = subprocess.run(
                [
                    "node",
                    "--experimental-strip-types",
                    "--test",
                    "--test-reporter=tap",
                    str(test_ts),
                ],
                capture_output=True,
                text=True,
            )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"node test failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
