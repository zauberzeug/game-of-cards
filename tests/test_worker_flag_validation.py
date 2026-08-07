"""Worker-flag values must satisfy the frontmatter contract at the CLI boundary.

`validate_card` refuses an empty or whitespace-only `worker` (and the same for
its `who` / `where` sub-keys), and `worker` has no block-scalar form, so
`_emit_worker` sends every scalar through `_yaml_inline`, which refuses any line
break. Neither constraint used to be checked where the values enter:

* `goc new --worker "   "` and `goc status <t> active --worker-who/--worker-where
  "   "` each wrote the blank value, printed a success line, exited 0 — and left
  a card the engine's own `goc validate` then rejected.
* `goc status`'s two flags reached `_yaml_inline` unguarded, so a line-break
  value raised a bare `FrontmatterError` traceback instead of `ERROR:` + exit 2.

`_reject_invalid_worker_flag` now runs at verb entry, above every disk read.
These tests pin both halves of the contract — the clean refusal, and the part a
"did it fail?" assertion would miss: that the target card is left untouched, so
a refused claim never strands a half-mutated or validate-red card.

The `new` / `status` asymmetry on the empty string is deliberate. `new --worker`
shares its argparse dest with the global `--worker` queue filter (default
`$GOC_WORKER`), where "" is the "no worker supplied" sentinel; `status`'s flags
default to None when omitted, so "" there is explicit user input.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BLANKS = ["", "   ", "\t", " \t "]
# One per character str.splitlines() breaks on. `worker` has no block-scalar
# form, so LF is refused alongside the rest.
BREAKS = ["\n", "\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", " ", " "]


class WorkerFlagValidationTest(unittest.TestCase):
    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        # The global --worker filter defaults to $GOC_WORKER and shares a dest
        # with `new --worker`; an ambient value would mask what these assert.
        env.pop("GOC_WORKER", None)
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def make_repo(self, tmp: str) -> Path:
        repo = Path(tmp)
        (repo / ".game-of-cards" / "deck").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
        return repo

    def assert_clean_refusal(self, result: subprocess.CompletedProcess[str], expect: str) -> None:
        self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
        self.assertNotIn("Traceback (most recent call last)", result.stderr)
        self.assertTrue(
            result.stderr.startswith("ERROR:"),
            msg=f"expected a clean ERROR: line, got {result.stderr!r}",
        )
        self.assertIn(expect, result.stderr)

    # ---- goc new --worker ------------------------------------------------

    def test_new_worker_whitespace_only_is_refused_before_mkdir(self) -> None:
        for blank in [b for b in BLANKS if b]:
            with self.subTest(value=repr(blank)):
                with tempfile.TemporaryDirectory() as tmp:
                    repo = self.make_repo(tmp)
                    result = self.run_goc(
                        repo, "new", "blank-worker-probe", "--gate", "none",
                        "--summary", "emittable summary", "--worker", blank,
                    )
                    self.assert_clean_refusal(
                        result, "--worker must not be empty or whitespace-only"
                    )
                    self.assertFalse(
                        (repo / ".game-of-cards" / "deck" / "blank-worker-probe").exists(),
                        msg="refused `goc new` stranded a card directory",
                    )

    def test_new_worker_empty_string_stays_the_no_worker_sentinel(self) -> None:
        """`new --worker` shares a dest with the global filter, whose default is
        `$GOC_WORKER`; "" means "not supplied" and must scaffold a worker-less
        card rather than erroring."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(tmp)
            result = self.run_goc(
                repo, "new", "empty-worker-sentinel", "--gate", "none",
                "--summary", "emittable summary", "--worker", "",
            )
            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            readme = repo / ".game-of-cards" / "deck" / "empty-worker-sentinel" / "README.md"
            self.assertNotIn("worker:", readme.read_text())

    # ---- goc status --worker-who / --worker-where ------------------------

    def scaffold_open_card(self, repo: Path, title: str) -> Path:
        result = self.run_goc(
            repo, "new", title, "--gate", "none", "--summary", "emittable summary"
        )
        self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
        return repo / ".game-of-cards" / "deck" / title / "README.md"

    def assert_claim_refused_and_card_untouched(self, flag: str, value: str, expect: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(tmp)
            readme = self.scaffold_open_card(repo, "claim-guard-probe")
            before = readme.read_text()

            result = self.run_goc(
                repo, "status", "claim-guard-probe", "active", flag, value, "--no-commit"
            )

            self.assert_clean_refusal(result, expect)
            # The whole point of guarding at entry: a refused claim must not
            # flip status, stamp a worker, or clear the draft flag.
            self.assertEqual(before, readme.read_text(), msg=f"{flag} refusal mutated the card")
            self.assertIn("status: open", before)
            self.assertNotIn("worker:", before)

    def test_claim_with_blank_worker_who_is_refused_and_leaves_card_untouched(self) -> None:
        for blank in BLANKS:
            with self.subTest(value=repr(blank)):
                self.assert_claim_refused_and_card_untouched(
                    "--worker-who", blank, "--worker-who must not be empty or whitespace-only"
                )

    def test_claim_with_blank_worker_where_is_refused_and_leaves_card_untouched(self) -> None:
        for blank in BLANKS:
            with self.subTest(value=repr(blank)):
                self.assert_claim_refused_and_card_untouched(
                    "--worker-where", blank, "--worker-where must not be empty or whitespace-only"
                )

    def test_claim_with_line_break_worker_who_is_refused_without_a_traceback(self) -> None:
        for ch in BREAKS:
            with self.subTest(char=repr(ch)):
                self.assert_claim_refused_and_card_untouched(
                    "--worker-who", f"alice{ch}bob",
                    "--worker-who must not contain a line break",
                )

    def test_claim_with_line_break_worker_where_is_refused_without_a_traceback(self) -> None:
        for ch in BREAKS:
            with self.subTest(char=repr(ch)):
                self.assert_claim_refused_and_card_untouched(
                    "--worker-where", f"feature{ch}foo",
                    "--worker-where must not contain a line break",
                )

    def test_trailing_carriage_return_from_a_crlf_paste_is_refused(self) -> None:
        """The realistic door: `--worker-who "$(cat identity)"` on a CRLF file.
        Command substitution strips a trailing LF but not the CR."""
        self.assert_claim_refused_and_card_untouched(
            "--worker-who", "alice\r", "--worker-who must not contain a line break"
        )

    # ---- the guard must not widen ----------------------------------------

    def test_ordinary_worker_overrides_still_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(tmp)
            readme = self.scaffold_open_card(repo, "ordinary-claim-probe")

            result = self.run_goc(
                repo, "status", "ordinary-claim-probe", "active",
                "--worker-who", "alice", "--worker-where", "feature/foo", "--no-commit",
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            text = readme.read_text()
            self.assertIn("status: active", text)
            self.assertIn("worker: {who: alice, where: feature/foo}", text)

    def test_who_only_override_still_claims_as_a_flat_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(tmp)
            readme = self.scaffold_open_card(repo, "who-only-claim-probe")

            result = self.run_goc(
                repo, "status", "who-only-claim-probe", "active",
                "--worker-who", "alice", "--no-commit",
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("status: active", readme.read_text())

    def test_omitted_worker_flags_still_auto_populate(self) -> None:
        """Both flags default to None; the guard must skip them entirely so the
        git-identity auto-detection path is unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(tmp)
            readme = self.scaffold_open_card(repo, "auto-claim-probe")

            result = self.run_goc(
                repo, "status", "auto-claim-probe", "active", "--no-commit"
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            text = readme.read_text()
            self.assertIn("status: active", text)
            self.assertIn("Test User", text)

    def test_claimed_card_passes_validate(self) -> None:
        """The regression in one line: whatever a successful claim writes, the
        engine's own validator must accept."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(tmp)
            self.scaffold_open_card(repo, "validate-after-claim-probe")
            self.run_goc(
                repo, "status", "validate-after-claim-probe", "active",
                "--worker-who", "alice", "--worker-where", "main", "--no-commit",
            )

            validate = self.run_goc(repo, "validate")
            self.assertNotIn("worker:", validate.stdout + validate.stderr)
            self.assertEqual(0, validate.returncode, msg=validate.stdout + validate.stderr)


if __name__ == "__main__":
    unittest.main()
