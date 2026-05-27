"""Reproduce: _write_skills_source's regex back-consumes blank-line
separators (and a preceding comment line's body) above the skills_source
key, contradicting its docstring's "preserves comments and ordering" claim.

Run: uv run python .game-of-cards/deck/skills-source-rewrite-regex-eats-blank-lines-above-the-key/reproduce.py
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

from goc.install import _write_skills_source  # noqa: E402


def run_case(label: str, config_text: str, expected: str) -> bool:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        cfg_dir = target / ".game-of-cards"
        cfg_dir.mkdir()
        cfg = cfg_dir / "config.yaml"
        cfg.write_text(config_text)
        _write_skills_source(target, "plugin")
        out = cfg.read_text()
    ok = out == expected
    print(f"--- {label}")
    print(f"  input    : {config_text!r}")
    print(f"  output   : {out!r}")
    print(f"  expected : {expected!r}")
    print(f"  preserved: {ok}")
    print()
    return ok


def main() -> int:
    results = []

    # Case 1: two blank-line separators above an active key.
    results.append(
        run_case(
            "blank separators above an active skills_source key",
            "auto_commit: true\n\n\nskills_source: auto\n",
            "auto_commit: true\n\n\nskills_source: plugin\n",
        )
    )

    # Case 2: a blank line above a commented-out key — the comment line
    # above is also clobbered.
    results.append(
        run_case(
            "blank line above a commented skills_source key",
            "# top comment\n\n# skills_source: vendored\n",
            "# top comment\n\nskills_source: plugin\n",
        )
    )

    all_preserved = all(results)
    print("=" * 60)
    if all_preserved:
        print("PASS: blank lines / comments preserved (defect absent).")
        return 0
    print("FAIL: _write_skills_source destroyed surrounding lines.")
    print("The regex char class [#\\s]* matches \\n, so under re.MULTILINE")
    print("it back-consumes preceding blank lines and comment bodies,")
    print("violating the docstring's 'preserves comments and ordering'.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
