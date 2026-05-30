#!/usr/bin/env python3
"""Prove that `goc upgrade` silently overwrites authored project-state files.

Scenario (mirrors a real downstream repo upgrading across versions):
  1. `goc install` into a fresh repo — scaffolds the empty `.game-of-cards/`
     content stubs and `hooks/*.md`.
  2. The consumer authors real content into those stubs (their project's tag
     vocabulary, a workflow-hook instruction).
  3. The consumer's `.goc-version` predates the current engine, so `goc upgrade`
     runs a real sync (it short-circuits to a no-op only when versions match).
  4. `goc upgrade` re-copies the stock templates over the authored files.

Expected (correct) behavior: an upgrade preserves authored project-state.
Observed behavior: the authored content is gone, replaced by the empty stub.

Exits 0 when the defect reproduces (authored content was lost), 1 otherwise.
"""

from __future__ import annotations

import contextlib
import io
import os
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


sys.path.insert(0, str(_repo_root()))

from goc import install as goc_install  # noqa: E402

# Files the consumer is documented to author (README "Author the content the
# skills should see"). We probe two: a content stub and a workflow hook.
STUB = Path(".game-of-cards/canonical-tags.md")
HOOK = Path(".game-of-cards/hooks/create-card.md")

AUTHORED_STUB = (
    "# canonical-tags (MyProject)\n\n"
    "```yaml\ncanonical_tags:\n  - myproject-rendering\n  - myproject-ingest\n```\n"
)
AUTHORED_HOOK = "When filing a card, always attach the Jira ticket id in the summary.\n"

SENTINEL_STUB = "myproject-rendering"
SENTINEL_HOOK = "Jira ticket id"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        prev_cwd = Path.cwd()
        os.chdir(repo)
        try:
            # Step 1 — fresh install (silence its chatty stdout).
            with contextlib.redirect_stdout(io.StringIO()):
                goc_install.install()

            # Step 2 — consumer authors real content into the stubs.
            (repo / STUB).write_text(AUTHORED_STUB)
            (repo / HOOK).write_text(AUTHORED_HOOK)

            # Step 3 — pin an older installed version so upgrade does real work
            # instead of the same-version "nothing to do" short-circuit.
            version_file = repo / ".game-of-cards/deck/.goc-version"
            version_file.write_text("0.0.1\n")

            # Step 4 — upgrade.
            with contextlib.redirect_stdout(io.StringIO()):
                goc_install.upgrade()

            stub_after = (repo / STUB).read_text()
            hook_after = (repo / HOOK).read_text()
        finally:
            os.chdir(prev_cwd)

    stub_lost = SENTINEL_STUB not in stub_after
    hook_lost = SENTINEL_HOOK not in hook_after

    print(f"authored content stub  ({STUB.name}): "
          f"{'LOST' if stub_lost else 'preserved'}")
    print(f"authored workflow hook ({HOOK.name}): "
          f"{'LOST' if hook_lost else 'preserved'}")
    print()
    print(f"--- {STUB} after upgrade (first 6 lines) ---")
    print("\n".join(stub_after.splitlines()[:6]) or "(empty)")

    if stub_lost or hook_lost:
        print("\nDEFECT REPRODUCED: goc upgrade overwrote authored project-state.")
        return 0
    print("\nNo data loss observed — defect did not reproduce.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
