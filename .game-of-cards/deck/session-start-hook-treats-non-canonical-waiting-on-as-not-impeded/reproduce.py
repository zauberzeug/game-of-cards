"""Reproduce the session-start hook / engine drift on non-canonical
`waiting_on` reasons.

The engine's `waiting_impedes` gates on `reason is not None` — any
non-None reason (canonical or not) with no parseable `waiting_until`
returns True. The Python and TS hooks gate on `reason in
_IMPEDED_WAITING_ON` / `IMPEDED_WAITING_ON.has(waitingOn)` — only the
canonical enum {external, resource, deferred} — and fall through to
`return until_future` for any other reason, so they report a
typo'd or invented reason as NOT impeded.

Run: `uv run python .game-of-cards/deck/<this-card>/reproduce.py`
"""

from __future__ import annotations

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


REPO = _repo_root()
sys.path.insert(0, str(REPO))


from goc import engine  # noqa: E402


def _load_hook_module():
    spec = importlib.util.spec_from_file_location(
        "deck_session_start",
        REPO / "goc" / "templates" / "hooks" / "deck_session_start.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_card(tmp: Path, frontmatter: str) -> Path:
    card_dir = tmp / "card"
    card_dir.mkdir()
    readme = card_dir / "README.md"
    readme.write_text(
        f"---\n{frontmatter}\n---\n\n# stub\n",
        encoding="utf-8",
    )
    return readme


def _engine_impeded(frontmatter_dict: dict) -> bool:
    """Drive engine.waiting_impedes directly with a fake Card-shaped object."""

    class FakeCard:
        title = "stub"

        def __init__(self, waiting_on, waiting_until):
            self.waiting_on = waiting_on
            self.waiting_until = waiting_until

    return engine.waiting_impedes(
        FakeCard(
            frontmatter_dict.get("waiting_on"),
            frontmatter_dict.get("waiting_until"),
        )
    )


def main() -> int:
    hook = _load_hook_module()

    cases = [
        (
            "non-canonical reason, no waiting_until",
            "waiting_on: externl\n",  # typo of `external`
            {"waiting_on": "externl", "waiting_until": None},
        ),
        (
            "non-canonical reason, unparseable waiting_until",
            'waiting_on: customer-call\nwaiting_until: "not-a-date"\n',
            {"waiting_on": "customer-call", "waiting_until": "not-a-date"},
        ),
    ]

    print("waiting_impedes drift across engine and session-start hook")
    print("-" * 64)
    any_drift = False
    for label, fm_text, fm_dict in cases:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            readme = _write_card(tmp, fm_text)
            hook_verdict = hook._is_impeded(readme)
        engine_verdict = _engine_impeded(fm_dict)
        drift = engine_verdict != hook_verdict
        any_drift = any_drift or drift
        print(f"\nCase: {label}")
        print(f"  engine.waiting_impedes        = {engine_verdict}")
        print(f"  deck_session_start._is_impeded = {hook_verdict}")
        print(f"  DRIFT                          = {drift}")

    print()
    if any_drift:
        print(
            "FAIL: hook and engine disagree on at least one cell — "
            "the hook reports such cards as resumable while the engine "
            "treats them as impeded. Pre-validate / hand-edited decks "
            "would hit this gap (see card README)."
        )
        return 1
    print("PASS: hook and engine agree on all tested cells.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
