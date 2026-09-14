#!/usr/bin/env python3
"""Reproduce: `goc -v` (render_table at verbose>=1) prints a card's
`summary` with a bare f-string, so a multi-line summary's continuation
lines escape the four-space indent that bounds the per-card detail block.

Exits 0 when the defect is FIXED, 1 while it is live.
"""
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

MULTI = (
    "First line of the summary.\n"
    "Second line that YAML kept as a block scalar.\n"
    "Third line."
)


def make_card(summary):
    return engine.Card(
        title="multi-line-summary-card",
        path=None,
        frontmatter={
            "title": "multi-line-summary-card",
            "status": "open",
            "contribution": "medium",
            "human_gate": "none",
            "summary": summary,
            "definition_of_done": "- [ ] MECHANICAL: x\n",
        },
        body="",
        dod_open=1,
        dod_done=0,
    )


def detail_lines(out):
    """The per-card block: everything after header, rule, and the data row."""
    return out.splitlines()[3:]


def strays(out):
    return [ln for ln in detail_lines(out) if ln and not ln.startswith("    ")]


def main():
    single = engine.render_table(
        [make_card("One line only.")], verbose=1, no_color=True
    )
    print(f"single-line summary: {len(strays(single))} unindented detail line(s)")

    multi = engine.render_table([make_card(MULTI)], verbose=1, no_color=True)
    print("--- rendered ---")
    print(multi)
    print("--- /rendered ---")

    escaped = strays(multi)
    if escaped:
        for ln in escaped:
            print(f"UNINDENTED: {ln!r}")
        print(
            f"DEFECT PRESENT: {len(escaped)} continuation line(s) escape the "
            "block indent"
        )
        return 1
    print("DEFECT FIXED: every detail line stays inside the four-space block indent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
