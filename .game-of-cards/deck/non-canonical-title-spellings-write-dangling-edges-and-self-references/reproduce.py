"""Reproduce: non-canonical title spellings become card identity.

`resolve_card_dir` accepts an in-deck title spelled with a trailing
slash (`alpha-card/`) or a `./` prefix (`./beta-card`) — both resolve to
the same directory as the bare name. Every caller then uses the *raw
argument string* as the card's identity, so the unnormalized spelling is
written verbatim into frontmatter edge fields and compared verbatim by
the self-edge / duplicate-member guards.

Builds a hermetic scratch deck, drives the four affected doors through
the real engine, and reports the resulting deck damage.

Exit 0 once the defect no longer fires (every non-canonical spelling is
refused before any write); non-zero while it does.
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

CARD = """---
title: {title}
status: open
stage: null
contribution: medium
created: "2026-08-02"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
summary: "scratch probe card {title}"
definition_of_done: |
  - [x] TDD: nothing to do
---

# {title}
"""


def _mkdeck(root: Path, titles: list[str]) -> None:
    (root / ".game-of-cards" / "deck").mkdir(parents=True)
    (root / ".game-of-cards" / "config.yaml").write_text("auto_commit: false\n")
    for t in titles:
        d = root / ".game-of-cards" / "deck" / t
        d.mkdir()
        (d / "README.md").write_text(CARD.format(title=t))


def _goc(root: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=root, env=env, capture_output=True, text=True,
    )


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _mkdeck(root, ["alpha-card", "beta-card", "delta-card"])

        # Door 1 — `advance` self-edge guard is a raw string compare, so a
        # trailing-slash spelling of the SAME card slips past it.
        r = _goc(root, "advance", "alpha-card", "--by", "alpha-card/")
        print(f"[1] goc advance alpha-card --by alpha-card/   -> exit {r.returncode}")
        print(f"    {r.stdout.strip() or r.stderr.strip()}")
        if r.returncode == 0:
            failures.append("advance accepted a trailing-slash self-spelling")

        # Door 2 — cross-card edge stores the `./`-prefixed spelling verbatim.
        r = _goc(root, "advance", "beta-card", "--by", "./delta-card")
        print(f"[2] goc advance beta-card --by ./delta-card   -> exit {r.returncode}")
        print(f"    {r.stdout.strip() or r.stderr.strip()}")
        if r.returncode == 0:
            failures.append("advance accepted a ./-prefixed advancer spelling")

        # Door 3 — supersession pointer stores the trailing-slash spelling.
        r = _goc(root, "status", "delta-card", "superseded", "--by", "beta-card/")
        print(f"[3] goc status delta-card superseded --by beta-card/ -> exit {r.returncode}")
        print(f"    {(r.stdout.strip() or r.stderr.strip()).splitlines()[-1]}")
        if r.returncode == 0:
            failures.append("status --by accepted a trailing-slash successor spelling")

        # The deck the three doors above leave behind.
        v = _goc(root, "validate")
        errs = [ln for ln in v.stdout.splitlines() + v.stderr.splitlines()
                if ln.startswith("ERROR")]
        print(f"[4] goc validate -> exit {v.returncode}, {len(errs)} error(s):")
        for ln in errs:
            print(f"    {ln}")
        if errs:
            failures.append(f"deck left invalid: {len(errs)} validate error(s)")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _mkdeck(root, ["solo-card", "other-card"])

        # Door 4 — the --bundle duplicate-title guard is a raw string compare,
        # so one card counts as two members and is closed twice.
        r = _goc(root, "done", "--bundle", "solo-card", "solo-card/")
        print(f"[5] goc done --bundle solo-card solo-card/   -> exit {r.returncode}")
        print(f"    {(r.stdout.strip() or r.stderr.strip()).splitlines()[-2:]}")
        log = root / ".game-of-cards" / "deck" / "solo-card" / "log.md"
        if r.returncode == 0 and log.exists():
            text = log.read_text()
            blocks = text.count("## Closure verification")
            selfref = [ln for ln in text.splitlines() if "Bundled with" in ln]
            print(f"    log.md attestation blocks: {blocks}")
            for ln in selfref:
                print(f"    {ln.strip()}")
            if blocks > 1:
                failures.append(
                    f"--bundle wrote {blocks} attestation blocks to one card"
                )
            if any("solo-card" in ln for ln in selfref):
                failures.append("--bundle recorded a card as bundled with itself")
        if r.returncode == 0:
            failures.append("--bundle accepted the same card under two spellings")

    print()
    if failures:
        print(f"DEFECT FIRES — {len(failures)} finding(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OK — every non-canonical title spelling is refused before any write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
