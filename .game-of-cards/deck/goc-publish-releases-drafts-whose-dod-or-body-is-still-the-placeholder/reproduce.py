#!/usr/bin/env python3
"""Reproduce: `goc publish` releases a draft that still carries one of the two
`goc new` scaffold placeholders.

Runs the card's Falsification recipe in a scratch deck (no git repo, every
mutating verb run with `--no-commit`):

1. `goc new` three cards; give each a summary so the separate
   summary-release gate cannot be what refuses.
2. `body-only-card`: replace only the body placeholder (DoD still the stub).
   `dod-only-card`: replace only the DoD placeholder (body still the stub).
   `authored-card`: replace both (the control).
3. `goc publish <card> --no-commit` on each, then `goc --ready`.

The rule three surfaces promise (card-schema reference § Draft contract,
publish's own refusal, `goc new`'s closing hint) is that publish has nothing
to release until body AND DoD are written. So the defect fires when either
half-authored draft publishes (exit 0, draft flag cleared, card listed by
`goc --ready`).

Exit-code contract: exits 0 once the defect no longer fires — both
half-authored drafts are refused with exit 2, keep `draft: true` and stay out
of `goc --ready`, while the fully authored control still publishes and is
listed. Exits 1 while the defect fires (or the control regresses).

Run: uv run python .game-of-cards/deck/goc-publish-releases-drafts-whose-dod-or-body-is-still-the-placeholder/reproduce.py
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


REPO = _repo_root()
LAUNCHER = REPO / "goc" / "_launch.py"

DOD_PLACEHOLDER = "- [ ] (replace with real criteria)"
BODY_PLACEHOLDER = "(write the design doc here)"
REAL_DOD = "- [ ] TDD: a real, checkable criterion"
REAL_BODY = "A real briefing a cold reader can act on."


def goc(cwd: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    # The launcher file, not `-m`, so the scratch cwd cannot shadow the engine.
    env = {k: v for k, v in os.environ.items() if k != "GOC_WORKER"}
    env["PYTHONPATH"] = str(REPO)
    return subprocess.run(
        [sys.executable, str(LAUNCHER), *argv],
        cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )


def readme(deck: Path, title: str) -> Path:
    return deck / title / "README.md"


def scaffold(root: Path, deck: Path, title: str, *, body: bool, dod: bool) -> None:
    made = goc(root, "new", title, "--gate", "none", "--tag", "bug",
               "--summary", f"Scratch card {title}.", "--no-commit")
    if made.returncode != 0:
        raise SystemExit(f"setup failed: goc new {title}:\n{made.stdout}{made.stderr}")
    path = readme(deck, title)
    text = path.read_text()
    if DOD_PLACEHOLDER not in text or BODY_PLACEHOLDER not in text or "\ndraft: true\n" not in text:
        raise SystemExit(f"setup failed: goc new {title} no longer writes both placeholders and the draft flag")
    if body:
        text = text.replace(BODY_PLACEHOLDER, REAL_BODY)
    if dod:
        text = text.replace(DOD_PLACEHOLDER, REAL_DOD)
    path.write_text(text)


def main() -> int:
    cases = [
        # title, body authored, DoD authored, publish should succeed
        ("body-only-card", True, False, False),
        ("dod-only-card", False, True, False),
        ("authored-card", True, True, True),
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        deck = root / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        for title, body, dod, _ in cases:
            scaffold(root, deck, title, body=body, dod=dod)

        for title, _, _, should_publish in cases:
            result = goc(root, "publish", title, "--no-commit")
            still_draft = "\ndraft: true\n" in readme(deck, title).read_text()
            print(f"--- goc publish {title} --no-commit: exit={result.returncode}")
            for line in (result.stdout + result.stderr).strip().splitlines():
                print(f"    {line}")
            print(f"    draft flag still set: {still_draft}")
            if should_publish:
                if result.returncode != 0 or still_draft:
                    failures.append(f"{title}: fully authored control was not published")
            else:
                if result.returncode != 2 or not still_draft:
                    failures.append(
                        f"{title}: half-authored draft published "
                        f"(exit {result.returncode}, draft flag cleared: {not still_draft})"
                    )

        ready = goc(root, "--ready", "--no-color")
        listed = {ln.split()[0] for ln in ready.stdout.splitlines() if ln.strip()}
        print(f"--- goc --ready: exit={ready.returncode}")
        for line in ready.stdout.strip().splitlines():
            print(f"    {line}")
        for title, _, _, should_publish in cases:
            if should_publish and title not in listed:
                failures.append(f"{title}: fully authored control missing from goc --ready")
            if not should_publish and title in listed:
                failures.append(f"{title}: half-authored card offered by goc --ready")

    print()
    if failures:
        print("DEFECT FIRES:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("OK: publish refuses both half-authored drafts and releases the authored one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
