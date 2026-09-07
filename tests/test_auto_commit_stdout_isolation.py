"""Regression: `_git_auto_commit` owns goc's stdout — git writes nowhere near it.

`git add` / `git commit` used to run without `capture_output=True`, the only two
`subprocess.run` calls in `goc/engine.py` that did. The child inherited goc's
stdout and wrote to it immediately while CPython block-buffered goc's own
prints, so under a pipe — agent tool capture, CI logs, `goc … | head` — the
porcelain summary arrived AHEAD of the verb line that announced the mutation.

Two halves are pinned here, and the second is what keeps the first honest:

1. A piped auto-committing verb emits only goc's own lines, in code order.
2. A FAILING commit still reports git's diagnostic. Capturing output must not
   turn a refusing pre-commit hook into a silent no-op — that would trade the
   leak for a worse defect.

Card: deck-auto-commit-prints-raw-git-output-before-the-verbs-own-report
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# `git commit`'s porcelain summary — the `[branch sha] subject` header, the
# diffstat, and the create/delete mode lines. None of it is goc output.
PORCELAIN = (
    re.compile(r"^\[[^\]]+ [0-9a-f]{7,}\] "),
    re.compile(r"^ \d+ files? changed"),
    re.compile(r"^ (create|delete) mode \d+ "),
)


class AutoCommitStdoutIsolationTest(unittest.TestCase):
    def goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"
        # capture_output is the point of the test: it makes stdout a pipe, the
        # shape that block-buffers goc's prints behind an uncaptured child's.
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
        )

    def seed(self, repo: Path) -> None:
        """Committed two-card deck with `auto_commit` at its shipped default."""
        subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "probe@example.invalid"], cwd=repo, check=True
        )
        subprocess.run(["git", "config", "user.name", "probe"], cwd=repo, check=True)
        (repo / ".game-of-cards" / "deck").mkdir(parents=True)
        (repo / ".game-of-cards" / "config.yaml").write_text("workflow:\n  auto_commit: true\n")
        for title in ("alpha", "beta"):
            result = self.goc(repo, "new", title, "--summary", "probe card", "--gate", "none")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            readme = repo / ".game-of-cards" / "deck" / title / "README.md"
            # Author, then publish: `_git_auto_commit` drops draft scaffolds, so
            # an unpublished card never reaches the commit under test.
            readme.write_text(
                readme.read_text()
                .replace("- [ ] (replace with real criteria)", "- [ ] MECHANICAL: real criterion")
                .replace("(write the design doc here)", "Body.")
            )
            result = self.goc(repo, "publish", title, "--no-commit")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "seed"], cwd=repo, check=True)

    def test_auto_committing_verbs_emit_only_goc_lines_in_order(self):
        # One case per auto-commit entry shape: the claim that opens every
        # pull-card session, an overlay write, and a two-endpoint edge write.
        cases = [
            (["status", "alpha", "active"], "alpha: open → active"),
            (["wait", "alpha", "--reason", "external"], "alpha: waiting_on='external'"),
            (["advance", "alpha", "--by", "beta"], "advance: alpha.advanced_by += beta"),
        ]
        for args, first_line_prefix in cases:
            with self.subTest(verb=" ".join(args)):
                with tempfile.TemporaryDirectory() as tmp:
                    repo = Path(tmp)
                    self.seed(repo)
                    result = self.goc(repo, *args)
                    self.assertEqual(result.returncode, 0, msg=result.stderr)
                    lines = result.stdout.splitlines()

                    self.assertIn(
                        "  committed", lines,
                        msg=f"no commit landed; case did not exercise the path:\n{result.stdout}",
                    )
                    leaked = [ln for ln in lines if any(p.match(ln) for p in PORCELAIN)]
                    self.assertEqual(
                        leaked, [],
                        msg=f"git porcelain reached goc's stdout:\n{result.stdout}",
                    )
                    self.assertTrue(
                        lines[0].startswith(first_line_prefix),
                        msg=(
                            f"verb report is not the first stdout line "
                            f"(expected {first_line_prefix!r}):\n{result.stdout}"
                        ),
                    )

    def test_failing_commit_still_reports_gits_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.seed(repo)
            # A refusing pre-commit hook is the realistic failure: this repo's
            # own hook chain runs goc validate and the mirror sync, either of
            # which can reject the commit an auto-committing verb attempts.
            hook = repo / ".git" / "hooks" / "pre-commit"
            hook.write_text(
                "#!/bin/sh\n"
                "echo HOOK-REFUSED-ON-STDOUT\n"
                "echo HOOK-REFUSED-ON-STDERR >&2\n"
                "exit 1\n"
            )
            hook.chmod(0o755)

            result = self.goc(repo, "status", "alpha", "active")

            self.assertIn("auto-commit failed", result.stderr)
            self.assertIn(
                "HOOK-REFUSED-ON-STDOUT", result.stderr,
                msg=f"captured hook stdout was swallowed:\n{result.stderr}",
            )
            self.assertIn(
                "HOOK-REFUSED-ON-STDERR", result.stderr,
                msg=f"captured hook stderr was swallowed:\n{result.stderr}",
            )
            # The mutation itself still landed on disk — an auto-commit failure
            # is non-fatal by contract and must not roll the state flip back.
            self.assertIn("alpha: open → active", result.stdout)
            readme = repo / ".game-of-cards" / "deck" / "alpha" / "README.md"
            self.assertIn("status: active", readme.read_text())

    def test_no_goc_module_leaves_a_child_on_gocs_stdout(self):
        """No subprocess in the shipped package may inherit goc's stdout.

        The source-level half of the same contract. The behavioral tests above
        only reach `_git_auto_commit`'s three entry shapes, so a new uncaptured
        call — in that function or anywhere else — would reintroduce the exact
        interleaving without turning anything red.

        Scoped to the whole package, not just `engine.py`, because the
        invariant is about the CLI's output contract rather than about one
        file: `engine.py` happens to be the only module that spawns children
        today, and a future `install.py` shelling out to git would break the
        same contract in the same way. Hook templates are included — they run
        as agent lifecycle hooks whose stdout the host reads as the hook's
        result.
        """
        modules = sorted(
            p for p in (ROOT / "goc").rglob("*.py")
            if "__pycache__" not in p.parts
        )
        self.assertTrue(modules, "no goc modules found — scope resolution broke")

        # Any spawning API, not just `run`: `Popen`/`call`/`check_call` inherit
        # stdout exactly the same way.
        spawn = re.compile(r"subprocess\.(run|call|check_call|Popen)\(")
        offenders: list[str] = []
        for path in modules:
            text = path.read_text()
            for match in spawn.finditer(text):
                depth = 0
                for j in range(match.end() - 1, len(text)):
                    if text[j] == "(":
                        depth += 1
                    elif text[j] == ")":
                        depth -= 1
                        if depth == 0:
                            break
                call = text[match.start(): j + 1]
                if "capture_output=True" in call or "stdout=" in call:
                    continue
                line_no = text.count("\n", 0, match.start()) + 1
                rel = path.relative_to(ROOT)
                offenders.append(f"{rel}:{line_no}: {' '.join(call.split())[:90]}")
        self.assertEqual(
            offenders, [],
            msg=(
                "a subprocess without capture_output=/stdout= inherits goc's stdout; "
                "under a pipe the child's output lands ahead of goc's own buffered "
                "lines:\n  " + "\n  ".join(offenders)
            ),
        )


if __name__ == "__main__":
    unittest.main()
