"""Reproduce: `goc wait --until <already-elapsed date>` leaves the card pullable.

Two invocations, both supplying an `--until` that is elapsed the moment it is
written: today's UTC date (a bare `YYYY-MM-DD` resolves to midnight UTC, so it
is past from the first second of the day it names) and a long-past date.

`goc wait` validated `--reason` against the schema enum and `--until` against
the ISO shape, then wrote the overlay and reported success — without ever
asking its own read guard whether the overlay it just wrote impedes anything.
`waiting_impedes` answers `False` for an elapsed `waiting_until` (documented,
deliberate: an elapsed wait re-surfaces the card), so the card stayed in
`--ready` and was absent from `--waiting`.

The decided fix is strict-refuse: exit 2, `ERROR:` on stderr, nothing written.
A future `--until` is the positive control: it must still be accepted and hide
its card, so a verb that refused every date would not read as fixed.

Exit codes follow the deck's reproducer contract:
  0 — the defect no longer fires (each elapsed --until is refused with nothing
      written, or the overlay it writes does hide the card)
  1 — the defect fires (exit 0 and a success line, the card still pullable)
  2 — the harness or a precondition is broken (setup or the control failed,
      or an outcome matched neither verdict)
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


class HarnessError(Exception):
    """Setup or the control failed: the run says nothing about the defect."""


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise HarnessError("repo root (pyproject.toml) not found")


def run() -> int:
    repo = _repo_root()
    # Run goc as `python -m goc.cli`, pinning the source tree on PYTHONPATH so
    # we don't need to install a wheel into the sandbox.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo) + os.pathsep + env.get("PYTHONPATH", "")
    env.pop("GOC_WORKTREE_DECK", None)

    now = datetime.now(tz=timezone.utc)
    cases = [
        ("today", now.strftime("%Y-%m-%d"), "deferred"),
        ("long past", "2020-01-01", "external"),
    ]
    control_until = (now + timedelta(days=30)).strftime("%Y-%m-%d")

    with tempfile.TemporaryDirectory() as td:
        sandbox = Path(td) / "sandbox"
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

        def new_card(title: str) -> Path:
            r = goc("new", title, "--contribution", "low", "--gate", "none",
                    "--summary", "Probe card for the elapsed --until case.",
                    "--tag", "api-contract", "--no-commit")
            if r.returncode != 0:
                raise HarnessError(f"goc new {title} failed: {r.stderr.strip()}")
            # `goc new` scaffolds a draft; drafts are hidden from every queue,
            # so publish it before asking whether the overlay hides it.
            readme = deck / title / "README.md"
            readme.write_text(
                readme.read_text()
                .replace("- [ ] (replace with real criteria)",
                         "- [ ] MECHANICAL: placeholder")
                .replace("(write the design doc here)",
                         "Body text so the card is not a placeholder scaffold.")
            )
            r = goc("publish", title, "--no-commit")
            if r.returncode != 0:
                raise HarnessError(f"goc publish {title} failed: {r.stderr.strip()}")
            return readme

        def queued(title: str) -> tuple[bool, bool]:
            """Whether `title` is listed by `goc --ready` and by `goc --waiting`."""
            ready = goc("--ready", "--no-color")
            waiting = goc("--waiting", "--no-color")
            for r in (ready, waiting):
                if r.returncode != 0:
                    raise HarnessError(f"goc {' '.join(r.args[3:])} failed: {r.stderr.strip()}")
            return title in ready.stdout, title in waiting.stdout

        control = "demo-control"
        new_card(control)
        r = goc("wait", control, "--until", control_until, "--no-commit")
        if r.returncode != 0 or queued(control) != (False, True):
            raise HarnessError(
                f"control: a future --until {control_until} did not take effect "
                f"(exit {r.returncode}): {r.stderr.strip()}"
            )
        print(f"control: goc wait {control} --until {control_until} → exit 0, "
              "hidden from --ready, listed by --waiting\n")

        bugs = 0
        for label, until, reason in cases:
            title = f"demo-{label.replace(' ', '-')}"
            readme = new_card(title)
            before = readme.read_bytes()
            wait = goc("wait", title, "--reason", reason, "--until", until, "--no-commit")
            written = readme.read_bytes() != before
            in_ready, in_waiting = queued(title)

            print(f"=== goc wait {title} --reason {reason} --until {until}  ({label}) ===")
            print(f"exit code: {wait.returncode}")
            print(f"stdout: {wait.stdout.strip()}")
            print(f"stderr: {wait.stderr.strip()}")
            print(f"README written: {written}; --ready lists it: {in_ready}; "
                  f"--waiting lists it: {in_waiting}")

            if wait.returncode == 2 and "ERROR:" in wait.stderr and "--until" in wait.stderr and not written:
                print(f"FIXED ({label}): refused with exit 2 and nothing written.\n")
            elif wait.returncode == 0 and not in_ready and in_waiting:
                print(f"FIXED ({label}): the overlay took effect.\n")
            elif wait.returncode == 0 and in_ready and not in_waiting:
                print(
                    f"BUG ({label}): exit 0 and a success line, yet {title} is still "
                    "listed by --ready and absent from --waiting — the overlay "
                    "impedes nothing.\n"
                )
                bugs += 1
            else:
                raise HarnessError(f"{label}: the outcome above matches neither verdict")

        print("=== diagnosis ===")
        if bugs:
            print(f"BUG: {bugs} of {len(cases)} elapsed --until values were accepted silently.")
            return 1
        print("FIXED: no elapsed --until value produced a silent no-op overlay.")
        return 0


def main() -> int:
    try:
        return run()
    except HarnessError as exc:
        print(f"HARNESS: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
