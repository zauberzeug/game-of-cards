"""Reproduce the OpenClaw plugin tool-verb drift.

Walks the argparse subparsers registered by `goc.engine._build_parser`
and compares against the `GOC_VERBS` literal-union shipped by the
OpenClaw plugin (read out of the compiled `dist/index.js` so the
assertion targets the artifact users actually load).

Exits non-zero when the two diverge — which they do today: `wait`
(`goc/engine.py:2649`) and `repair-edges` (`goc/engine.py:2687`) are
registered in the engine but absent from `GOC_VERBS`.
"""
from __future__ import annotations

import re
import sys
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


def engine_subparsers() -> list[str]:
    """Return the verb list registered by `_build_parser`, in declaration order."""
    import argparse

    parser = engine._build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            # Python 3.7+ preserves dict insertion order for `choices`.
            return list(action.choices.keys())
    raise RuntimeError("could not locate subparsers on the goc parser")


GOC_VERBS_RE = re.compile(
    r"var\s+GOC_VERBS\s*=\s*\[([^\]]*)\]",
    re.MULTILINE,
)


def openclaw_verbs() -> list[str]:
    """Parse the `GOC_VERBS` array out of the compiled OpenClaw plugin bundle."""
    dist = REPO / "openclaw-plugin" / "dist" / "index.js"
    text = dist.read_text(encoding="utf-8")
    m = GOC_VERBS_RE.search(text)
    if not m:
        raise RuntimeError(f"GOC_VERBS not found in {dist}")
    body = m.group(1)
    return [token.strip().strip('"').strip("'") for token in body.split(",") if token.strip()]


def main() -> int:
    engine_verbs = engine_subparsers()
    plugin_verbs = openclaw_verbs()
    print(f"engine subparsers: {', '.join(engine_verbs)}")
    print(f"GOC_VERBS:         {', '.join(plugin_verbs)}")

    missing = [v for v in engine_verbs if v not in set(plugin_verbs)]
    extra = [v for v in plugin_verbs if v not in set(engine_verbs)]

    if missing:
        print(f"missing from GOC_VERBS: {missing}")
    if extra:
        print(f"extra in GOC_VERBS (not a real engine verb): {extra}")

    if not missing and not extra:
        print("OK: engine and plugin tool-verb lists agree")
        return 0

    print(
        f"FAIL: {len(missing)} verb(s) registered in goc/engine.py are not "
        f"callable through the OpenClaw plugin tool"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
