"""Reproduce: pages.yml embeds a second, stale llms.txt body.

Detects the heredoc `(out / "llms.txt").write_text(...)` in
`.github/workflows/pages.yml`, checks it for the known-stale markers,
and shows it diverges from the maintained `site/llms.txt` (which wins
on the deployed site only because the verbatim site/ copy runs later).

Exits non-zero while the embedded body exists; exits zero once
site/llms.txt is the single source of truth.
"""

import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()

STALE_MARKERS = [
    "creates `deck/`",
    "goc install --agents claude",
    "`goc status` prints an empty deck",
]


def main() -> int:
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text()
    m = re.search(
        r'\(out / "llms\.txt"\)\.write_text\("""(.*?)"""', workflow, re.DOTALL
    )
    if m is None:
        print(
            "[OK] pages.yml no longer embeds its own llms.txt body — "
            "site/llms.txt is the single source of truth."
        )
        return 0

    body = m.group(1)
    print("[FAIL] pages.yml embeds its own llms.txt body (heredoc write found)")
    for marker in STALE_MARKERS:
        if marker in body:
            print(f"       stale marker present: {marker!r}")
    site_copy = ROOT / "site" / "llms.txt"
    if site_copy.exists() and body.replace("          ", "") != site_copy.read_text():
        print(
            "       embedded body differs from site/llms.txt "
            "(site copy wins today only by copy order)"
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
