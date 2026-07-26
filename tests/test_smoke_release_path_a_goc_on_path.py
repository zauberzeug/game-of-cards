from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "smoke_release.sh"


def _path_a_body(text: str) -> str:
    """Return the body of `run_path_a`, up to the next top-level `}`."""
    start = text.index("run_path_a() {")
    end = text.index("\n}", start)
    return text[start:end]


class SmokeReleasePathAGocOnPathTest(unittest.TestCase):
    """Path A must not launch its agent run on an unestablished premise.

    `run_path_a` installs `goc` with `uv tool install`, then sends a prompt
    asserting "goc is on PATH". `uv tool install` places the console script in
    uv's tool-bin directory but does not put that directory on PATH — the CI
    job this script mirrors adds it explicitly
    (`echo "$HOME/.local/bin" >> $GITHUB_PATH`). Without either that step or a
    resolvability guard, a machine whose shell lacks uv's bin dir on PATH burns
    a 30-turn agent run and then reports `FAIL Path A: deck dir not created` —
    naming the plugin payload for a harness gap.
    """

    def setUp(self) -> None:
        self.text = SCRIPT.read_text()
        self.path_a = _path_a_body(self.text)

    def test_path_a_prompt_asserts_goc_is_on_path(self) -> None:
        # Anchors the rest of this test: the guard is required *because* the
        # prompt makes the claim. If the prompt stops claiming it, revisit.
        self.assertIn("goc is on PATH", self.path_a)

    def test_path_a_extends_path_with_uv_tool_bin_dir(self) -> None:
        self.assertRegex(
            self.path_a,
            r"uv tool dir --bin",
            "Path A must ask uv where it installed the console script rather "
            "than hardcoding ~/.local/bin (UV_TOOL_BIN_DIR can move it).",
        )
        self.assertRegex(
            self.path_a,
            r"export PATH=\"\$goc_bin_dir:\$PATH\"",
            "Path A must prepend uv's tool-bin dir to PATH, mirroring the CI "
            "job's $GITHUB_PATH step.",
        )

    def test_path_a_fails_fast_when_goc_does_not_resolve(self) -> None:
        self.assertRegex(
            self.path_a,
            r"if ! command -v goc >/dev/null 2>&1; then",
            "Path A must guard `goc` resolvability with the same idiom the "
            "script already uses for `claude`, so a missing prerequisite is "
            "reported before any agent turn is spent.",
        )
        # The guard has to abort, not warn: a warning still spends the run.
        guard = self.path_a[self.path_a.index("if ! command -v goc"):]
        self.assertIn("exit 1", guard.split("fi", 1)[0])

    def test_path_a_guard_precedes_the_agent_invocation(self) -> None:
        self.assertLess(
            self.path_a.index("command -v goc"),
            self.path_a.index("claude -p"),
            "The resolvability guard must run before the agent is launched.",
        )

    def test_script_is_valid_bash_and_guard_aborts_without_goc(self) -> None:
        """Execute the real guard logic with an empty PATH; it must exit 1."""
        self.assertEqual(
            subprocess.run(
                ["bash", "-n", str(SCRIPT)], capture_output=True, text=True,
            ).returncode,
            0,
            "smoke_release.sh must parse as valid bash",
        )

        # Re-run the guard in isolation under the script's own `set -euo
        # pipefail`, with a PATH that resolves neither `uv` nor `goc`. Proves
        # the guard aborts (rather than falling through to `claude -p`) and
        # that the empty-`uv tool dir` branch does not trip `set -e`.
        guard = self.path_a[self.path_a.index("    local goc_bin_dir"):]
        guard = guard[: guard.index("    ( cd \"$workdir\"")]
        bash = shutil.which("bash")
        self.assertIsNotNone(bash, "bash is required to run this test")
        with tempfile.TemporaryDirectory() as empty_bin:
            script = (
                "set -euo pipefail\n"
                f"REPO_ROOT={ROOT}\n"
                "run_path_a() {\n" + guard + "\n}\n"
                "run_path_a\n"
                "echo REACHED-AGENT-LAUNCH\n"
            )
            # PATH holds only an empty dir, so neither `uv` nor `goc` resolves.
            # bash is invoked by absolute path so the shell itself still starts.
            r = subprocess.run(
                [bash, "-c", script],
                capture_output=True, text=True, env={"PATH": empty_bin},
            )
        self.assertEqual(r.returncode, 1, f"expected the guard to abort; got {r!r}")
        self.assertNotIn("REACHED-AGENT-LAUNCH", r.stdout)
        self.assertIn("goc not on PATH", r.stderr)

    def test_reproduce_script_exits_zero(self) -> None:
        card = (
            ROOT / ".game-of-cards" / "deck"
            / "release-smoke-script-launches-path-a-without-putting-goc-on-path"
            / "reproduce.py"
        )
        if not card.exists():  # pragma: no cover - card dir may be pruned
            self.skipTest(f"{card} not present")
        r = subprocess.run(
            [sys.executable, str(card)], capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(r.returncode, 0, f"reproduce.py still fails:\n{r.stdout}\n{r.stderr}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
