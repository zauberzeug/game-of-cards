"""Reproduce: a non-mapping config.yaml crashes load_deck_config's callers.

A bare-list or scalar `.game-of-cards/config.yaml` parses to a Python
list/str. `load_deck_config()` returns it unguarded (only `or {}` for the
falsy case), so `auto_commit_enabled()` / `get_skills_source()` raise
AttributeError when they call `.get()` on it.

Exits 0 when the defect is FIXED (non-mapping config coerced to {}), 1 when
the defect fires.
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

import tempfile
from goc import engine


def _run_with_config(text: str):
    """Point the engine's config paths at a temp file holding `text` and
    return (ok, detail) for calling the two real consumers."""
    with tempfile.TemporaryDirectory() as d:
        cfg = Path(d) / "config.yaml"
        cfg.write_text(text)
        orig_new = engine.GAME_OF_CARDS_CONFIG_FILE
        orig_legacy = engine.LEGACY_DECK_CONFIG_FILE
        engine.GAME_OF_CARDS_CONFIG_FILE = cfg
        engine.LEGACY_DECK_CONFIG_FILE = Path(d) / "does-not-exist.yaml"
        try:
            data = engine.load_deck_config()
            if not isinstance(data, dict):
                return False, f"load_deck_config returned {type(data).__name__}, not dict"
            # Exercise the real consumers that call .get() on the config.
            data.get("workflow")
            engine.get_skills_source()
            return True, "coerced to dict; consumers ran clean"
        except Exception as exc:  # noqa: BLE001
            return False, f"{type(exc).__name__}: {exc}"
        finally:
            engine.GAME_OF_CARDS_CONFIG_FILE = orig_new
            engine.LEGACY_DECK_CONFIG_FILE = orig_legacy


CASES = {
    "bare list": "- a\n- b\n",
    "scalar string": "just a string\n",
    "valid mapping (control)": "skills_source: vendored\n",
    "empty file (control)": "",
}

failures = []
for name, text in CASES.items():
    ok, detail = _run_with_config(text)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    # Controls must stay OK; malformed cases must not crash once fixed.
    if not ok:
        failures.append(name)

if failures:
    print(f"\nDEFECT PRESENT: {len(failures)} case(s) crashed: {failures}")
    sys.exit(1)
print("\nAll cases handled without crashing — defect fixed.")
sys.exit(0)
