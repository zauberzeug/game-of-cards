"""Proof: the GoC marker-merge silently rewrites a CRLF file to LF.

`goc install` / `goc upgrade` merge their guidance block into AGENTS.md /
CLAUDE.md via `_append_marker_block`, which reads with `Path.read_text()`
and writes with `Path.write_text()`. Both apply Python's universal-newline
translation, so a Windows-authored (CRLF) briefing file has EVERY line —
including the user's own content outside the GoC markers — normalized to
LF on each run. The documented contract says content outside the markers
is preserved; the bytes are not.

Exit 0 == defect reproduced (CR bytes outside the GoC block were dropped).
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc.install import GOC_BEGIN, GOC_END, _append_marker_block  # noqa: E402


def main() -> int:
    with TemporaryDirectory() as d:
        target = Path(d) / "AGENTS.md"
        # A CRLF-authored file: user content above and below an existing block.
        user_lines = [
            "# Agent Guidelines",
            "",
            "My house rules above the GoC block.",
            "",
            GOC_BEGIN,
            "old goc body",
            GOC_END,
            "",
            "My house rules below the GoC block.",
            "",
        ]
        raw = "\r\n".join(user_lines).encode("utf-8")
        target.write_bytes(raw)
        cr_before = raw.count(b"\r")

        _append_marker_block(target, "new goc body", header="# Agent Guidelines")

        out = target.read_bytes()
        cr_after = out.count(b"\r")

        print(f"CR bytes before merge: {cr_before}")
        print(f"CR bytes after  merge: {cr_after}   (expected: still {cr_before})")
        user_kept = b"My house rules below the GoC block." in out
        crlf_kept_outside_block = b"My house rules below the GoC block.\r\n" in out
        print(f"user content text preserved:        {user_kept}")
        print(f"user content CRLF line-ending kept: {crlf_kept_outside_block}   (expected True)")

        if cr_after < cr_before:
            print(
                f"\nDEFECT REPRODUCED: {cr_before - cr_after} CR bytes silently "
                "dropped; the whole file was rewritten LF-only."
            )
            return 0
        print("\nNo defect: CRLF line endings preserved.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
