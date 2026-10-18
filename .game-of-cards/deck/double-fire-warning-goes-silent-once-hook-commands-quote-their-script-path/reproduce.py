"""Reproduce: the hook double-fire warning goes silent once GOC_CLAUDE_HOOKS
quotes its script paths.

`validate_plugin_hook_double_fire` learns GoC's hook script names from
`engine._goc_hook_basenames`, which splits each GOC_CLAUDE_HOOKS command on
"/" itself instead of reading it through `install.claude_hook_bindings`, the
registry's one command-to-script walk. Under the quoted command form that
`hook-command-registrations-word-split-on-install-paths-with-spaces`
prescribes (`python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/x.py"`), the stray
parse keeps the closing quote on every name and the warning stops firing for
a repo that does double-fire. The settings are written by the real vendored
install writer (`_merge_claude_settings`), so they are what a consumer gets.

Exit 1 while the defect fires, 0 once the two parses agree and the warning
survives the quoted form.
"""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from goc import engine, install  # noqa: E402

PLUGIN_KEY = "game-of-cards@zauberzeug-claude"


def quoted(registry: dict[str, str]) -> dict[str, str]:
    """The registry with each script path quoted, as the spaces card prescribes."""
    return {
        event: command.replace("${CLAUDE_PROJECT_DIR}/", '"${CLAUDE_PROJECT_DIR}/', 1) + '"'
        for event, command in registry.items()
    }


def probe(label: str) -> tuple[list[str], list[str], int]:
    """Install vendored hooks with the live registry, enable the plugin, validate."""
    shared = sorted(install.claude_hook_bindings()[0])
    stray = sorted(engine._goc_hook_basenames())
    home = Path(tempfile.mkdtemp())
    repo = Path(tempfile.mkdtemp())
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(
        json.dumps({"enabledPlugins": {PLUGIN_KEY: True}}), encoding="utf-8"
    )
    install._merge_claude_settings(repo / ".claude" / "settings.json")
    warnings = engine.validate_plugin_hook_double_fire(repo_root=repo, home=home)
    print(f"[{label}]")
    print(f"  sample command               : {next(iter(install.GOC_CLAUDE_HOOKS.values()))}")
    print(f"  claude_hook_bindings names   : {shared}")
    print(f"  _goc_hook_basenames names    : {stray}")
    print(f"  double-fire warnings (want 1): {len(warnings)}")
    return shared, stray, len(warnings)


def existing_suite_result() -> unittest.TestResult:
    import test_validate_plugin_hook_double_fire as suite

    loader = unittest.defaultTestLoader
    runner = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0)
    return runner.run(loader.loadTestsFromModule(suite))


def main() -> int:
    probe("registry as shipped")
    with mock.patch.dict(install.GOC_CLAUDE_HOOKS, quoted(dict(install.GOC_CLAUDE_HOOKS)), clear=True):
        shared, stray, count = probe("registry with quoted script paths")
        result = existing_suite_result()
        print(
            f"  existing double-fire suite under the quoted registry: "
            f"{result.testsRun} run, {len(result.failures)} failed, {len(result.errors)} errors"
        )
    defect = stray != shared or count != 1
    if defect:
        print(
            "DEFECT: _goc_hook_basenames diverges from claude_hook_bindings under the quoted "
            "registry and the plugin+vendored double-fire warning goes silent"
        )
        return 1
    print("OK: both parses agree and the double-fire warning survives the quoted registry")
    return 0


if __name__ == "__main__":
    sys.exit(main())
