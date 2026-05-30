"""Reproduce: `goc validate` accepts whitespace-only worker values.

Sets up a scratch repo, installs goc into it, files two cards — one with a
bare `worker: " "` string and one with a mapping `worker: {who: " "}` — and
checks that `goc validate` reports them as OK when it should reject them.

Currently fails (validator passes). After the fix in
`goc/engine.py:validate_card`, both cards must produce an error and
`goc validate` must exit non-zero.
"""

from __future__ import annotations

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


def main() -> int:
    root = _repo_root()
    sys.path.insert(0, str(root))

    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td)
        subprocess.run(["git", "init", "-q"], cwd=scratch, check=True)
        py = sys.executable
        env_setup = subprocess.run(
            [py, "-m", "goc.cli", "install", "--briefing-target", "AGENTS.md"],
            cwd=scratch,
            capture_output=True,
            text=True,
        )
        if env_setup.returncode != 0:
            print("install failed:", env_setup.stderr)
            return 2

        bare_card = "ws-bare"
        subprocess.run(
            [py, "-m", "goc.cli", "new", bare_card,
             "--contribution", "medium", "--gate", "none",
             "--tag", "bug", "--worker", " "],
            cwd=scratch, check=True, capture_output=True,
        )

        bare_path = scratch / ".game-of-cards" / "deck" / bare_card / "README.md"
        worker_line = next(
            line for line in bare_path.read_text().splitlines()
            if line.startswith("worker:")
        )
        print(f"[bare]    persisted: {worker_line!r}")

        mapping_card = "ws-mapping"
        subprocess.run(
            [py, "-m", "goc.cli", "new", mapping_card,
             "--contribution", "medium", "--gate", "none", "--tag", "bug"],
            cwd=scratch, check=True, capture_output=True,
        )
        mapping_path = scratch / ".game-of-cards" / "deck" / mapping_card / "README.md"
        text = mapping_path.read_text()
        text = text.replace("worker: " + chr(34) + " " + chr(34),
                            "worker: {who: " + chr(34) + " " + chr(34) + "}")
        if "worker: {who:" not in text:
            text = text.replace(
                "advances: []",
                "advances: []\nworker: {who: \" \"}",
                1,
            )
        mapping_path.write_text(text)
        worker_line = next(
            line for line in mapping_path.read_text().splitlines()
            if line.startswith("worker:")
        )
        print(f"[mapping] persisted: {worker_line!r}")

        result = subprocess.run(
            [py, "-m", "goc.cli", "validate"],
            cwd=scratch, capture_output=True, text=True,
        )
        print("\n--- goc validate stdout ---")
        print(result.stdout)
        if result.stderr.strip():
            print("--- goc validate stderr ---")
            print(result.stderr)
        print(f"--- exit code: {result.returncode} ---")

        bare_rejected = (
            f"{bare_card}: worker:" in result.stdout
            or f"{bare_card}: worker:" in result.stderr
        )
        mapping_rejected = (
            f"{mapping_card}: worker:" in result.stdout
            or f"{mapping_card}: worker:" in result.stderr
        )

        if bare_rejected and mapping_rejected and result.returncode != 0:
            print("\nPASS: validator rejected both whitespace-only worker forms.")
            return 0
        print(
            "\nFAIL: validator accepted whitespace-only worker"
            f" (bare_rejected={bare_rejected}, mapping_rejected={mapping_rejected},"
            f" exit={result.returncode})."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
