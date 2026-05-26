"""Reproduce: mutate_frontmatter_field truncates a block field whose value
contains an internal blank line, orphaning everything after the blank and
the frontmatter fields below it.

Exit 0 == the post-mutation frontmatter is intact: the block field is
          replaced cleanly and the trailing `status` field survives (fixed).
Exit 1 == the tail is orphaned / a following field is lost (defect fires).
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

# A definition_of_done block with an internal blank line, followed by a
# trailing `status` field whose survival is the canary for tail orphaning.
text = (
    "---\n"
    "title: t\n"
    "definition_of_done: |\n"
    "  - [ ] a\n"
    "\n"
    "  - [ ] b\n"
    "status: open\n"
    "---\n"
    "body here\n"
)

out = engine.mutate_frontmatter_field(text, "definition_of_done", "REPLACED")
fm, body = engine.parse_frontmatter(out)

dod = fm.get("definition_of_done")
status = fm.get("status")
orphaned = "- [ ] b" in out

print(f"mutated frontmatter:\n{out}")
print(f"definition_of_done -> {dod!r}")
print(f"status             -> {status!r}")
print(f"orphaned tail line  -> {orphaned}")
print()

failures = []
if dod != "REPLACED":
    failures.append(f"definition_of_done not replaced cleanly: {dod!r}")
if status != "open":
    failures.append(f"trailing status field lost: {status!r}")
if orphaned:
    failures.append("post-blank block line '- [ ] b' orphaned into frontmatter")
if body.strip() != "body here":
    failures.append(f"body corrupted: {body!r}")

if failures:
    print("DEFECT:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("OK: block field replaced and trailing field intact")
sys.exit(0)
