"""Reproduce: `goc wait --until <already-elapsed date>` leaves the card pullable.

Two invocations, both supplying an `--until` that is elapsed the moment it is
written: today's UTC date (a bare `YYYY-MM-DD` resolves to midnight UTC, so it
is past from the first second of the day it names) and a long-past date.

`goc wait` validates `--reason` against the schema enum and `--until` against
the ISO shape, then writes the overlay and reports success — without ever
asking its own read guard whether the overlay it just wrote impedes anything.
`waiting_impedes` answers `False` for an elapsed `waiting_until` (documented,
deliberate: an elapsed wait re-surfaces the card), so the card stays in
`--ready` and is absent from `--waiting`.

Expected after fix: the verb either rejects the elapsed `--until` (non-zero
exit, no mutation) or its own output states that the overlay does not impede.
Either outcome exits 0; the BUG branch exits 1.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


def main() -> int:
    repo = _repo_root()
    # Run goc as `python -m goc.cli`, pinning the source tree on PYTHONPATH so
    # we don't need to install a wheel into the sandbox.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo) + os.pathsep + env.get("PYTHONPATH", "")

    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    cases = [
        ("today", today, "deferred"),
        ("long past", "2020-01-01", "external"),
    ]

    with tempfile.TemporaryDirectory() as td:
        sandbox = Path(td) / "sandbox"
        sandbox.mkdir()
        deck = sandbox / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)

        def goc(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, "-m", "goc.cli", *args],
                cwd=sandbox,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        bugs = 0
        for label, until, reason in cases:
            title = f"demo-{label.replace(' ', '-')}"
            r = goc("new", title, "--contribution", "low", "--gate", "none",
                    "--tag", "api-contract", "--no-commit")
            assert r.returncode == 0, f"goc new failed: {r.stderr}"
            # `goc new` scaffolds a draft; drafts are hidden from every queue,
            # so clear the flag before asking whether the overlay hides it.
            readme = deck / title / "README.md"
            readme.write_text(
                readme.read_text()
                .replace("- [ ] (replace with real criteria)",
                         "- [ ] MECHANICAL: placeholder")
                .replace("(write the design doc here)",
                         "Body text so the card is not a placeholder scaffold.")
            )
            r = goc("publish", title, "--no-commit")
            assert r.returncode == 0, f"goc publish failed: {r.stderr}"

            wait = goc("wait", title, "--reason", reason, "--until", until, "--no-commit")
            ready = goc("--ready", "--no-color")
            waiting = goc("--waiting", "--no-color")

            print(f"=== goc wait {title} --reason {reason} --until {until}  ({label}) ===")
            print(f"exit code: {wait.returncode}")
            print(f"stdout: {wait.stdout.strip()}")
            print(f"stderr: {wait.stderr.strip()}")
            print()
            print("--- goc --ready (card should be hidden if the overlay impedes) ---")
            print(ready.stdout.strip() or "(empty)")
            print()
            print("--- goc --waiting (card should be listed if the overlay impedes) ---")
            print(waiting.stdout.strip() or "(empty)")
            print()

            if wait.returncode != 0:
                print(f"FIXED ({label}): elapsed --until rejected with non-zero exit.\n")
                continue
            announced = "impede" in (wait.stdout + wait.stderr).lower()
            if announced:
                print(f"FIXED ({label}): the verb states the overlay does not impede.\n")
                continue
            still_ready = title in ready.stdout
            hidden_from_waiting = title not in waiting.stdout
            if still_ready and hidden_from_waiting:
                print(
                    f"BUG ({label}): exit 0 and a success line, yet {title} is still "
                    "listed by --ready and absent from --waiting — the overlay "
                    "impedes nothing.\n"
                )
                bugs += 1
            else:
                print(f"FIXED ({label}): the overlay took effect.\n")

        print("=== diagnosis ===")
        if bugs:
            print(f"BUG: {bugs} of {len(cases)} elapsed --until values were accepted silently.")
            return 1
        print("FIXED: no elapsed --until value produced a silent no-op overlay.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
