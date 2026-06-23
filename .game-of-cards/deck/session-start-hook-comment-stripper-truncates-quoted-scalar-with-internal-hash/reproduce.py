"""Reproduce: SessionStart hook's comment stripper truncates a quoted scalar
at an internal `#`, diverging from the engine's quote-aware `_strip_comment`.

Run from a clean checkout:

    uv run python deck/session-start-hook-comment-stripper-truncates-quoted-scalar-with-internal-hash/reproduce.py

Exits non-zero while the defect is live; exits zero once the hook helper is
made quote-aware to match the engine.
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

from goc import engine  # noqa: E402
from goc._vendor import yaml_lite  # noqa: E402

# Load the hook module by path (it is a template, not an installed module).
_hook_path = ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py"
_spec = importlib.util.spec_from_file_location("_dss_repro", _hook_path)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def main() -> int:
    ok = True

    print(
        "scalar-parse divergence "
        "(hook _frontmatter_tail vs engine yaml_lite.safe_load):"
    )
    lines = [
        'waiting_on: "external # waiting on PR review"',
        'status: "done # closed early"',
        'human_gate: "decision # needs sign-off"',
    ]
    for line in lines:
        key = line.split(":", 1)[0]
        engine_val = yaml_lite.safe_load(line + "\n")[key]
        hook_val = hook._frontmatter_tail(line)
        flag = "" if engine_val == hook_val else "  <- DIVERGES"
        if engine_val != hook_val:
            ok = False
        print(f"  {line!r}")
        print(f"    engine: {engine_val!r}")
        print(f"    hook  : {hook_val!r}{flag}")

    print()
    print(
        "impede-decision divergence "
        "(hook _is_impeded vs engine waiting_impedes):"
    )
    with tempfile.TemporaryDirectory() as td:
        card_dir = Path(td) / "card"
        card_dir.mkdir()
        readme = card_dir / "README.md"
        readme.write_text(
            "---\n"
            "title: example\n"
            "status: active\n"
            "human_gate: none\n"
            "waiting_on: null\n"
            'waiting_until: "2020-01-01 # deferred, see note"\n'
            "definition_of_done: |\n"
            "  - [ ] x\n"
            "---\n"
            "body\n",
            encoding="utf-8",
        )
        card = engine.load_card(card_dir)
        engine_impeded = engine.waiting_impedes(card)
        hook_impeded = hook._is_impeded(readme)
        print(
            '  card: status=active, waiting_until="2020-01-01 # deferred, see note"'
        )
        print(
            f"    engine waiting_impedes : {engine_impeded}   "
            "(date is unparseable -> backstop hides card)"
        )
        print(
            f"    hook   _is_impeded     : {hook_impeded}  "
            "(truncated to '2020-01-01' -> elapsed -> resumable)"
        )
        if engine_impeded != hook_impeded:
            ok = False

    print()
    if ok:
        print("PASS: hook readers match the engine for quoted scalars with internal '#'.")
        return 0
    print("FAIL: hook reports a card the engine impedes as resumable.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
