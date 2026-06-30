#!/usr/bin/env python3
"""Reproduce: pattern-generalization hook `_enabled` only accepted lowercase `true`.

The hook's opt-in gate matched `pattern_generalization_check\\s*:\\s*(false|true)`
and compared against the literal `"true"`, so every other YAML-true spelling
the engine's yaml_lite coerces to True (`True`, `TRUE`, `yes`, `Yes`, `YES`)
silently left the hook DISABLED — intended-on → actually-off.

PASS once `_enabled` accepts the full `_TRUE_SET` while keeping `false`/absent
disabled.
"""
import importlib.util
import tempfile
from pathlib import Path

HOOK = (
    Path(__file__).resolve().parents[3]
    / "goc"
    / "templates"
    / "hooks"
    / "pattern_generalization_check.py"
)

spec = importlib.util.spec_from_file_location("pgc", HOOK)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _enabled_for(value: str | None) -> bool:
    d = Path(tempfile.mkdtemp())
    if value is not None:
        goc = d / ".game-of-cards"
        goc.mkdir(parents=True, exist_ok=True)
        (goc / "config.yaml").write_text(
            f"hooks:\n  pattern_generalization_check: {value}\n", encoding="utf-8"
        )
    return mod._enabled(str(d))


def main() -> int:
    enable_spellings = ["true", "True", "TRUE", "yes", "Yes", "YES"]
    disable_cases = {"false": "false", "False": "False", "absent-key": None}

    failures = []
    for s in enable_spellings:
        if not _enabled_for(s):
            failures.append(f"{s!r} -> _enabled=False (expected True)")
    for label, val in disable_cases.items():
        if _enabled_for(val):
            failures.append(f"{label} -> _enabled=True (expected False)")

    if failures:
        print("FAIL")
        for f in failures:
            print("  " + f)
        return 1
    print("PASS: all YAML-true spellings enable; false/absent stay disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
