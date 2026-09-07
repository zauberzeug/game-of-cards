#!/usr/bin/env python3
"""`goc triage`'s empty line hides the conjuncts that emptied it.

`_cmd_triage` selects on four conjuncts — `status == "open"`,
`human_gate != "none"`, `not card_is_draft`, and an optional `--worker`
substring — but reported a zero match with the constant
`No parked cards (gate ≠ none).`, naming only the second. Three unrelated deck
states rendered byte-identically.

Three cases, each a deck where the answer is "nothing", for a different reason:

  A  every parked card is an unauthored `goc new` scaffold
  B  `--worker` typo matches nothing, and no hidden draft matches it either
  C  `--worker` matches a real person whose only parked card is still a draft

Exits 0 while the defect fires, non-zero once the fix lands.
"""

from __future__ import annotations

import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

CARD = """---
title: {title}
summary: A parked card.
status: open
stage: null
contribution: medium
created: "2026-08-19T05:00:00Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: []
worker: {worker}
draft: {draft}
definition_of_done: |
  - [ ] MECHANICAL: {dod}
---

# {title}

{body}
"""


def _deck(tmp: Path, name: str, cards) -> Path:
    """Write a throwaway deck; `cards` is (title, worker, draft-as-yaml)."""
    root = tmp / name / ".game-of-cards" / "deck"
    for title, worker, draft in cards:
        d = root / title
        d.mkdir(parents=True)
        authored = draft == "false"
        d.joinpath("README.md").write_text(
            CARD.format(
                title=title,
                worker=worker,
                draft=draft,
                dod="real criteria" if authored else "(replace with real criteria)",
                body="Authored." if authored else "(write the design doc here)",
            )
        )
        d.joinpath("log.md").write_text("")
    return root


def _triage_line(deck: Path, worker: str | None = None) -> str:
    engine.DECK_DIR = deck
    args = SimpleNamespace(as_json=False, worker=worker)
    buf = io.StringIO()
    with redirect_stdout(buf):
        engine._cmd_triage(args)
    return buf.getvalue().strip().splitlines()[0]


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)

        # A — the shortest path through the tool: `goc new --gate decision`
        #     files a card that is parked AND `draft: true`, so the very next
        #     `goc triage` must not answer "nothing is waiting on you".
        drafts_only = _deck(
            tmp,
            "drafts-only",
            [("first-scaffold", "rodja", "true"), ("second-scaffold", "rodja", "true")],
        )
        line_a = _triage_line(drafts_only)
        print("A. every parked card is an unauthored `goc new` scaffold:")
        print(f"     {line_a}")
        if "draft" not in line_a.lower():
            failures.append(
                "A: the empty line does not count the unauthored draft scaffolds it dropped"
            )
        if "status: open" not in line_a:
            failures.append("A: the empty line does not name the `status: open` conjunct")
        print()

        # B — a mistyped worker. The value is unregistered, so nothing rejects
        #     it at parse time; echoing it back is the only signal there is.
        #     The lone draft is `worker: rodja`, which `--worker nobdy` also
        #     excludes, so claiming a hidden draft here would be the defect
        #     `zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface`
        #     fixed on the queue line: `goc publish` would not surface it.
        mixed = _deck(
            tmp,
            "mixed",
            [("authored-card", "rodja", "false"), ("draft-card", "rodja", "true")],
        )
        line_b = _triage_line(mixed, worker="nobdy")
        print("B. `--worker nobdy` (a typo for 'rodja'; both cards are worker: rodja):")
        print(f"     {line_b}")
        if "nobdy" not in line_b:
            failures.append("B: the empty line does not echo the `--worker` value that emptied it")
        if "draft" in line_b.lower():
            failures.append(
                "B: the empty line claims hidden drafts that `goc publish` would not surface here"
            )
        print()

        # C — the count must be worker-SCOPED, not merely worker-suppressed:
        #     rodja's only parked card is a draft, so publishing it would put a
        #     card in this very view.
        line_c = _triage_line(mixed_c := _deck(
            tmp, "worker-draft", [("rodjas-draft", "rodja", "true"), ("someone-else", "ana", "false")]
        ), worker="rodja")
        print("C. `--worker rodja`, whose only parked card is still a draft:")
        print(f"     {line_c}")
        assert mixed_c.exists()
        if "rodja" not in line_c:
            failures.append("C: the empty line does not echo the `--worker` value")
        if "draft" not in line_c.lower():
            failures.append(
                "C: the empty line drops a hidden draft that DOES match the worker filter"
            )
        print()

        # The contract being enforced, for reference.
        queue_args = SimpleNamespace(
            ready=False, waiting=False, done_flag=False, status_flag=None,
            stage_flag=None, contribution=None, human_gate="decision", since=None,
            closed_since=None, advances=None, advanced_by=None, tags=None, worker="nobdy",
        )
        print("for comparison, the queue table's own zero-match line:")
        print(f"     {engine.render_empty_query_line(queue_args, 'open', hidden_drafts=1)}")
        print()

    for f in failures:
        print(f"DEFECT: {f}")
    if failures:
        print()
        print("`render_empty_query_line`'s docstring cites `goc triage` as a surface that")
        print("already 'prints a sentence', and argues an unregistered `worker` filter must")
        print("be echoed back because no enum can validate a typo against it. triage takes")
        print("--worker and echoed nothing.")
        return 0

    print("OK: triage's empty line names every conjunct that emptied the result.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
