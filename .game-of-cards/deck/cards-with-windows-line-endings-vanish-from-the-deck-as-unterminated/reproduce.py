"""Proof: a CRLF-authored card's frontmatter is accepted by the opener
guard but rejected by FRONTMATTER_RE, so parse_frontmatter raises
FrontmatterError("unterminated") on structurally valid input.

Run: uv run python deck/<title>/reproduce.py
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

from goc.engine import FrontmatterError, parse_frontmatter  # noqa: E402

LF = "---\nstatus: open\ntitle: x\n---\nbody here\n"
CRLF = "---\r\nstatus: open\r\ntitle: x\r\n---\r\nbody here\r\n"

print("=== LF (control) ===")
data, body = parse_frontmatter(LF)
print("parsed:", data, "| body:", repr(body))

print("\n=== CRLF (same content, Windows line endings) ===")
print("opener guard accepts CRLF:", CRLF.startswith("---\r\n"))
try:
    data, body = parse_frontmatter(CRLF)
    print("parsed:", data, "| body:", repr(body))
    print("\nRESULT: CRLF parsed fine — defect NOT present.")
except FrontmatterError as exc:
    print("RAISED FrontmatterError:", exc)
    print(
        "\nRESULT: DEFECT PRESENT — opener guard accepted '---\\r\\n' but the "
        "regex rejected it as unterminated. load_all_cards() will warn-and-drop "
        "this card from every queue/board."
    )
    sys.exit(1)
