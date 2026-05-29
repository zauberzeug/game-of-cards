"""Reproduce: `_apply_summary_rewrite` corrupts the frontmatter when the LLM
returns a multi-line summary.

Reachability: `goc quality-pass --llm` accepts an LLM-authored summary
rewrite (`_apply_verdict_interactive`, engine.py:3081 -> `_apply_summary_rewrite`,
engine.py:3053-3058). The prompt at engine.py:2942-2949 invites multi-sentence
summaries, so a `\n` in the model output is a realistic event. `_yaml_inline`
documents (engine.py:208-209) that multi-line strings are NOT supported here,
but does not enforce the contract — the value falls through to a bare unquoted
emit, the rewrite writes `summary: line1\nline2` to disk, and `line2` (plus
every frontmatter field below it) becomes garbage.

Run:
    uv run python deck/inline-emitter-writes-multi-line-strings-bare-destroying-subsequent-frontmatter/reproduce.py
"""

from __future__ import annotations

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

from goc.engine import (  # noqa: E402
    _yaml_inline,
    mutate_frontmatter_field,
    parse_frontmatter,
)


def main() -> int:
    original = (
        "---\n"
        "title: t\n"
        "summary: orig\n"
        "status: open\n"
        "contribution: medium\n"
        "tags: [bug]\n"
        "---\n"
        "body\n"
    )

    # Simulate the `_apply_summary_rewrite` call path verbatim — no caller
    # changes, just the bytes the LLM-driven flow writes today.
    new_summary = "Line one of the rewrite.\nLine two of the rewrite."
    rewritten = mutate_frontmatter_field(original, "summary", _yaml_inline(new_summary))

    print("--- rewritten readme on disk ---")
    print(rewritten)

    fm, _body = parse_frontmatter(rewritten)
    print("--- parsed frontmatter keys ---")
    print(sorted(fm.keys()))
    print("--- parsed frontmatter dict ---")
    print(dict(fm))

    expected_keys = {"title", "summary", "status", "contribution", "tags"}
    missing = sorted(expected_keys - set(fm.keys()))
    summary_full = fm.get("summary") == new_summary

    if missing or not summary_full:
        print()
        if missing:
            print(f"FAIL: fields vanished from parsed frontmatter: {missing}")
        if not summary_full:
            print(
                "FAIL: summary did not round-trip "
                f"(got {fm.get('summary')!r}, want {new_summary!r})"
            )
        return 1

    print()
    print("OK: every frontmatter field survived and the summary round-tripped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
