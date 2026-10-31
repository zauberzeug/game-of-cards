"""Regression guard: OpenClaw's prompt hook is silent in a workspace without a deck.

The `before_prompt_build` handler in `openclaw-plugin/index.ts` ports
`goc/templates/hooks/deck_prompt_router.py`. The plugin's hooks run in every
workspace, so the handler may append the deck-first reminder only where the
session's project dir holds a deck — `.game-of-cards/deck/` or the legacy
`deck/` — the rule the Python router follows ("Every runtime hook is inert in
a repo that never opted in", AGENTS.md). Before the fix the handler appended
the reminder to every work-shaped prompt, opted in or not
(`openclaw-prompt-hook-fires-in-workspaces-without-a-deck`).

This test extracts the handler, the prompt patterns, the reminder, and the
deck helpers from `index.ts` and runs them under
`node --experimental-strip-types` against a fake `api` and real temporary
directories, so it pins the production source rather than a copy of it.

Same extract-and-run pattern as `tests/test_openclaw_session_start_hook.py`.
Skipped if `node` is unavailable or too old for `--experimental-strip-types`.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_TS = ROOT / "openclaw-plugin" / "index.ts"


def _extract_const(src: str, name: str) -> str:
    """Capture a top-level `const NAME = ...;` statement, one line or many,
    ending at the first line that ends in `;` — matches the formatting in
    openclaw-plugin/index.ts, where array items end in `,`.
    """
    m = re.search(rf"^const {re.escape(name)}\b.*?;$", src, re.DOTALL | re.MULTILINE)
    if not m:
        raise RuntimeError(f"const {name} not found in {INDEX_TS}")
    return m.group(0)


def _extract_top_level_function(src: str, name: str) -> str:
    """Capture a top-level `function NAME` / `async function NAME` block
    ending at the first line that is exactly `}` at column 0.
    """
    pattern = rf"^(?:async )?function {re.escape(name)}\b.*?(?=^\}}$)\}}$"
    m = re.search(pattern, src, re.DOTALL | re.MULTILINE)
    if not m:
        raise RuntimeError(f"function {name} not found in {INDEX_TS}")
    return m.group(0)


def _extract_hook_registration(src: str, hook: str) -> str:
    """Capture the `api.on("<hook>", ...)` call inside `register(api)`,
    ending at the `});` that sits at the call's own indentation.
    """
    pattern = rf'^( *)api\.on\("{re.escape(hook)}".*?^\1\}}\);$'
    m = re.search(pattern, src, re.DOTALL | re.MULTILINE)
    if not m:
        raise RuntimeError(f'api.on("{hook}", ...) not found in {INDEX_TS}')
    return m.group(0)


def _node_supports_strip_types() -> bool:
    if shutil.which("node") is None:
        return False
    probe = subprocess.run(
        ["node", "--experimental-strip-types", "-e", "const x: number = 1;"],
        capture_output=True,
    )
    return probe.returncode == 0


# The extracted registration runs inside this harness the way it runs inside
# `register(api)`: `api.on` records the handler, and `sessionProjectDir` is the
# closure variable session_start fills in.
HARNESS_TS = """
const handlers = new Map<string, (ctx: any) => Promise<void>>();
const api = { on: (name: string, fn: (ctx: any) => Promise<void>) => { handlers.set(name, fn); } };
let sessionProjectDir: string | undefined;
"""

ASSERTIONS_TS = """
import { test } from "node:test";
import assert from "node:assert/strict";

const WORK_PROMPT = "Please fix the login redirect bug";

// Runs the registered handler with a host context that records what it was
// given, through whichever context method `use` names.
async function reminders(prompt: string, use: "append" | "prepend" = "append"): Promise<string[]> {
  const got: string[] = [];
  const ctx: any = { userPrompt: prompt };
  if (use === "append") ctx.appendSystemContext = (s: string) => got.push(s);
  else ctx.prependSystemContext = (s: string) => got.push(s);
  await handlers.get("before_prompt_build")!(ctx);
  return got;
}

