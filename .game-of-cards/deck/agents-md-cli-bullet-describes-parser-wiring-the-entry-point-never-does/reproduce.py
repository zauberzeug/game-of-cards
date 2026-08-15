"""Reproduce: AGENTS.md's `goc/cli.py` bullet describes wiring cli.py never does.

Three independent probes, each deriving the truth from the tree rather than
restating it:

1. `_build_parser` is imported by `goc/cli.py` and never *called* there — the
   engine parser is built inside `engine.cli()`. Proven by walking cli.py's AST
   for a `Call` whose func is the name `_build_parser`.
2. `install` / `upgrade` are not subcommands of the engine parser. They are
   intercepted on `argv[0]` before argparse runs and routed to two standalone
   `ArgumentParser` instances, so neither appears in `goc --help`.
3. `--version` is registered by `engine._build_parser`, not by cli.py. Proven by
   finding the `version` action on the engine parser and finding no
   `add_argument("--version", ...)` anywhere in cli.py's AST.

Then the doc check: the AGENTS.md bullet still makes all three claims. Exits
non-zero while the bullet asserts wiring the code does not perform; exits zero
once the bullet describes what cli.py actually does.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
"""

from __future__ import annotations

import argparse
import ast
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

CLI_PY = ROOT / "goc" / "cli.py"
AGENTS_MD = ROOT / "AGENTS.md"


def _cli_tree() -> ast.Module:
    return ast.parse(CLI_PY.read_text(encoding="utf-8"), filename=str(CLI_PY))


def _imports_build_parser(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and any(alias.name == "_build_parser" for alias in node.names)
        for node in ast.walk(tree)
    )


def _calls(tree: ast.Module, name: str) -> bool:
    """True iff `name(...)` is called anywhere in the module."""
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == name
        for node in ast.walk(tree)
    )


def _adds_version_argument(tree: ast.Module) -> bool:
    """True iff cli.py itself registers a `--version` argparse argument."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "add_argument"):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and arg.value == "--version":
                return True
    return False


def _engine_subcommands() -> set[str]:
    from goc.engine import _build_parser

    parser = _build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    raise AssertionError("no subparsers found on the engine parser")


def _engine_has_version_action() -> bool:
    from goc.engine import _build_parser

    return any(
        "--version" in action.option_strings for action in _build_parser()._actions
    )


def _cli_bullet() -> str:
    """The `goc/cli.py` bullet of AGENTS.md's `## Code architecture` section."""
    text = AGENTS_MD.read_text(encoding="utf-8")
    section_start = text.index("## Code architecture")
    section_end = text.index("\n## ", section_start + 1)
    section = text[section_start:section_end]
    start = section.index("**`goc/cli.py`**")
    end = section.index("**`goc/engine.py`**")
    return section[start:end]


# The three claims, matched across the bullet's line wrapping.
CLAIMS = {
    "builds the engine parser via _build_parser": re.compile(
        r"[Bb]uilds\s+the\s+engine's\s+\s*argparse\s+parser\s+via\s+`_build_parser`",
        re.DOTALL,
    ),
    "bolts install + upgrade onto that parser": re.compile(
        r"bolts\s+on\s+`install`\s*\+\s*`upgrade`", re.DOTALL
    ),
    "adds --version": re.compile(r"adds\s+`--version`", re.DOTALL),
}


def main() -> int:
    tree = _cli_tree()

    imports_bp = _imports_build_parser(tree)
    calls_bp = _calls(tree, "_build_parser")
    subcommands = _engine_subcommands()
    routed_verbs = sorted({"install", "upgrade"} & subcommands)
    cli_adds_version = _adds_version_argument(tree)
    engine_adds_version = _engine_has_version_action()

    print("=== what goc/cli.py actually does ===")
    print(f"imports `_build_parser`            : {imports_bp}")
    print(f"calls   `_build_parser`            : {calls_bp}")
    print(f"registers `--version` itself       : {cli_adds_version}")
    print()
    print("=== what the engine parser actually holds ===")
    print(f"engine parser registers `--version`: {engine_adds_version}")
    print(f"engine subcommands ({len(subcommands)})            : {sorted(subcommands)}")
    print(f"of which install/upgrade           : {routed_verbs or '(none)'}")
    print()

    bullet = _cli_bullet()
    asserted = sorted(name for name, rx in CLAIMS.items() if rx.search(bullet))
    print("=== what AGENTS.md's goc/cli.py bullet claims ===")
    print(bullet.strip())
    print()
    print(f"claims still asserted              : {asserted or '(none)'}")
    print()

    facts = [
        (
            "builds the engine parser via _build_parser",
            not calls_bp,
            "cli.py imports `_build_parser` but never calls it; "
            "`engine.cli()` builds the parser itself",
        ),
        (
            "bolts install + upgrade onto that parser",
            not routed_verbs,
            "install/upgrade are intercepted on argv[0] before argparse and "
            "routed to two standalone parsers; neither is an engine subcommand "
            "(this is why `goc --help` omits them)",
        ),
        (
            "adds --version",
            not cli_adds_version and engine_adds_version,
            "`--version` is registered by `engine._build_parser`, as cli.py's "
            "own comment states",
        ),
    ]

    print("=== verdict ===")
    false_claims = []
    for claim, is_false, why in facts:
        if claim in asserted and is_false:
            false_claims.append(claim)
            print(f"[FAIL] AGENTS.md claims '{claim}' — {why}")
        elif claim in asserted:
            print(f"[ok]   AGENTS.md claims '{claim}' — and the code does it")
        else:
            print(f"[ok]   AGENTS.md no longer claims '{claim}'")

    if false_claims:
        print()
        print(
            f"{len(false_claims)} false claim(s) in AGENTS.md:148-151. The bullet is "
            "the always-loaded briefing an agent reads before touching the CLI, and it "
            "contradicts the open card "
            "`goc-help-omits-install-and-upgrade-subcommands`."
        )
        return 1

    print()
    print("AGENTS.md's goc/cli.py bullet matches what cli.py does.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
