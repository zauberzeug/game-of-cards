"""Reproduce: the SessionStart hook over-coerces quoted waiting scalars.

The hook strips outer quotes before its null/bool/int coercion check, so a
quoted ``waiting_on: "true"`` (and ``"false"``/``"42"``/``"null"`` plus
``waiting_until: "null"``) — which the engine keeps as a live string reason
and treats as impeded — is wrongly resolved to absent. The card is then
announced as resumable while the engine hides it from the queue.

Exits non-zero while the defect is present (any DIVERGE row), zero once the
hook agrees with ``engine.waiting_impedes`` across the matrix.
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

_hook_path = ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py"
_spec = importlib.util.spec_from_file_location("deck_session_start", _hook_path)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


# (frontmatter line, label) — each names a card the engine treats as impeded
# (the quoted token is a live string reason) but the hook may resolve away.
CASES = [
    ('waiting_on: "true"', 'waiting_on: "true"'),
    ('waiting_on: "false"', 'waiting_on: "false"'),
    ('waiting_on: "42"', 'waiting_on: "42"'),
    ("waiting_on: 'yes'", "waiting_on: 'yes'"),
    ('waiting_on: "null"', 'waiting_on: "null"'),
    ('waiting_until: "null"', 'waiting_until: "null"'),
]


def main() -> int:
    diverged = 0
    with tempfile.TemporaryDirectory() as td:
        card_dir = Path(td) / "card"
        card_dir.mkdir()
        readme = card_dir / "README.md"
        for fm_line, label in CASES:
            readme.write_text(
                "---\n"
                "title: x\n"
                "status: active\n"
                "human_gate: none\n"
                f"{fm_line}\n"
                "---\nbody\n",
                encoding="utf-8",
            )
            card = engine.load_card(card_dir)
            e = engine.waiting_impedes(card)
            h = hook._is_impeded(readme)
            verdict = "ok" if e == h else "DIVERGE"
            if e != h:
                diverged += 1
            print(
                f"{label:22} | engine impedes={e!s:5} | "
                f"hook impedes={h!s:5} | {verdict}"
            )

    if diverged:
        print(f"\nFAIL: {diverged} divergence(s) — hook disagrees with engine.")
        return 1
    print("\nPASS: hook agrees with engine across the quoted-scalar matrix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
