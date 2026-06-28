#!/usr/bin/env python3
"""Reproduce: an emit-path `goc` verb rewrites a `worker: {where: ...}`-only
mapping into the invalid `worker: {who: "", where: ...}` form.

A card hand-authored (or migrated) with a worker mapping that carries `where`
but omits `who` is already rejected by `goc validate` with
`worker: mapping must have a 'who' key`. That is a *missing-key* error the
author can fix by adding `who`. But run any full-frontmatter re-emit verb on
the same card — `goc wait`, `goc decide`, `goc advance`, `goc unadvance`,
`goc quality-pass`, `goc migrate-list-style` — and `_emit_worker` defaults the
missing `who` to `""` and writes `worker: {who: "", where: ...}`. The verb
reports success while silently inventing a `who` the author never wrote, and
the validate error mutates into `'who' must be a non-empty, non-whitespace
string`.

The sibling writer `_auto_populate_worker` (engine.py) explicitly REFUSES to
emit this exact shape ("there is no valid worker to stamp ... rather than write
an invalid `{who: "", where: <branch>}` that self-corrupts the card"), and
`_yaml_inline` raises rather than emit a value that cannot round-trip. The
emitter `_emit_worker` is the one site that violates that shared invariant.

Run: uv run python .game-of-cards/deck/worker-mapping-with-only-a-branch-emits-invalid-empty-who/reproduce.py
"""
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
sys.path.insert(0, str(REPO))

from goc.engine import _emit_worker  # noqa: E402

CARD = """\
---
title: scratch-card
summary: "scratch"
status: open
stage: null
contribution: medium
created: "2026-06-19T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: x
worker: {where: feature/x}
---

# scratch
"""


def _goc(cwd: Path, *argv) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *argv],
        cwd=str(cwd), capture_output=True, text=True,
        env={"PYTHONPATH": str(REPO), "PATH": __import__("os").environ.get("PATH", "")},
    )


def main() -> int:
    # 1. Unit-level proof: the emitter manufactures an empty `who`.
    emitted = _emit_worker({"where": "feature/x"})
    print("1. _emit_worker({'where': 'feature/x'}) ->", repr(emitted))
    unit_bug = emitted == '{who: "", where: feature/x}'
    print("   manufactures empty who:", unit_bug)
    print()

    # 2. End-to-end through a real verb in an isolated deck.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cdir = root / ".game-of-cards" / "deck" / "scratch-card"
        cdir.mkdir(parents=True)
        (cdir / "README.md").write_text(CARD)
        (cdir / "log.md").write_text("")

        before = _goc(root, "validate")
        worker_in = (cdir / "README.md").read_text().splitlines()
        print("2. INPUT worker line:",
              next(ln for ln in worker_in if ln.startswith("worker")))
        print("   validate BEFORE verb:",
              next((ln for ln in (before.stdout + before.stderr).splitlines()
                    if "worker:" in ln), "(none)").strip())
        print()

        wait = _goc(root, "wait", "scratch-card", "--reason", "external", "--no-commit")
        print("3. `goc wait` exit:", wait.returncode, "->",
              (wait.stdout + wait.stderr).strip().splitlines()[-1])
        worker_out = (cdir / "README.md").read_text().splitlines()
        out_line = next(ln for ln in worker_out if ln.startswith("worker"))
        print("   OUTPUT worker line:", out_line)
        print()

        after = _goc(root, "validate")
        after_line = next((ln for ln in (after.stdout + after.stderr).splitlines()
                           if "worker:" in ln), "(none)").strip()
        print("4. validate AFTER verb:", after_line)

    e2e_bug = out_line == 'worker: {who: "", where: feature/x}' \
        and "must be a non-empty" in after_line
    print()
    if unit_bug and e2e_bug:
        print("DEFECT CONFIRMED: emit-path verb invented `who: \"\"` and turned a "
              "missing-key error into a non-empty-string error.")
        return 0
    print("DEFECT NOT REPRODUCED — emitter may have been fixed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
