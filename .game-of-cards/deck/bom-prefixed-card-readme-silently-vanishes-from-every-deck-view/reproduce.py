"""A UTF-8 BOM before the opening `---` makes a card vanish from every
deck view silently (exit 0, no stderr warning), while validate and the
title verbs misdiagnose it as "missing opening '---' at line 1".

Contrast case: an *unterminated* frontmatter card in the same deck DOES
print a per-card WARNING on queue reads — proving the silent BOM path
violates the engine's own surface-a-warning-per-broken-card contract.
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

CARD = """---
title: bom-probe-card
status: open
stage: null
contribution: medium
created: "2026-07-22T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] TDD: probe criterion
---

# bom-probe-card

Probe body.
"""


def goc(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(REPO))
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, capture_output=True, text=True,
    )


def main() -> int:
    failures = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        card_dir = root / ".game-of-cards" / "deck" / "bom-probe-card"
        card_dir.mkdir(parents=True)
        readme = card_dir / "README.md"
        readme.write_text(CARD, encoding="utf-8")

        before = goc(root)
        print("== queue BEFORE BOM ==")
        print(before.stdout.rstrip() or "(empty)")
        if "bom-probe-card" not in before.stdout:
            failures.append("probe card missing from queue even before the BOM")

        readme.write_bytes(b"\xef\xbb\xbf" + readme.read_bytes())

        after = goc(root)
        print("== queue AFTER BOM ==")
        print(after.stdout.rstrip() or "(empty)")
        print(f"stderr: {after.stderr.rstrip() or '(empty)'}   exit: {after.returncode}")
        if "bom-probe-card" in after.stdout:
            failures.append("card still listed after BOM (defect no longer fires)")
        if after.stderr.strip():
            failures.append("queue read warned about the BOM card (defect fixed?)")

        val = goc(root, "validate")
        print("== goc validate ==")
        print((val.stdout + val.stderr).rstrip())
        if "missing opening '---' at line 1" not in (val.stdout + val.stderr):
            failures.append("validate no longer emits the misleading line-1 message")

    if failures:
        print("\n[NO-REPRO] " + "; ".join(failures))
        return 1
    print("\n[FAIL] BOM card vanished silently (exit 0, no warning); "
          "validate blames a missing '---' that IS at line 1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
