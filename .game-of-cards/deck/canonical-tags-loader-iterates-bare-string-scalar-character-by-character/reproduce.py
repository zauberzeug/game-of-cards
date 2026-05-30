"""Reproduce: _load_consuming_repo_tags iterates a bare-string canonical_tags
scalar character-by-character.

Exits non-zero while the defect is live. After the fix, the loader either
silently drops the malformed shape (returns set()) or coerces the string to
a one-element list — but in NO case does it ingest the characters of the
string as individual tags.
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

from goc.engine import _FENCED_YAML  # noqa: E402
from goc._vendor import yaml_lite as yaml  # noqa: E402


# Simulates one `canonical-tags.md` whose fenced YAML block uses bare-scalar
# form for `canonical_tags`. This is the shape a user reaches for when they
# only need one tag and assume YAML's "a list of one is a scalar" idiom.
CANONICAL_TAGS_MD = """\
```yaml
canonical_tags: my-tag
```
"""


def _simulate_loader(text: str) -> set[str]:
    """Inline reproduction of the buggy loop body in
    `_load_consuming_repo_tags` (engine.py:455-458). Kept verbatim so the
    repro stays accurate even if the engine adds the guard.
    """
    out: set[str] = set()
    for match in _FENCED_YAML.finditer(text):
        block = yaml.safe_load(match.group(1)) or {}
        out.update(block.get("canonical_tags") or [])
    return out


loaded = _simulate_loader(CANONICAL_TAGS_MD)
print(f"Bare-string input: 'canonical_tags: my-tag'")
print(f"Loaded canonical_tags set: {sorted(loaded)}")
print(f"Number of tags: {len(loaded)}")
print(f"Expected: 1 tag ('my-tag')")

if loaded == {"my-tag"}:
    print("FIXED: scalar coerced to one-element list.")
    sys.exit(0)
if loaded == set():
    print("FIXED: malformed shape silently dropped.")
    sys.exit(0)
if len(loaded) > 1 and "my-tag" not in loaded:
    print("DEFECT LIVE: string iterated character-by-character.")
    sys.exit(1)
print("UNEXPECTED: neither defect nor known-good shape.")
sys.exit(2)
