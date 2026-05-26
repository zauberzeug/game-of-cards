#!/usr/bin/env python3
"""Reproduce: dynamic content passed as the `re.sub` *replacement* argument is
parsed for backreferences (`\\1`, `\\g<name>`, trailing `\\`).

Three install.py sites pass dynamically-built content as `repl`:
  - goc/install.py:884  `_append_marker_block`  -> marker block body
  - goc/install.py:222  `_sync_claude_import`    -> CLAUDE import block
  - goc/install.py:1040 `_write_skills_source`   -> skills_source value

If a future template / value ever contains a backslash-escape sequence, the
substitution corrupts the output or raises `re.error` mid-install.

Exit 0 = defect reproduced (or, after the fix, the literal survives). The script
asserts the *fixed* behavior, so it fails loudly while the bug is present and
passes once the callable-replacement fix lands.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from goc.install import (  # noqa: E402
    CLAUDE_IMPORT_BEGIN,
    CLAUDE_IMPORT_END,
    GOC_END,
    _append_marker_block,
    _sync_claude_import,
)

# A briefing body containing an re.sub backreference-looking sequence. A real
# template edit could introduce `\g<...>` via a regex example or a Windows path.
POISON = r"See pattern.sub(r'\g<name>', text) and the path C:\Users\x for details."


def check_append_marker_block() -> None:
    with tempfile.TemporaryDirectory() as d:
        target = Path(d) / "AGENTS.md"
        # File already carries a GoC marker block whose version matches
        # GOC_BEGIN_RE (`v[\d.]+`), so the replace branch — not the append
        # branch — runs and `POISON` is handed to `re.sub` as the replacement.
        target.write_text(
            f"Top matter.\n\n<!-- BEGIN GOC v1.2.3 -->\nold body\n{GOC_END}\n"
        )
        _append_marker_block(target, POISON, header="# Agent Guidelines")
        out = target.read_text()
        assert POISON in out, (
            "append_marker_block corrupted the briefing body:\n" + out
        )


def check_sync_claude_import() -> None:
    # The import block embeds `@{briefing_target}`; a backslash in the target
    # path would be read as a backreference by the replacement branch.
    with tempfile.TemporaryDirectory() as d:
        target = Path(d)
        claude_md = target / "CLAUDE.md"
        claude_md.write_text(
            f"Custom top.\n\n{CLAUDE_IMPORT_BEGIN}\n@OLD.md\n{CLAUDE_IMPORT_END}\n"
        )
        # AGENTS.md is the only importable target; assert the block survives the
        # replace branch intact (this site is fixed for symmetry / robustness).
        _sync_claude_import(target, "AGENTS.md")
        out = claude_md.read_text()
        assert "@AGENTS.md" in out, "sync_claude_import lost the import line:\n" + out


def main() -> int:
    check_append_marker_block()
    check_sync_claude_import()
    print("PASS: dynamic replacement bodies survive the marker-block merge verbatim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
