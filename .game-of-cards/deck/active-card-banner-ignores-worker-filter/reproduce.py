"""Reproduce: the `ACTIVE:` banner ignores the `--worker` filter.

Drives the real `goc` CLI against a temp deck holding two active cards
owned by different workers (plus an open card so the queue renders).
`goc --worker alice` scopes the open queue to alice; the `ACTIVE:`
heads-up banner above it must do the same and name only alice's active
card.

Exits 0 when the banner is correctly worker-scoped (fixed engine);
exits 1 when it leaks bob's card (the bug).
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


ROOT = _repo_root()


def _write_card(cwd: Path, title: str, status: str, worker: str) -> None:
    card_dir = cwd / "deck" / title
    card_dir.mkdir(parents=True)
    closed_at = "2026-05-04" if status == "done" else "null"
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"summary: {title}\n"
        f"status: {status}\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-05-04\n"
        f"closed_at: {closed_at}\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        f"worker: {worker}\n"
        "definition_of_done: |\n"
        "  - [ ] test card\n"
        "---\n\n"
        f"# {title}\n"
    )


def _run(cwd: Path, *args: str) -> str:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    r = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )
    return r.stdout + r.stderr


def main():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        _write_card(cwd, "alice-active", "active", "alice")
        _write_card(cwd, "bob-active", "active", "bob")
        _write_card(cwd, "alice-open", "open", "alice")

        out = _run(cwd, "--worker", "alice")
        banner = next((ln for ln in out.splitlines() if ln.startswith("ACTIVE:")), "")

        print("=== `goc --worker alice` ACTIVE banner ===")
        print(banner or "(no ACTIVE banner)")
        print()

        leaks_bob = "bob-active" in banner
        has_alice = "alice-active" in banner
        print(f"banner mentions bob-active:   {leaks_bob}   (BUG if True)")
        print(f"banner mentions alice-active: {has_alice}")
        print()

        if (not leaks_bob) and has_alice:
            print("PASS: ACTIVE banner is scoped to --worker alice.")
            sys.exit(0)
        print("FAIL: ACTIVE banner ignores --worker (lists other workers' cards).")
        sys.exit(1)


if __name__ == "__main__":
    main()
