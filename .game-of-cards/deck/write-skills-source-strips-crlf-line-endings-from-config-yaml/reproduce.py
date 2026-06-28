"""Reproduce: _write_skills_source strips CRLF line endings from config.yaml.

A consumer whose `.game-of-cards/config.yaml` was authored with CRLF
(`\r\n`) line endings has every line rewritten to LF the first time
`goc install` / `goc upgrade` / a skills-source mode switch calls
`_write_skills_source`. The function reads with `Path.read_text()`
(universal-newline translation collapses CRLF -> LF) and writes back with
`Path.write_text()` (LF only), so the whole file — including untouched
lines — loses its CRLF convention.

Expected (after fix): only the targeted `skills_source:` line changes;
the file's CRLF convention is preserved (CR byte count unchanged), the
same way AGENTS.md / CLAUDE.md are preserved via `_read_text_keep_newline`
/ `_write_text_keep_newline`.
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

from goc.install import _write_skills_source


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        goc_dir = repo / ".game-of-cards"
        goc_dir.mkdir()
        config = goc_dir / "config.yaml"
        # CRLF-authored config with a commented skills_source example line.
        raw = (
            "# GoC project config\r\n"
            "deck_dir: .game-of-cards/deck\r\n"
            "# skills_source: auto\r\n"
            "some_key: value\r\n"
        ).encode("utf-8")
        config.write_bytes(raw)

        before = config.read_bytes().count(b"\r")
        _write_skills_source(repo, "vendored")
        after_bytes = config.read_bytes()
        after = after_bytes.count(b"\r")

        print(f"CR bytes before: {before}")
        print(f"CR bytes after:  {after}")
        print("--- resulting file (repr) ---")
        print(repr(after_bytes.decode("utf-8")))

        # The skills_source line must be set regardless.
        assert b"skills_source: vendored" in after_bytes, "skills_source not written"

        if after != before:
            print(
                f"\nDEFECT CONFIRMED: CRLF stripped — {before} CR bytes became {after}."
            )
            return 1
        print("\nOK: CRLF preserved; only the skills_source line changed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
