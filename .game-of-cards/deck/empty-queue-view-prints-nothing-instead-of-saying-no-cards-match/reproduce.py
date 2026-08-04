#!/usr/bin/env python3
"""Empty-result queue views print nothing; every sibling view says so.

Builds a three-card scratch deck, then renders the same zero-match query
through each of goc's four read surfaces. The table path is the only one
that emits no output at all — and the *reason* the blank is dangerous is
that it is byte-identical across a genuinely drained queue, a zero-match
filter, and a typo'd `--worker` value.

Exits 0 once the table path announces the empty result like its siblings.
"""

from __future__ import annotations

import os
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))


def run(deck_repo: Path, *argv: str) -> tuple[int, str]:
    """Run `goc <argv>` against the scratch repo; return (exit code, stdout+stderr)."""
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *argv],
        cwd=str(deck_repo), env=env, capture_output=True, text=True, check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


def build_deck(tmp: Path) -> Path:
    """A scratch repo whose three open cards are all parked behind a human gate."""
    (tmp / ".game-of-cards" / "deck").mkdir(parents=True)
    (tmp / ".game-of-cards" / "config.yaml").write_text("auto_commit: false\n")
    (tmp / "pyproject.toml").write_text('[project]\nname = "scratch"\n')
    for title in ("alpha", "beta", "gamma"):
        run(tmp, "new", title, "--summary", f"Summary for {title}.", "--gate", "decision")
        run(tmp, "publish", title)
    return tmp


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        deck_repo = build_deck(Path(td))

        # Every card is gate-parked, so the ready queue is legitimately empty.
        probes = [
            ("table  `goc --ready`", ("--ready",)),
            ("table  `goc --status disproved`", ("--status", "disproved")),
            ("table  `goc --ready --worker typo`", ("--ready", "--worker", "no-such-worker")),
            ("json   `goc --json --ready`", ("--json", "--ready")),
            ("board  `goc --board --status disproved`", ("--board", "--status", "disproved")),
            ("triage `goc triage --worker typo`", ("triage", "--worker", "no-such-worker")),
        ]

        print("zero-match query → what the reader sees\n")
        silent: list[str] = []
        outputs: dict[str, str] = {}
        for label, argv in probes:
            code, out = run(deck_repo, *argv)
            outputs[label] = out
            first = out.strip().splitlines()[0] if out.strip() else ""
            shown = f"{first[:58]!r}" if first else "(nothing)"
            print(f"  exit {code}  {len(out):>4} bytes  {label:<42} {shown}")
            if label.startswith("table") and not out.strip():
                silent.append(label)

        print()
        table_blanks = [outputs[l] for l, _ in probes if l.startswith("table")]
        identical = len(set(table_blanks)) == 1
        print(f"  the three table probes are byte-identical: {identical}")
        print("    a drained queue, a zero-match status filter and a typo'd --worker")
        print("    are indistinguishable to the reader and to Skill(pull-card).")

        print(f"\n{len(silent)} table view(s) reported an empty result with no output.")
        if silent:
            for label in silent:
                print(f"  - {label}")
            print(
                "\nFAIL: the table path stays silent while `triage` prints a sentence, "
                "`--json` prints [] and `--board` prints its header."
            )
            return 1
        print("\nOK: the table path announces an empty result like its siblings.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
