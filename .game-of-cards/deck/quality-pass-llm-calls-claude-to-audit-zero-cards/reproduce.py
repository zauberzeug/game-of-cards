"""Reproduce: `goc quality-pass --llm` starts `claude` with no card to audit.

A fake `claude` is the only entry on PATH, so no real `claude` is ever
reached. It records each call and answers with an empty verdict list. The
control runs `goc quality-pass --llm --dry-run` over a deck holding one open
card and must start the fake once. Four selections that hold no live card
must not start it at all:

- no deck,
- an empty deck,
- `--limit 0` over the one-card deck,
- `--status active` over the one-card deck, where no card is active.

Each of the four must also exit 0: a pass with nothing to audit has not failed.

Exit codes: 0 — the defect no longer fires (no empty selection starts
`claude`); 1 — the defect fires; 2 — the control never started the fake, so
there is no verdict.

Run: uv run python .game-of-cards/deck/quality-pass-llm-calls-claude-to-audit-zero-cards/reproduce.py
"""

from __future__ import annotations

import json
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

CARD = """---
title: probe-card
summary: "A live card for the control run."
status: open
stage: null
contribution: medium
created: "2026-11-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: probe.
---

# probe-card

Body.
"""

FAKE_CLAUDE = """\
import json, os, sys
stdin = sys.stdin.buffer.read().decode("utf-8")
with open(os.environ["FAKE_CLAUDE_CAPTURE"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"argv": sys.argv[1:], "stdin_bytes": len(stdin)}) + "\\n")
print(json.dumps({"result": "[]"}))
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake = tmp_path / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE, encoding="utf-8")
        shim = bin_dir / "claude"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" "$@"\n', encoding="utf-8")
        shim.chmod(0o755)

        def project(name: str, deck: str) -> Path:
            root = tmp_path / name
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            if deck != "none":
                (root / ".game-of-cards" / "deck").mkdir(parents=True)
            if deck == "one-card":
                card = root / ".game-of-cards" / "deck" / "probe-card"
                card.mkdir()
                (card / "README.md").write_text(CARD, encoding="utf-8")
                (card / "log.md").write_text("", encoding="utf-8")
            return root

        def run(cwd: Path, *flags: str) -> tuple[subprocess.CompletedProcess[str], int]:
            capture = tmp_path / f"calls-{cwd.name}-{len(flags)}-{'_'.join(flags)}.jsonl"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT)
            env.pop("GOC_WORKTREE_DECK", None)
            # The fake's directory is the WHOLE PATH: a fake that failed to
            # start must never fall through to a real `claude`.
            env["PATH"] = str(bin_dir)
            env["FAKE_CLAUDE_CAPTURE"] = str(capture)
            result = subprocess.run(
                [sys.executable, str(ROOT / "goc" / "_launch.py"),
                 "quality-pass", "--llm", "--dry-run", *flags],
                cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, text=True, check=False, timeout=120,
            )
            calls = 0
            if capture.exists():
                calls = sum(1 for ln in capture.read_text(encoding="utf-8").splitlines()
                            if json.loads(ln))
            return result, calls

        one_card = project("one-card", "one-card")
        control, control_calls = run(one_card)
        print(f"--- control: one open card  exit={control.returncode}  claude calls={control_calls}")
        if control.returncode != 0 or control_calls != 1:
            print(control.stdout + control.stderr)
            print("\n[NO VERDICT] the control did not start the fake `claude` exactly once")
            return 2

        cases = {
            "no deck": (project("no-deck", "none"), ()),
            "empty deck": (project("empty-deck", "empty"), ()),
            "--limit 0": (one_card, ("--limit", "0")),
            "--status active": (one_card, ("--status", "active")),
        }
        failures: list[str] = []
        for label, (cwd, flags) in cases.items():
            result, calls = run(cwd, *flags)
            layer2 = [ln for ln in result.stdout.splitlines() if ln.startswith("Layer-2")]
            print(f"--- {label}  exit={result.returncode}  claude calls={calls}")
            print(f"    {layer2[0] if layer2 else '(no Layer-2 line)'}")
            if calls:
                failures.append(f"{label}: started `claude` {calls}x with no live card selected")
            if result.returncode != 0:
                failures.append(f"{label}: exit {result.returncode}, want 0")

    if failures:
        print("\n[FAIL] defect fires:")
        for failure in failures:
            print(" -", failure)
        return 1
    print("\n[OK] defect no longer fires: no empty selection starts `claude`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
