"""Reproduce: .claude/settings.json that parses to a non-dict crashes install.

Pre-fix: this script exits 1 — both `_merge_claude_settings` and
`_strip_goc_settings_entries` raise `AttributeError` when the parsed
JSON is `null`, a list, a string, or a number.

Post-fix: this script exits 0 — both functions backup-and-warn (merge)
or warn-and-skip (strip), matching the existing `JSONDecodeError`
branches.

Run via:
    uv run python .game-of-cards/deck/claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror/reproduce.py
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

from goc.install import _merge_claude_settings, _strip_goc_settings_entries  # noqa: E402


NON_DICT_INPUTS = [
    ("null", "JSON null"),
    ("[]", "empty JSON array"),
    ('"hello"', "JSON string"),
    ("42", "JSON number"),
]


def _try(label: str, fn, settings_path: Path) -> bool:
    """Return True if fn(settings_path) ran without an unhandled exception."""
    try:
        fn(settings_path)
        return True
    except Exception as exc:
        print(f"  {label}: CRASHED with {type(exc).__name__}: {exc}")
        return False


def main() -> int:
    failures = 0
    for body, description in NON_DICT_INPUTS:
        print(f"--- input: settings.json = {body!r}  ({description})")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "settings.json"
            p.write_text(body + "\n")
            if not _try("_merge_claude_settings", _merge_claude_settings, p):
                failures += 1

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "settings.json"
            p.write_text(body + "\n")
            if not _try("_strip_goc_settings_entries", _strip_goc_settings_entries, p):
                failures += 1

    print()
    if failures:
        print(f"REPRO: {failures} non-dict input(s) crashed install helpers — defect present.")
        return 1
    print("REPRO: all non-dict inputs handled gracefully — defect fixed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
