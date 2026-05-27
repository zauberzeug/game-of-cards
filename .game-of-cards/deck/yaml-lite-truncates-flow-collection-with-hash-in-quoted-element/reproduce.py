"""Demonstrate that yaml_lite corrupts inline flow collections (`[...]` / `{...}`)
when a quoted element contains ` #`, and that goc's own emitter produces such
values — so a `goc`-written card round-trips to silent data loss on reload.

Run: uv run python .game-of-cards/deck/yaml-lite-truncates-flow-collection-with-hash-in-quoted-element/reproduce.py
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

from goc._vendor.yaml_lite import safe_load  # noqa: E402
from goc.engine import emit_frontmatter  # noqa: E402

fail = False

# 1) Unit level: _strip_comment is reached via safe_load for flow values.
doc = 'title: x\n' 'tags: ["a #b", c]\n' 'worker: {who: x, where: "br #1"}\n'
parsed = safe_load(doc)
print("INPUT YAML:")
print(doc)
print("safe_load ->", parsed)
print()

expected_tags = ["a #b", "c"]
expected_worker = {"who": "x", "where": "br #1"}

if parsed.get("tags") != expected_tags:
    print(f"  [FAIL] tags corrupted: {parsed.get('tags')!r} != {expected_tags!r}")
    fail = True
if parsed.get("worker") != expected_worker:
    print(f"  [FAIL] worker dropped/corrupted: {parsed.get('worker')!r} != {expected_worker!r}")
    fail = True
print()

# 2) End-to-end: the emitter PRODUCES these unparseable values from a normal
#    Python dict, so a real card written by goc loses data on reload.
fm = {"title": "x", "tags": ["a #b", "c"], "worker": {"who": "x", "where": "br #1"}}
emitted = emit_frontmatter(fm)
print("emit_frontmatter(fm):")
print(emitted)
inner = emitted.split("---", 2)[1]
reparsed = safe_load(inner)
print("reparsed ->", reparsed)
if reparsed.get("tags") != fm["tags"] or reparsed.get("worker") != fm["worker"]:
    print("  [FAIL] emit -> parse round-trip is lossy (emitter output its own parser cannot read)")
    fail = True

print()
print("RESULT:", "FAIL — defect reproduced" if fail else "PASS — defect fixed")
sys.exit(1 if fail else 0)
