"""Regression guard: the OpenClaw goc tool's `skill` verb serves bundled skills.

OpenClaw's skill catalog advertises each skill with a host-side `location`
path that sandboxed sessions cannot read, so `openclaw-plugin/index.ts`
serves the ported bodies through the goc tool instead (verb `skill`). This
test extracts `serveGocSkill` and its helpers from `index.ts` and runs them
under `node --experimental-strip-types` against the committed
`openclaw-plugin/skills/` payload: body fetch, sibling fetch, listing,
unknown-name recovery, and path-traversal rejection.

Same extract-and-run pattern as `tests/test_openclaw_session_start_hook.py`.
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
SKILLS_DIR = ROOT / "openclaw-plugin" / "skills"


def _extract_top_level_function(src: str, name: str) -> str:
    """Capture a top-level `function NAME` / `async function NAME` block
    ending at the first line that is exactly `}` at column 0 — matches the
    formatting in openclaw-plugin/index.ts.
    """
    pattern = rf"^(?:async )?function {re.escape(name)}\b.*?(?=^\}}$)\}}$"
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


ASSERTIONS_TS = """
import { test } from "node:test";
import assert from "node:assert/strict";

test("no args lists the bundled skills", async () => {
  const r = await serveGocSkill([]);
  assert.strictEqual(r.isError, false);
  assert.match(r.content[0].text, /- card-schema/);
  assert.match(r.content[0].text, /- deck/);
});

test("one arg returns the skill body", async () => {
  const r = await serveGocSkill(["card-schema"]);
  assert.strictEqual(r.isError, false);
  assert.match(r.content[0].text, /name: card-schema/);
});

test("two args return a sibling file", async () => {
  const r = await serveGocSkill(["card-schema", "reference.md"]);
  assert.strictEqual(r.isError, false);
  assert.ok(r.content[0].text.length > 0);
});

test("unknown skill errors and lists valid names", async () => {
  const r = await serveGocSkill(["no-such-skill"]);
  assert.strictEqual(r.isError, true);
  assert.match(r.content[0].text, /- deck/);
});

test("missing sibling errors and lists available files", async () => {
  const r = await serveGocSkill(["card-schema", "no-such-file.md"]);
  assert.strictEqual(r.isError, true);
  assert.match(r.content[0].text, /reference\\.md/);
});

test("path traversal in the name is rejected", async () => {
  const r = await serveGocSkill([".."]);
  assert.strictEqual(r.isError, true);
  const dot = await serveGocSkill(["."]);
  assert.strictEqual(dot.isError, true);
});

test("path traversal in the file is rejected", async () => {
  const r = await serveGocSkill(["card-schema", "../deck/SKILL.md"]);
  assert.strictEqual(r.isError, true);
  assert.match(r.content[0].text, /invalid file path/);
});
"""


@unittest.skipUnless(
    _node_supports_strip_types(),
    "node with --experimental-strip-types not available",
)
class OpenclawSkillServingTest(unittest.TestCase):
    def test_serve_goc_skill_contract(self) -> None:
        src = INDEX_TS.read_text(encoding="utf-8")
        preamble = "\n".join(
            [
                'import { resolve, sep } from "node:path";',
                'import { access, readFile, readdir } from "node:fs/promises";',
                f"const SKILLS_DIR = {str(SKILLS_DIR)!r};",
            ]
        )
        extracted = "\n\n".join(
            [
                _extract_top_level_function(src, "pathExists"),
                _extract_top_level_function(src, "toolText"),
                _extract_top_level_function(src, "bundledSkillNames"),
                _extract_top_level_function(src, "serveGocSkill"),
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            test_ts = Path(tmp) / "serve-goc-skill.test.ts"
            test_ts.write_text(
                preamble + "\n\n" + extracted + "\n\n" + ASSERTIONS_TS,
                encoding="utf-8",
            )
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
