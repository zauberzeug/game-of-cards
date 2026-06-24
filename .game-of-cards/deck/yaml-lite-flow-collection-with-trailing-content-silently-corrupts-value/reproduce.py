"""Reproduce: an inline flow collection followed by non-comment trailing
content on the same line is silently corrupted instead of rejected.

Before the fix:
    tags: [bug, api]# recategorize  -> ['[bug, api]# recategorize']  (phantom element)
    worker: {who: a}# note          -> {}                            (all pairs dropped)

After the fix both raise ParseError, matching the parser's documented
fail-loud posture for malformed structural input.

Exit 0 == defect no longer fires (both inputs raise ParseError).
Exit 1 == defect still present (silent corruption observed).
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

from goc.engine import parse_frontmatter, FrontmatterError  # noqa: E402
from goc._vendor.yaml_lite import ParseError  # noqa: E402

SEQ = """---
title: x
tags: [bug, api]# recategorize
---
body
"""

MAP = """---
title: x
worker: {who: a}# note
---
body
"""


def _outcome(doc):
    # parse_frontmatter wraps the parser's ParseError in FrontmatterError;
    # either surfaced loudly at the parse boundary is the correct outcome.
    try:
        fm, _ = parse_frontmatter(doc)
        return ("parsed", fm)
    except (ParseError, FrontmatterError) as e:
        return ("raised", str(e))


def main() -> int:
    seq_kind, seq_val = _outcome(SEQ)
    map_kind, map_val = _outcome(MAP)

    if seq_kind == "parsed":
        print(f"tags   = {seq_val.get('tags')!r}   (expected: ParseError)")
    else:
        print(f"tags   -> ParseError: {seq_val}")
    if map_kind == "parsed":
        print(f"worker = {map_val.get('worker')!r}   (expected: ParseError)")
    else:
        print(f"worker -> ParseError: {map_val}")

    if seq_kind == "raised" and map_kind == "raised":
        print("PASS: both malformed flow collections rejected with ParseError")
        return 0
    print("FAIL: malformed flow collection silently corrupted instead of raising")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
