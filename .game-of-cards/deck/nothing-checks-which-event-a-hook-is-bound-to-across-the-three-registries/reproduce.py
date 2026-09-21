#!/usr/bin/env python3
"""Reproduce: nothing checks WHICH event a hook script is bound to.

`AGENTS.md` says the hook event mapping stays hand-written in three registries
— `GOC_CLAUDE_HOOKS` (`goc/install.py`), `claude-plugin/hooks/hooks.json`, and
`codex-plugin/hooks/hooks.json` — because a command is not derivable from a
script name, and that `goc validate` covers all three. It covers only the
script *set*: `_plugin_registered_hook_scripts` collects basenames and the
parity check is a two-way name-set difference, so the event a script is bound
to reaches error strings only.

This script builds a throwaway REPO_ROOT-shaped tree (the live working tree is
never touched) carrying the three real hook templates and both payloads, then
plants one mis-binding per case and runs BOTH validators over it:

  1. the two payload events swapped against each other — the session primer
     fires on `Stop`, the pattern check on `SessionStart`;
  2. one payload event renamed to an event no registry knows;
  3. `GOC_CLAUDE_HOOKS` itself swapped, with both payloads left correct —
     the recipe's control, establishing whether the vendored path is stronger.

A mis-bound hook still exits 0 at runtime, so nothing downstream notices.
Exits 0 when every case is reported (bug FIXED), 1 when any case passes both
validators clean (bug PRESENT).
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import goc.engine as eng  # noqa: E402
from goc.install import GOC_CLAUDE_HOOKS  # noqa: E402

PRIMER = "deck_session_start.py"
ROUTER = "deck_prompt_router.py"
PATTERN = "pattern_generalization_check.py"

#: The event each script is written for — the mapping all three registries
#: state by hand and none of them compare.
TRUE_EVENTS = {
    "SessionStart": PRIMER,
    "UserPromptSubmit": ROUTER,
    "Stop": PATTERN,
}


def _claude_command(name: str) -> str:
    return "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/" + name


def _codex_command(name: str) -> str:
    """Codex's version-fallback wrapper — names the script three times."""
    return (
        f'sh -c \'p="${{PLUGIN_ROOT}}/hooks/{name}"; if [ ! -f "$p" ]; then '
        f'd="$(dirname "${{PLUGIN_ROOT}}")"; '
        f'p="$(ls -t "$d"/*/hooks/{name} 2>/dev/null | head -n 1)"; fi; '
        f'exec python3 "$p"\''
    )


def _registry(mapping: dict[str, str], command) -> str:
    return json.dumps({
        "hooks": {
            event: [{"hooks": [{"type": "command", "command": command(name)}]}]
            for event, name in mapping.items()
        }
    }, indent=2)


def _build_tree(root: Path, claude: dict[str, str], codex: dict[str, str]) -> None:
    """A REPO_ROOT shape whose payloads are in sync on scripts, not on events."""
    templates = root / "goc" / "templates" / "hooks"
    templates.mkdir(parents=True)
    for name in TRUE_EVENTS.values():
        (templates / name).write_text("#\n")

    for plugin, mapping, command in (
        ("claude-plugin", claude, _claude_command),
        ("codex-plugin", codex, _codex_command),
    ):
        hooks = root / plugin / "hooks"
        hooks.mkdir(parents=True)
        for name in TRUE_EVENTS.values():
            (hooks / name).write_text("#\n")
        (hooks / "hooks.json").write_text(_registry(mapping, command))


def _validate(root: Path, vendored: dict[str, str]) -> list[str]:
    """Run both hook validators against `root` with `vendored` as GOC_CLAUDE_HOOKS."""
    package, repo = eng.PACKAGE_DIR, eng.REPO_ROOT
    eng.PACKAGE_DIR, eng.REPO_ROOT = root / "goc", root
    try:
        with mock.patch.dict(GOC_CLAUDE_HOOKS, vendored, clear=True):
            return eng.validate_hook_registration() + eng.validate_plugin_hook_registration()
    finally:
        eng.PACKAGE_DIR, eng.REPO_ROOT = package, repo


def _vendored(mapping: dict[str, str]) -> dict[str, str]:
    return {
        event: "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/" + name
        for event, name in mapping.items()
    }


SWAPPED = {"Stop": PRIMER, "UserPromptSubmit": ROUTER, "SessionStart": PATTERN}
RENAMED = {"Resume": PRIMER, "UserPromptSubmit": ROUTER, "Stop": PATTERN}

CASES = (
    (
        "codex payload swaps SessionStart and Stop",
        {"claude": TRUE_EVENTS, "codex": SWAPPED, "vendored": TRUE_EVENTS},
    ),
    (
        "claude payload binds the primer to an event nothing else names",
        {"claude": RENAMED, "codex": TRUE_EVENTS, "vendored": TRUE_EVENTS},
    ),
    (
        "GOC_CLAUDE_HOOKS swaps the events both payloads agree on",
        {"claude": TRUE_EVENTS, "codex": TRUE_EVENTS, "vendored": SWAPPED},
    ),
)


def main() -> int:
    unreported: list[str] = []
    for label, case in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _build_tree(root, case["claude"], case["codex"])
            errors = _validate(root, _vendored(case["vendored"]))
        print(f"{label}:")
        if errors:
            for err in errors:
                print(f"    reported: {err}")
        else:
            print("    reported: nothing — both validators returned []")
            unreported.append(label)

    if unreported:
        print()
        print("BUG PRESENT: a mis-bound hook event passes every tripwire in:")
        for label in unreported:
            print(f"  - {label}")
        print("The script half of the registration is checked; the event half is not.")
        return 1

    print()
    print("BUG FIXED: every mis-bound event is reported by goc validate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
