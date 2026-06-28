#!/usr/bin/env python3
"""Reproduce: `goc new` stamps the GOC_WORKER queue-filter env var (and
the global `--worker` filter) into the new card's authored `worker`
frontmatter field, because `new`'s SUPPRESS'd `--worker` shares its dest
with the global filter whose default is os.environ.get("GOC_WORKER").

Exits 0 when the defect is FIXED (bare `new` leaves worker unset),
1 while it is live.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def run_new(cwd: Path, *args: str, env_worker: str | None = None) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    if env_worker is not None:
        env["GOC_WORKER"] = env_worker
    else:
        env.pop("GOC_WORKER", None)
    subprocess.run(
        [sys.executable, "-m", "goc.cli", *args, "--no-commit"],
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def worker_field(cwd: Path, title: str) -> str | None:
    text = (cwd / ".game-of-cards" / "deck" / title / "README.md").read_text()
    m = re.search(r"^worker:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / ".game-of-cards" / "deck").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=cwd, check=True)

        run_new(cwd, "new", "env-worker", env_worker="alice")
        run_new(cwd, "--worker", "bob", "new", "global-worker")
        run_new(cwd, "new", "clean")  # no env, no flag — control
        run_new(cwd, "new", "explicit", "--worker", "carol")

        env_w = worker_field(cwd, "env-worker")
        global_w = worker_field(cwd, "global-worker")
        clean_w = worker_field(cwd, "clean")
        explicit_w = worker_field(cwd, "explicit")

        print(f"GOC_WORKER=alice  new env-worker     -> worker={env_w!r}")
        print(f"--worker bob      new global-worker  -> worker={global_w!r}")
        print(f"(none)            new clean          -> worker={clean_w!r}")
        print(f"                  new --worker carol -> worker={explicit_w!r}")

        # Explicit --worker must always be honored.
        assert explicit_w == "carol", f"explicit --worker lost: {explicit_w!r}"
        # Control must never carry a worker.
        assert clean_w is None, f"control card unexpectedly stamped: {clean_w!r}"

        if env_w is not None or global_w is not None:
            print(
                "DEFECT PRESENT: filter value leaked into authored worker field"
            )
            return 1

        print("DEFECT FIXED: filter value no longer stamps the worker field")
        return 0


if __name__ == "__main__":
    sys.exit(main())
