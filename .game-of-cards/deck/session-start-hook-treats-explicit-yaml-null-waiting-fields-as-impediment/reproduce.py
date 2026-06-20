"""Reproduce: SessionStart hook treats explicit YAML-null waiting fields as an
impediment, diverging from the engine's `waiting_impedes`.

A card whose frontmatter carries `waiting_on: null` (or `~`, `Null`, `NULL`) or
`waiting_until: null` has NO active impediment by the engine's reading — its
yaml_lite parser resolves those literals to None. The hook's field readers
return the raw token string, which `_is_impeded` then treats as a live overlay.

Exit 0 once the hook agrees with the engine on every case below.
"""

import importlib.util
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

import goc.engine as engine  # noqa: E402

_HOOK_PATH = ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py"
_spec = importlib.util.spec_from_file_location("deck_session_start", _HOOK_PATH)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def _card(frontmatter_lines: str):
    d = Path(tempfile.mkdtemp())
    (d / "README.md").write_text(
        f"---\n{frontmatter_lines}\n---\n\nbody\n", encoding="utf-8"
    )
    return d


CASES = [
    ("status: active\nwaiting_on: null", "waiting_on: null"),
    ("status: active\nwaiting_until: null", "waiting_until: null"),
    ("status: active\nwaiting_on: ~", "waiting_on: ~"),
    ("status: active\nwaiting_on: Null", "waiting_on: Null"),
    ("status: active\nwaiting_on: NULL", "waiting_on: NULL"),
    ("status: active\nwaiting_on: external", "waiting_on: external (control)"),
    ("status: active\nwaiting_on: ", "waiting_on: (empty)"),
]


def main() -> int:
    diverged = 0
    for fm, label in CASES:
        d = _card(fm)
        hook_view = hook._is_impeded(d / "README.md")
        engine_view = engine.waiting_impedes(engine.load_card(d))
        agree = hook_view == engine_view
        if not agree:
            diverged += 1
        flag = "" if agree else "  <-- DIVERGE"
        print(
            f"{label:35s}: hook={str(hook_view):5s} "
            f"engine={str(engine_view):5s}{flag}"
        )
    if diverged:
        print(f"\nFAIL: {diverged} case(s) diverge — hook misreports impediment.")
        return 1
    print("\nOK: hook agrees with engine on all cases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
