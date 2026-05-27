"""Reproduce: _strip_goc_block collapses the blank line that separated
user content above the GoC marker block from user content below it.

Exit 0 == the inter-paragraph blank line survives (defect fixed).
Exit 1 == the blank line was collapsed (defect fires).
"""
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import install  # noqa: E402

text = (
    "Intro paragraph.\n"
    "\n"
    "<!-- BEGIN GOC v1.2.3 -->\n"
    "body\n"
    "<!-- END GOC -->\n"
    "\n"
    "## My Section\n"
)
expected = "Intro paragraph.\n\n## My Section\n"

with tempfile.TemporaryDirectory() as d:
    path = Path(d) / "AGENTS.md"
    path.write_text(text)
    install._strip_goc_block(path)
    got = path.read_text()

print(f"expected: {expected!r}")
print(f"got:      {got!r}")
print()
if got != expected:
    print("DEFECT: blank-line separator around the marker block was collapsed")
    sys.exit(1)
print("OK: blank-line separator preserved")
sys.exit(0)
