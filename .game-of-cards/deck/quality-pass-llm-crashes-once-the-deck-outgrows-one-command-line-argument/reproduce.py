#!/usr/bin/env python3
"""Reproducer: `goc quality-pass --llm` crashes once the deck's prompt no
longer fits in one command-line argument.

`_run_sonnet_quality_pass` (goc/engine.py) runs
`claude --model sonnet -p <prompt> --output-format json`, and the prompt
holds the title, summary and DoD of every selected card. Linux caps a single
argument at 32 pages (MAX_ARG_STRLEN: 131072 bytes on 4 KiB pages), so a deck
whose cards render a prompt above that fails at exec time with E2BIG. The
call site catches CalledProcessError, ValueError, JSONDecodeError and
RuntimeError, but not OSError, so the run dies with a traceback before Claude
is ever started.

The harness drives only the public CLI (`python goc/_launch.py`), never an
engine-private name. It builds throwaway projects of synthetic open cards and
makes a fake `claude` the only thing on PATH, so no real `claude` can ever be
reached. The fake records every card title it receives (on argv or stdin) and
answers with an empty verdict list in the `--output-format json` envelope. It
then runs `goc quality-pass --llm --dry-run`:

  1. control: 5 cards. Must exit 0 with every title delivered, or the harness
     itself is broken (exit 2).
  2. verdict: 100 cards with DoDs the length of this repo's average, so the
     prompt clears the per-argument limit by a wide margin.
  3. informational: a copy of this repo's own `.game-of-cards/`. Its open
     queue grows and shrinks, so it never decides the verdict.

Exit codes: 0 = defect no longer fires (the 100-card run exits 0, prints no
traceback, and every card reaches `claude`); 1 = defect fires; 2 = harness or
precondition broken (non-Linux host, control run failed, or this script
crashed).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

CONTROL_CARDS = 5
VERDICT_CARDS = 100

FAKE_CLAUDE = r'''
import json, os, re, sys
text = " ".join(sys.argv[1:])
try:
    text += sys.stdin.read()
except Exception:
    pass
titles = re.findall(r'\\?"title\\?":\s*\\?"([a-z0-9-]+)\\?"', text)
with open(os.environ["FAKE_CLAUDE_LOG"], "a", encoding="utf-8") as fh:
    fh.write("CALL\n")
    for t in titles:
        fh.write(t + "\n")
print(json.dumps({"result": "[]"}))
'''


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


def _dod(i: int) -> str:
    # Six method-tagged items of ~270 characters: ~1.7 KB per card, the
    # average DoD + summary size of this repo's open queue on 2026-11-02.
    filler = (
        "the fix lands in the engine, the plugin mirrors are re-synced, and a "
        "regression test pins the behaviour so a later refactor cannot quietly "
        "bring the defect back without turning the suite red on the same commit"
    )
    return "".join(f"  - [ ] TDD: criterion {k} of synthetic card {i}: {filler}.\n" for k in range(1, 7))


def _write_deck(project: Path, count: int) -> list[str]:
    deck = project / ".game-of-cards" / "deck"
    deck.mkdir(parents=True)
    titles = []
    for i in range(1, count + 1):
        title = f"synthetic-card-{i:03d}"
        titles.append(title)
        card = deck / title
        card.mkdir()
        (card / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f'summary: "Synthetic open card {i} for the quality-pass argument-size reproducer."\n'
            "status: open\n"
            "stage: null\n"
            "contribution: medium\n"
            'created: "2026-11-02T00:00:00Z"\n'
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            f"{_dod(i)}"
            "---\n\n"
            f"# {title}\n\nSynthetic card body.\n",
            encoding="utf-8",
        )
        (card / "log.md").write_text("", encoding="utf-8")
    return titles


def _payload_bytes(project: Path) -> int:
    """Lower bound of the prompt size: the JSON of each card's title, summary
    and DoD (the slice the engine sends) without the instruction text around
    it. Read from the files this script wrote, not from the engine."""
    slim = []
    for card in sorted((project / ".game-of-cards" / "deck").iterdir()):
        text = (card / "README.md").read_text(encoding="utf-8")
        summary = text.split('summary: "', 1)[1].split('"\n', 1)[0]
        dod = text.split("definition_of_done: |\n", 1)[1].split("---\n", 1)[0]
        slim.append({"title": card.name, "summary": summary, "definition_of_done": dod})
    return len(json.dumps(slim, indent=2).encode("utf-8"))


def _run(root: Path, project: Path, fake_bin: Path, log: Path) -> tuple[int, str, list[str], int]:
    if log.exists():
        log.unlink()
    env = dict(os.environ)
    # The fake's directory is the WHOLE PATH. CPython's exec loop tries every
    # PATH entry in turn, so with the real PATH appended, a fake that failed to
    # start (a noexec /tmp, say) would fall through to a real `claude` and send
    # it the deck. Alone on PATH, such a failure stops the control run (exit 2)
    # instead. The engine needs nothing else from PATH here: it is started by
    # absolute interpreter path, its git probes tolerate a missing git, and the
    # shim names /bin/sh and the interpreter absolutely.
    env["PATH"] = str(fake_bin)
    env["FAKE_CLAUDE_LOG"] = str(log)
    env.pop("GOC_WORKTREE_DECK", None)
    proc = subprocess.run(
        [sys.executable, str(root / "goc" / "_launch.py"), "quality-pass", "--llm", "--dry-run"],
        cwd=str(project),
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=300,
    )
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    calls = lines.count("CALL")
    received = [ln for ln in lines if ln != "CALL"]
    return proc.returncode, proc.stderr, received, calls


def _stderr_tail(stderr: str) -> str:
    lines = [ln for ln in stderr.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else "(empty)"


def main() -> int:
    if not sys.platform.startswith("linux"):
        print(
            f"PRECONDITION: this measures Linux's per-argument limit (MAX_ARG_STRLEN); "
            f"host is {sys.platform}. Run it on Linux."
        )
        return 2
    limit = 32 * os.sysconf("SC_PAGE_SIZE")
    root = _repo_root()
    with tempfile.TemporaryDirectory(prefix="goc-qp-argv-") as tmp:
        tmp_path = Path(tmp)
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        fake_py = tmp_path / "fake_claude.py"
        fake_py.write_text(FAKE_CLAUDE, encoding="utf-8")
        shim = fake_bin / "claude"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake_py}" "$@"\n', encoding="utf-8")
        shim.chmod(0o755)
        log = tmp_path / "claude-calls.log"

        print(f"Linux per-argument limit (MAX_ARG_STRLEN): {limit} bytes")

        control = tmp_path / "control"
        control_titles = _write_deck(control, CONTROL_CARDS)
        rc, err, received, calls = _run(root, control, fake_bin, log)
        print(
            f"[control]  {CONTROL_CARDS} cards, card JSON {_payload_bytes(control)} bytes: "
            f"exit {rc}, claude calls {calls}, titles delivered {len(set(received) & set(control_titles))}/{CONTROL_CARDS}"
        )
        if rc != 0 or set(received) != set(control_titles):
            print(f"HARNESS BROKEN: the control run must pass. stderr: {_stderr_tail(err)}")
            return 2

        big = tmp_path / "big"
        big_titles = _write_deck(big, VERDICT_CARDS)
        size = _payload_bytes(big)
        if size <= limit:
            print(f"HARNESS BROKEN: synthetic card JSON is {size} bytes, not above the {limit}-byte limit")
            return 2
        rc, err, received, calls = _run(root, big, fake_bin, log)
        delivered = len(set(received) & set(big_titles))
        crashed = "Traceback (most recent call last)" in err
        print(
            f"[verdict]  {VERDICT_CARDS} cards, card JSON {size} bytes: exit {rc}, "
            f"claude calls {calls}, titles delivered {delivered}/{VERDICT_CARDS}, traceback {'yes' if crashed else 'no'}"
        )
        print(f"           stderr tail: {_stderr_tail(err)}")

        real = tmp_path / "real"
        real.mkdir()
        shutil.copytree(root / ".game-of-cards", real / ".game-of-cards")
        r_rc, r_err, r_received, r_calls = _run(root, real, fake_bin, log)
        r_crashed = "Traceback (most recent call last)" in r_err
        print(
            f"[info]     copy of this repo's deck: exit {r_rc}, claude calls {r_calls}, "
            f"titles delivered {len(set(r_received))}, traceback {'yes' if r_crashed else 'no'}"
        )
        print(f"           stderr tail: {_stderr_tail(r_err)}")

    if rc != 0 or crashed or delivered != VERDICT_CARDS:
        print(
            "\nDEFECT FIRES: `goc quality-pass --llm` cannot audit a deck whose prompt "
            "exceeds one command-line argument."
        )
        return 1
    print("\nOK: every card reached claude and the run exited 0.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # a crash in the harness is never a verdict
        traceback.print_exc()
        print("HARNESS BROKEN: reproduce.py crashed (exit 2).")
        sys.exit(2)