test("the prompt is work-shaped, so a deck decides alone", () => {
  assert.ok(WORK_INITIATING.some((re) => re.test(WORK_PROMPT.toLowerCase())));
});

test("no reminder for a work-shaped prompt in a workspace without a deck", async () => {
  sessionProjectDir = DIRS.none;
  assert.deepStrictEqual(await reminders(WORK_PROMPT), []);
  assert.deepStrictEqual(await reminders(WORK_PROMPT, "prepend"), []);
});

test("the reminder, unchanged, in a workspace with .game-of-cards/deck/", async () => {
  sessionProjectDir = DIRS.canonical;
  assert.deepStrictEqual(await reminders(WORK_PROMPT), [DECK_REMINDER]);
  assert.deepStrictEqual(await reminders(WORK_PROMPT, "prepend"), [DECK_REMINDER]);
  assert.match(DECK_REMINDER, /^\\[Game of Cards \\| runtime active\\]\\n/);
});

test("the legacy deck/ opts a workspace in too", async () => {
  sessionProjectDir = DIRS.legacy;
  assert.deepStrictEqual(await reminders(WORK_PROMPT), [DECK_REMINDER]);
});

test("a .game-of-cards/ without its deck/ is not a deck", async () => {
  sessionProjectDir = DIRS.configOnly;
  assert.deepStrictEqual(await reminders(WORK_PROMPT), []);
});

test("before session_start records a project dir, the process cwd decides", async () => {
  sessionProjectDir = undefined;
  const before = process.cwd();
  try {
    process.chdir(DIRS.none);
    assert.deepStrictEqual(await reminders(WORK_PROMPT), []);
    process.chdir(DIRS.canonical);
    assert.deepStrictEqual(await reminders(WORK_PROMPT), [DECK_REMINDER]);
  } finally {
    process.chdir(before);
  }
});

test("prompts that are not work-shaped stay silent even with a deck", async () => {
  sessionProjectDir = DIRS.canonical;
  for (const prompt of ["", "explain how the router works", "git status", "thanks!"]) {
    assert.deepStrictEqual(await reminders(prompt), [], prompt);
  }
});
"""


@unittest.skipUnless(
    _node_supports_strip_types(),
    "node with --experimental-strip-types not available",
)
class OpenclawPromptHookDeckGuardTest(unittest.TestCase):
    def test_reminder_requires_a_deck(self) -> None:
        src = INDEX_TS.read_text(encoding="utf-8")
        extracted = "\n\n".join(
            [
                'import { resolve } from "node:path";',
                'import { access } from "node:fs/promises";',
                *(
                    _extract_const(src, name)
                    for name in ("WORK_VERBS", "WORK_INITIATING", "EXPLORATION", "TOOLING", "DECK_REMINDER")
                ),
                _extract_top_level_function(src, "pathExists"),
                _extract_top_level_function(src, "hasDeck"),
                HARNESS_TS,
                _extract_hook_registration(src, "before_prompt_build"),
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            dirs = {
                "none": Path(tmp, "none"),
                "canonical": Path(tmp, "canonical"),
                "legacy": Path(tmp, "legacy"),
                "configOnly": Path(tmp, "config-only"),
            }
            dirs["none"].mkdir()
            (dirs["canonical"] / ".game-of-cards" / "deck").mkdir(parents=True)
            (dirs["legacy"] / "deck").mkdir(parents=True)
            (dirs["configOnly"] / ".game-of-cards").mkdir(parents=True)
            (dirs["configOnly"] / ".game-of-cards" / "config.yaml").write_text("{}\n", encoding="utf-8")
            dirs_ts = f"const DIRS = {json.dumps({k: str(v) for k, v in dirs.items()})};"

            test_ts = Path(tmp, "prompt-hook.test.ts")
            test_ts.write_text(
                extracted + "\n\n" + dirs_ts + "\n" + ASSERTIONS_TS, encoding="utf-8"
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
