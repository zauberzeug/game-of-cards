"""Reproduce: `_enforce_closure_on_integration_or_exit` is wired into
`_cmd_done` and `_cmd_done_bundle` but NOT into `_cmd_status` when the
new status is a terminal one (`disproved` or `superseded`).

This script is a *static* reproducer: it parses `goc/engine.py` with the
AST and inspects which command handlers reach the integration-check
helper. A behavioural reproducer would need to set up a temporary git
repo with `workflow.closure_on_integration: true`, file a card, flip its
status from an unintegrated HEAD, and observe that `goc done` errors
while `goc status … disproved` silently succeeds — but the asymmetry is
already evident from the call graph, and the static check is robust to
unrelated environment changes.

Expected output (defect present):
  _cmd_done:        integration check = True
  _cmd_done_bundle: integration check = True
  _cmd_status:      integration check = False  <-- DEFECT
"""

from __future__ import annotations

import ast
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


HELPER = "_enforce_closure_on_integration_or_exit"
COMMANDS = ("_cmd_done", "_cmd_done_bundle", "_cmd_status")


def calls_helper(fn_node: ast.FunctionDef) -> bool:
    for node in ast.walk(fn_node):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == HELPER:
                return True
            if isinstance(func, ast.Attribute) and func.attr == HELPER:
                return True
    return False


def main() -> int:
    engine_path = _repo_root() / "goc" / "engine.py"
    tree = ast.parse(engine_path.read_text())

    by_name: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in COMMANDS:
            by_name[node.name] = node

    missing = [name for name in COMMANDS if name not in by_name]
    if missing:
        print(f"ERROR: command(s) not found in engine.py: {missing}")
        return 2

    results = {name: calls_helper(by_name[name]) for name in COMMANDS}
    width = max(len(name) for name in COMMANDS) + 1
    for name in COMMANDS:
        marker = "" if results[name] else "  <-- DEFECT"
        print(f"{(name + ':').ljust(width)} integration check = {results[name]}{marker}")

    # The defect is: the three terminal-flip command handlers do not all
    # call the helper. Exit non-zero while the asymmetry exists so the
    # DoD's "TDD: reproduce.py exits zero" item flips green once the
    # chosen fix lands.
    if all(results.values()) or not any(results.values()):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
