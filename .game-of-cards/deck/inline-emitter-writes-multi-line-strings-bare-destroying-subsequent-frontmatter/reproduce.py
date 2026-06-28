"""Reproduce: a multi-line summary survives `_apply_summary_rewrite` end-to-end.

Two assertions on the same module:

1. `_apply_summary_rewrite(card, "Line one.\\nLine two.")` writes a README
   whose frontmatter parses back with every field intact and the two-line
   summary round-tripped (fix (b): the caller now goes through
   `emit_frontmatter`, which emits `|-` block-scalar style for multi-line
   values).

2. `_yaml_inline("Line one.\\nLine two.")` raises `FrontmatterError`
   (fix (a): the inline emitter refuses multi-line input at the
   boundary, parallel to the existing float-refusal branch, so no other
   bypassing caller can spawn the same data-loss bug family).

Run:
    uv run python .game-of-cards/deck/inline-emitter-writes-multi-line-strings-bare-destroying-subsequent-frontmatter/reproduce.py
"""

from __future__ import annotations

import sys
import tempfile
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

from goc.engine import (  # noqa: E402
    FrontmatterError,
    _apply_summary_rewrite,
    _yaml_inline,
    parse_frontmatter,
)


def _check_apply_summary_rewrite() -> list[str]:
    failures: list[str] = []
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
    new_summary = "Line one of the rewrite.\nLine two of the rewrite."

    with tempfile.TemporaryDirectory() as tmp:
        card_dir = Path(tmp)
        readme = card_dir / "README.md"
        readme.write_text(original)
        card = SimpleNamespace(path=card_dir)

        _apply_summary_rewrite(card, new_summary)

        rewritten = readme.read_text()
        print("--- rewritten readme on disk ---")
        print(rewritten)

        fm, _body = parse_frontmatter(rewritten)
        print("--- parsed frontmatter keys ---")
        print(sorted(fm.keys()))
        print("--- parsed frontmatter dict ---")
        print(dict(fm))

        expected_keys = {"title", "summary", "status", "contribution", "tags"}
        missing = sorted(expected_keys - set(fm.keys()))
        if missing:
            failures.append(f"fields vanished from parsed frontmatter: {missing}")
        if fm.get("summary") != new_summary:
            failures.append(
                "summary did not round-trip "
                f"(got {fm.get('summary')!r}, want {new_summary!r})"
            )
    return failures


def _check_yaml_inline_refuses_multiline() -> list[str]:
    failures: list[str] = []
    try:
        result = _yaml_inline("Line one.\nLine two.")
    except FrontmatterError as exc:
        print("--- _yaml_inline refusal ---")
        print(f"raised FrontmatterError as expected: {exc}")
    else:
        failures.append(
            "_yaml_inline accepted multi-line input and returned "
            f"{result!r} instead of raising FrontmatterError"
        )
    return failures


def main() -> int:
    failures = _check_apply_summary_rewrite() + _check_yaml_inline_refuses_multiline()
    if failures:
        print()
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print()
    print("OK: multi-line summary round-trips, _yaml_inline refuses multi-line.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
