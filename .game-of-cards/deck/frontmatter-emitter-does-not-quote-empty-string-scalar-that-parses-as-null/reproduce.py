"""Prove that an empty-string scalar does not round-trip through the
frontmatter emitter/parser: emit writes a bare `key: ` line, and the parser
reads that back as None — a silent str -> None mutation on any rewrite.
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

from goc.engine import emit_frontmatter, parse_frontmatter, _parser_coerces_scalar  # noqa: E402

original = {"title": "t", "summary": ""}
text = emit_frontmatter(original)
fm, _body = parse_frontmatter(text)

print("emitted frontmatter:")
print(text)
print(f"original summary:      {original['summary']!r}")
print(f"round-tripped summary: {fm.get('summary')!r}")
print()
print(f"_parser_coerces_scalar(''): {_parser_coerces_scalar('')}  "
      "(emitter believes '' is safe to emit bare)")
print(f"round-trip preserved:       {fm.get('summary') == original['summary']}")

if fm.get("summary") != original["summary"]:
    print("\nFAIL: empty string round-tripped to a different value "
          f"({fm.get('summary')!r}); the emitter must quote it as \"\".")
    sys.exit(1)

print("\nOK: empty string round-trips intact.")
sys.exit(0)
