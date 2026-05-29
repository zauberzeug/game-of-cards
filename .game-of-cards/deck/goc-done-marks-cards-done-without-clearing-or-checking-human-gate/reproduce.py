"""Show that `goc done` (and `goc status ... disproved|superseded`) close a
card while leaving `human_gate: decision` intact, and that `goc validate`
accepts the resulting frontmatter.

Run from a clean checkout:
    uv run python .game-of-cards/deck/goc-done-marks-cards-done-without-clearing-or-checking-human-gate/reproduce.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


REPO = _repo_root()


def run(cmd, cwd):
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(cwd),
            "GIT_AUTHOR_NAME": "repro",
            "GIT_AUTHOR_EMAIL": "repro@example.com",
            "GIT_COMMITTER_NAME": "repro",
            "GIT_COMMITTER_EMAIL": "repro@example.com",
        },
    )
    return result.returncode, result.stdout, result.stderr


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "demo"
        root.mkdir()
        # Minimal scaffold so engine.DECK_DIR resolves.
        (root / ".game-of-cards" / "deck").mkdir(parents=True)
        (root / "pyproject.toml").write_text(
            "[project]\nname='demo'\nversion='0.0.0'\n"
        )

        py = sys.executable
        goc = [py, "-m", "goc.cli"]

        # Build a tiny env that lets the module import.
        import os

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO)

        def gocrun(argv):
            r = subprocess.run(
                goc + argv,
                cwd=root,
                capture_output=True,
                text=True,
                env=env,
            )
            return r.returncode, r.stdout, r.stderr

        # 1) Create a card with --gate decision and a # Decision required section.
        rc, out, err = gocrun(
            [
                "new",
                "demo-card",
                "--contribution",
                "low",
                "--gate",
                "decision",
                "--tag",
                "bug",
            ]
        )
        assert rc == 0, f"new failed: {err}"

        card = root / ".game-of-cards" / "deck" / "demo-card" / "README.md"
        text = card.read_text()
        # Replace the DoD placeholder with a satisfied criterion so `goc done`
        # will accept the close without `--force`.
        text = text.replace(
            "- [ ] (replace with real criteria)",
            "- [x] satisfied criterion",
        )
        # Add a `## Decision required` body section to mimic a real parked card.
        text = text.rstrip() + (
            "\n\n## Decision required\n\n"
            "Option A vs Option B — pending human pick.\n"
        )
        card.write_text(text)

        # Sanity-check: human_gate is still "decision" pre-close.
        assert "human_gate: decision" in text, text

        # 2) Run `goc done` on the parked card.
        rc, out, err = gocrun(["done", "demo-card"])
        print("--- goc done demo-card ---")
        print("rc =", rc)
        print("stdout:", out.rstrip())
        print("stderr:", err.rstrip())

        post = card.read_text()
        gate_line = [ln for ln in post.splitlines() if ln.startswith("human_gate:")]
        status_line = [ln for ln in post.splitlines() if ln.startswith("status:")]
        body_has_decision_required = "## Decision required" in post

        print()
        print("--- post-close frontmatter ---")
        for ln in status_line + gate_line:
            print(ln)
        print(
            "body still contains '## Decision required' section:",
            body_has_decision_required,
        )

        # 3) Show that `goc validate` accepts this contradictory state.
        rc, out, err = gocrun(["validate"])
        print()
        print("--- goc validate ---")
        print("rc =", rc)
        if out:
            print("stdout:", out.rstrip())
        if err:
            print("stderr:", err.rstrip())

        # Assertions: the bug is "the contradictory state survives close
        # AND validation."
        assert any("status: done" in ln for ln in status_line), status_line
        assert any(
            "human_gate: decision" in ln for ln in gate_line
        ), f"expected gate to survive close, got {gate_line}"
        assert body_has_decision_required, "expected '## Decision required' to survive"
        assert rc == 0, "expected `goc validate` to silently accept the contradiction"

        print()
        print("DEFECT CONFIRMED:")
        print("  status: done AND human_gate: decision coexist on the closed card,")
        print("  the unresolved `## Decision required` body section survives,")
        print("  and `goc validate` exits 0 with no warning.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
