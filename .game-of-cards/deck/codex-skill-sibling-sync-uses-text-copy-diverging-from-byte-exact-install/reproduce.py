"""Reproduce: the Codex skill-tree sync copies non-SKILL.md sibling assets
through a text round-trip (read_text/write_text), which LF-normalizes line
endings, while every other mirror path — `goc install` (_sync_skill_tree →
shutil.copy2), the OpenClaw porter, and the Claude dir-sync — copies siblings
byte-for-byte.

So a sibling asset containing CRLF (or any bytes that differ under a text
round-trip) lands byte-identical via `goc install --codex` but LF-normalized
in the `.codex/skills/` and `codex-plugin/skills/` mirrors. This script shows
the two copy modes producing different bytes for the same input.

Run on a clean checkout:
    uv run python .game-of-cards/deck/<title>/reproduce.py
"""

import shutil
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


def main() -> int:
    raw = b"key: value\r\nother: thing\r\n"  # a sibling asset with CRLF bytes

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        src = tmpdir / "schema.yaml"
        src.write_bytes(raw)

        # What `goc install --codex` writes for a sibling (install.py: shutil.copy2).
        install_dst = tmpdir / "install" / "schema.yaml"
        install_dst.parent.mkdir()
        shutil.copy2(src, install_dst)
        install_bytes = install_dst.read_bytes()

        # What `_sync_codex_skill_tree` writes for a sibling
        # (sync_plugin_assets.py:380,383 — read_text() then write_text()).
        sync_dst = tmpdir / "sync" / "schema.yaml"
        sync_dst.parent.mkdir()
        sync_dst.write_text(src.read_text())
        sync_bytes = sync_dst.read_bytes()

        print(f"source bytes        : {raw!r}")
        print(f"goc install (copy2) : {install_bytes!r}")
        print(f"codex sync (text)   : {sync_bytes!r}")
        print()
        if install_bytes != sync_bytes and install_bytes == raw:
            print("DEFECT CONFIRMED: the Codex sibling sync LF-normalizes a CRLF")
            print("asset that `goc install --codex` preserves byte-for-byte. The")
            print("dogfood mirror would diverge from what a consumer install writes,")
            print("and the text-vs-text --check in _check_codex_skill_tree cannot")
            print("detect the skew.")
            return 0
        print("Defect not reproduced (copy modes may have been unified).")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
