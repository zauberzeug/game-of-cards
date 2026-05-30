"""Reproduce: `goc decide` stamps the archived-deliberation log entry with
the card's `created` timestamp instead of the now-of-writing, producing
out-of-order log.md entries when an intermediate write (e.g. `goc attest`)
has already appended a more recent entry.

Run: `uv run python .game-of-cards/deck/<title>/reproduce.py`
"""
from __future__ import annotations

import os
import re
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


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        deck = root / ".game-of-cards" / "deck"
        card = deck / "demo-card"
        card.mkdir(parents=True)
        # README: parked on a decision gate, created two months before "now".
        readme = """\
---
title: demo-card
summary: "demo"
status: open
stage: null
contribution: medium
created: "2026-04-01T00:00:00Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] decide
---

# demo-card

Some framing.

## Decision required

Pick A or B.

- A: do this
- B: do that
"""
        (card / "README.md").write_text(readme)

        # log.md already has an intermediate entry — e.g. from a prior
        # `goc attest` run between filing and decision. This is the
        # canonical case where the bug becomes visible.
        prior_log = "## 2026-05-15T10:00:00Z: attestation run\n\nLayer-3 check passed.\n"
        (card / "log.md").write_text(prior_log)

        env = dict(os.environ)
        # Disable any auto-commit so the reproduction is hermetic.
        env["GOC_AUTO_COMMIT"] = "0"

        cmd = [
            sys.executable, "-m", "goc.cli",
            "decide", "demo-card",
            "--decision", "A",
            "--because", "rubric pointed at A",
            "--no-commit",
        ]
        result = subprocess.run(
            cmd, cwd=root, env=env,
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print("ERROR running goc decide:", result.stderr)
            return 2

        log_text = (card / "log.md").read_text()

        # Collect the headers (`## ...`) in order.
        headers = re.findall(r"^## .+$", log_text, flags=re.MULTILINE)

        print("=" * 60)
        print("log.md headers in file order:")
        for h in headers:
            print(f"  {h}")
        print("=" * 60)

        # The bug: the 'decision deliberation archived' header is stamped
        # with the card's 'created' value (2026-04-01), so it lands AFTER
        # the 2026-05-15 attestation header even though chronologically
        # the archival happens after the attestation.
        ts_pattern = re.compile(r"^## (\S+):")
        ts_by_header = []
        for h in headers:
            m = ts_pattern.match(h)
            if m:
                ts_by_header.append((m.group(1), h))

        out_of_order = []
        for i in range(1, len(ts_by_header)):
            prev_ts, prev_h = ts_by_header[i - 1]
            cur_ts, cur_h = ts_by_header[i]
            if cur_ts < prev_ts:
                out_of_order.append((prev_h, cur_h))

        if out_of_order:
            print("FAIL: log.md headers are NOT in chronological order.")
            print()
            for prev_h, cur_h in out_of_order:
                print(f"  earlier header (later in file):")
                print(f"    {prev_h}")
                print(f"  later header (earlier in file):")
                print(f"    {cur_h}")
                print()
            print("The 'decision deliberation archived' entry uses the card's")
            print("`created` timestamp instead of _utc_now_iso() at decide-time.")
            print("Cited code: goc/engine.py:4593 — `filed = t.created or now`")
            return 1

        print("PASS: log.md headers are in chronological order.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
