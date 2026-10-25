"""Reproduce: Skill(refine-deck)'s reference.md calls the working
`goc quality-pass --llm` flag a stub.

Reads the `## Quality-pass `--llm` flag` section of the shipped template and
checks it against the engine: the parser registers `--llm` on `quality-pass`,
`_run_sonnet_quality_pass` shells out to `claude`, and `_apply_verdict_interactive`
writes accepted rewrites. A section that calls that a stub, or omits an option
whose help starts "With --llm:", misdescribes the flag.

Exit 0 — section matches the engine; 1 — drift present; 2 — harness broken
(section or parser shape not found).
"""
import argparse
import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir() and (p / "goc").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402

REFERENCE = ROOT / "goc" / "templates" / "skills" / "refine-deck" / "reference.md"
HEADING = "## Quality-pass `--llm` flag"


def main() -> int:
    text = REFERENCE.read_text()
    if HEADING not in text:
        print(f"HARNESS: {HEADING!r} not found in {REFERENCE.relative_to(ROOT)}")
        return 2
    start = text.index(HEADING)
    end = text.find("\n## ", start + 1)
    section = text[start:] if end == -1 else text[start:end]
    print(section.rstrip())
    print()

    sub = next(
        (a for a in engine._build_parser()._actions if isinstance(a, argparse._SubParsersAction)),
        None,
    )
    qp = sub.choices.get("quality-pass") if sub else None
    if qp is None:
        print("HARNESS: no quality-pass subparser")
        return 2
    llm_options = [
        a.option_strings[0]
        for a in qp._actions
        if a.option_strings and (a.help or "").startswith("With --llm:")
    ]
    if "--llm" not in {s for a in qp._actions for s in a.option_strings}:
        print("HARNESS: quality-pass registers no --llm")
        return 2

    problems = []
    if re.search(r"\bstub\b", section, re.IGNORECASE):
        problems.append(
            "calls the flag a stub, but _run_sonnet_quality_pass runs `claude` and "
            "_apply_verdict_interactive writes accepted rewrites"
        )
    for option in llm_options:
        if f"`{option}" not in section:
            problems.append(f"never names {option}, which the parser documents as 'With --llm: ...'")

    for problem in problems:
        print(f"[DRIFT] {problem}")
    if problems:
        return 1
    print("OK: the section describes the flag the engine ships.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
