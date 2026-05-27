"""Reproduce: README.md whose frontmatter parses to a non-mapping YAML value
(a block list, or certain bare scalars) crashes load_card with a raw
AttributeError instead of raising the FrontmatterError the loader contract
promises for malformed frontmatter.

Run: uv run python deck/<this-card>/reproduce.py
Pre-fix: the list case raises AttributeError("'list' object has no attribute
'get'") — a raw traceback that points away from the actual problem.
Post-fix: parse_frontmatter raises FrontmatterError naming the card/shape.
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

from goc import engine  # noqa: E402

CASES = {
    "top-level list": "---\n- a\n- b\n---\nbody\n",
    "bare scalar string": "---\njustastring\n---\nbody\n",
    "top-level int": "---\n42\n---\nbody\n",
}


def main() -> int:
    failures = []
    for name, text in CASES.items():
        d = Path(tempfile.mkdtemp())
        (d / "README.md").write_text(text)
        try:
            card = engine.load_card(d)
            outcome = f"returned {type(card).__name__ if card else 'None'}"
            ok = card is None  # acceptable: treated as non-card
        except engine.FrontmatterError as exc:
            outcome = f"FrontmatterError: {exc}"
            ok = True  # the contract: coherent malformed-frontmatter signal
        except Exception as exc:  # noqa: BLE001
            outcome = f"{type(exc).__name__}: {exc}"
            ok = False  # raw traceback = the defect
        print(f"[{'PASS' if ok else 'FAIL'}] {name:20s} -> {outcome}")
        if not ok:
            failures.append(name)

    print()
    if failures:
        print(f"DEFECT PRESENT: {len(failures)} case(s) raised a non-"
              f"FrontmatterError exception: {', '.join(failures)}")
        return 1
    print("OK: all non-mapping frontmatter shapes handled coherently")
    return 0


if __name__ == "__main__":
    sys.exit(main())
