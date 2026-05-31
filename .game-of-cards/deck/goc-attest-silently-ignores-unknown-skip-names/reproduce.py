"""Demonstrate that `goc attest --skip <typo>` silently accepts unknown skip names.

Builds a temp deck with one configured Layer-2 manual check, runs
`goc attest <card> --skip <typo> --non-interactive`, and asserts:

  - The CLI prints no "unknown skip name" error.
  - The configured check ran (not marked SKIPPED).

Exit code: 0 if the defect is observed (typo silently accepted),
non-zero if the defect is fixed (CLI rejects or warns about typo).
"""

from __future__ import annotations

import os
import shutil
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


def _make_temp_deck(tmp: Path) -> tuple[Path, str]:
    """Scaffold a temp deck dir with one card and one Layer-2 check."""
    deck_root = tmp / ".game-of-cards"
    deck_dir = deck_root / "deck"
    deck_dir.mkdir(parents=True)

    config_yaml = "layer_2_project_dod:\n  - name: placeholder\n    kind: manual\n    description: stand-in check\n    prompt: \"Did the thing pass? (y/N)\"\n"
    (deck_root / "config.yaml").write_text(config_yaml)

    card_title = "demo-card"
    card_dir = deck_dir / card_title
    card_dir.mkdir()
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {card_title}\n"
        "summary: demo card for attest --skip typo reproduction\n"
        "status: open\n"
        "stage: null\n"
        "contribution: low\n"
        "created: \"2026-05-31T00:00:00Z\"\n"
        "closed_at: null\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: []\n"
        "definition_of_done: |\n"
        "  - [ ] placeholder\n"
        "---\n\n# demo card\n"
    )
    (card_dir / "log.md").write_text("")
    return tmp, card_title


def _run_attest(repo_root: Path, deck_tmp: Path, card: str, skip_name: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "goc.cli",
            "attest",
            card,
            "--skip",
            skip_name,
            "--non-interactive",
        ],
        cwd=str(deck_tmp),
        env=env,
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        deck_tmp, card = _make_temp_deck(tmp)
        proc = _run_attest(REPO, deck_tmp, card, skip_name="plceholdr")

        stdout = proc.stdout
        stderr = proc.stderr

        unknown_skip_error = (
            "do not match any configured check" in stderr
            or "unknown skip name" in stderr.lower()
        )
        skipped_marker_present = "[~] placeholder" in stdout or "SKIPPED" in stdout
        check_actually_ran = "[ ] placeholder" in stdout or "[x] placeholder" in stdout

        print("=== goc attest stdout ===")
        print(stdout)
        if stderr.strip():
            print("=== goc attest stderr ===")
            print(stderr)
        print("=== assertions ===")
        print(f"typo accepted silently: {not unknown_skip_error}       (expected: False — should error or warn)")
        print(f"skipped marker present:  {skipped_marker_present}     (i.e. typo was honored as a skip; expected for fixed behavior)")
        print(f"check actually ran:      {check_actually_ran}     (i.e. configured check executed instead of being skipped)")

        defect_observed = (not unknown_skip_error) and (not skipped_marker_present) and check_actually_ran
        if defect_observed:
            print("\nDEFECT REPRODUCED: typo silently accepted, check ran instead of being skipped.")
            return 0
        print("\nNo defect: typo was rejected, warned about, or otherwise surfaced to the user.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
