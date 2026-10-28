"""Check that `goc attest --skip <name>` refuses a name no configured check has.

The defect: argparse takes any string for `--skip`, and `_cmd_attest` only
asked whether each configured check was named — never whether each name was a
configured check. A typo (`--skip plceholdr` for `placeholder`) was dropped
without a word: the check it meant to skip ran anyway and was recorded as run,
while the caller believed it was skipped. Beside a valid skip the typo even
exited 0 with `Attestation OK`. Fixed, an unknown name is refused before any
check runs: exit 2, `ERROR:` on stderr naming the unknown name and listing the
configured checks, log.md untouched. A valid skip, the control, is still
recorded as `[~] … SKIPPED`.

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = the harness or
a precondition is broken.

Run with:  uv run python .game-of-cards/deck/goc-attest-silently-ignores-unknown-skip-names/reproduce.py
"""

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


REPO = _repo_root()

# `placeholder` is a manual check, so `--non-interactive` fails it whenever it
# runs; `advanced-by-closed` passes on a card with no edges. Skipping the
# first and running the second is an attestation that succeeds.
CONFIG = """layer_2_project_dod:
  - name: placeholder
    kind: manual
    description: stand-in check
    prompt: "Did the thing pass? (y/N)"
layer_3_goc_dod:
  - name: advanced-by-closed
    kind: derived
"""
CONFIGURED = ("placeholder", "advanced-by-closed")

CARD = """---
title: {slug}
summary: "Probe card for the attest --skip typo reproduction."
status: open
stage: null
contribution: low
created: "2026-05-31T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: probe.
---

# {slug}
"""

# (card, --skip names, the unknown name the refusal must report): each case on
# its own card, so a call that wrongly writes one log.md cannot make the next
# case look refused.
CASES = (
    # The typo alone: pre-fix, the check it meant to skip ran (and failed).
    ("typo", ("plceholdr",), "plceholdr"),
    # The typo beside a valid skip: pre-fix, the check the typo meant to skip
    # ran, passed, and the whole call exited 0 with `Attestation OK`.
    ("typo-beside-a-valid-skip", ("placeholder", "advanced-by-clsed"), "advanced-by-clsed"),
)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        deck_root = Path(tmp) / "deck-root"
        gocdir = deck_root / ".game-of-cards"
        deck = gocdir / "deck"
        deck.mkdir(parents=True)
        (gocdir / "config.yaml").write_text(CONFIG)
        for slug in ("control", *(case[0] for case in CASES)):
            (deck / slug).mkdir()
            (deck / slug / "README.md").write_text(CARD.format(slug=slug))
            (deck / slug / "log.md").write_text("")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
        env.pop("GOC_WORKTREE_DECK", None)

        def attest(slug: str, skips: tuple[str, ...]) -> subprocess.CompletedProcess:
            flags = [arg for name in skips for arg in ("--skip", name)]
            res = subprocess.run(
                [sys.executable, "-m", "goc.cli", "attest", slug, *flags, "--non-interactive"],
                cwd=deck_root,
                env=env,
                capture_output=True,
                text=True,
            )
            print(f"$ goc attest {slug} {' '.join(flags)} --non-interactive")
            print(f"  exit {res.returncode}")
            for line in res.stdout.strip().splitlines() or ["(empty)"]:
                print(f"  stdout: {line}")
            for line in res.stderr.strip().splitlines() or ["(empty)"]:
                print(f"  stderr: {line}")
            return res

        def log(slug: str) -> str:
            return (deck / slug / "log.md").read_text()

        # The control: a valid skip is recorded as skipped while the other
        # configured check runs and passes.
        control = attest("control", ("placeholder",))
        if (
            control.returncode != 0
            or "Attestation OK" not in control.stdout
            or "[~] placeholder SKIPPED" not in log("control")
        ):
            print("HARNESS: attesting with a valid --skip failed — the control is broken", file=sys.stderr)
            return 2

        accepted = []
        for slug, skips, unknown in CASES:
            print()
            before = log(slug)
            res = attest(slug, skips)
            refused = (
                res.returncode == 2
                and "ERROR:" in res.stderr
                and repr(unknown) in res.stderr
                and all(name in res.stderr for name in CONFIGURED)
                and "Layer-" not in res.stdout
                and log(slug) == before
            )
            if not refused:
                accepted.append(slug)
                print("  resulting log.md:")
                for line in log(slug).rstrip().splitlines():
                    print(f"    | {line}")

        if not accepted:
            print("\nFIXED: an unknown --skip name is refused before any check runs, naming the"
                  " configured checks, with nothing written; a valid skip is still recorded.")
            return 0
        print(f"\nDEFECT FIRES: unknown --skip name accepted for {', '.join(accepted)}"
              " — the check it meant to skip ran instead of being skipped.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
