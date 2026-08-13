"""No guard ties the plugin payloads' `hooks.json` to `goc/templates/hooks/*.py`.

Builds a throwaway copy of the repo's plugin-payload layout, adds a fourth hook
template, runs the real `scripts/sync_plugin_assets.py` over it, and then asks
every mechanism that is supposed to notice: is the new script registered?

The sync copies the file into `claude-plugin/hooks/`, `codex-plugin/hooks/` and
`.claude/hooks/`, but neither plugin's hand-maintained `hooks.json` gains an
entry — so on the default (plugin) install path the script ships as a file no
host ever invokes. The inverse is checked too: retiring a template prunes the
mirrored file while both registries keep a command pointing at it.

`engine.validate_hook_registration` is the guard that already enforces exactly
this invariant — for `GOC_CLAUDE_HOOKS`, the vendored `--local-skills` path
only. This script calls it, and the engine's whole validator set, against the
drifted tree to show that nothing fires.

Exits non-zero while the defect is present, zero once a parity check covers the
two plugin registries.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
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

PROBE = "probe_new_hook.py"

# The sync script walks every payload pair and imports the package it is
# syncing, so it needs the tree essentially whole. `.git` and the deck are the
# only large parts and neither is read: staging is well under a second.
STAGE_IGNORE = shutil.ignore_patterns(
    ".git", ".game-of-cards", "__pycache__", "node_modules"
)

# Every `<name>.py` a hooks.json command mentions. Claude's command names the
# script once (`python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<name>.py`); Codex's shell
# fallback names it three times. A set collapses both shapes.
_PY_IN_COMMAND = re.compile(r"[\w.-]+\.py")


def _registered_scripts(hooks_json: Path) -> set[str]:
    """Script basenames every command in `hooks_json` refers to."""
    data = json.loads(hooks_json.read_text())
    out: set[str] = set()
    for groups in data.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                out.update(_PY_IN_COMMAND.findall(hook.get("command", "")))
    return out


def _stage(tree: Path) -> Path:
    shutil.copytree(ROOT, tree, ignore=STAGE_IGNORE)
    return tree


def _sync(tree: Path) -> None:
    """Run the real sync script over the staged tree.

    It ends with `git add`, which fails outside a repo — the copying it is
    being measured on has already happened by then, so the exit code is not
    the signal here.
    """
    subprocess.run(
        [sys.executable, "scripts/sync_plugin_assets.py"],
        cwd=tree, capture_output=True, text=True,
    )


def _guard_errors(tree: Path) -> list[str]:
    """Every error `goc validate`'s hook guards raise about the staged tree.

    The engine reads `PACKAGE_DIR` and `REPO_ROOT` at call time, so pointing
    both at the staged copy measures the real validators without a probe script
    ever being written into the working tree.
    """
    package, repo = engine.PACKAGE_DIR, engine.REPO_ROOT
    engine.PACKAGE_DIR, engine.REPO_ROOT = tree / "goc", tree
    try:
        checks = [engine.validate_hook_registration]
        # Absent until the fix lands; asking for it by name keeps the probe
        # honest about which guard is missing rather than which one is renamed.
        plugin_check = getattr(engine, "validate_plugin_hook_registration", None)
        if plugin_check is not None:
            checks.append(plugin_check)
        return [err for check in checks for err in check()]
    finally:
        engine.PACKAGE_DIR, engine.REPO_ROOT = package, repo


def _reports(tree: Path, script: str) -> bool:
    """True iff some guard names `script` alongside a plugin payload."""
    return any(
        script in err and any(p in err for p in ("claude-plugin", "codex-plugin"))
        for err in _guard_errors(tree)
    )


def main() -> int:
    print("plugin hooks.json ← goc/templates/hooks/ registration parity\n")
    failures: list[str] = []

    retired = "deck_prompt_router.py"

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # --- direction 1: a new hook template ---------------------------------
        added = _stage(tmp / "added")
        (added / "goc" / "templates" / "hooks" / PROBE).write_text(
            "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n"
        )
        _sync(added)

        print(f"  ADDED goc/templates/hooks/{PROBE}, then ran sync_plugin_assets.py\n")
        drifted = False
        for plugin in ("claude-plugin", "codex-plugin"):
            hooks_dir = added / plugin / "hooks"
            shipped = (hooks_dir / PROBE).exists()
            registered = PROBE in _registered_scripts(hooks_dir / "hooks.json")
            print(f"    {plugin:<14} ships the file: {shipped!s:<5}  "
                  f"hooks.json registers it: {registered}")
            drifted |= shipped and not registered
        if not drifted:
            failures.append(
                "setup did not drift: the sync registered the new script by itself, "
                "so this probe no longer measures anything"
            )
        print(f"\n    reported by goc validate's guards: {_reports(added, PROBE)}")
        if not _reports(added, PROBE):
            failures.append(f"a payload shipping an unregistered {PROBE} goes unreported")

        # --- direction 2: a retired hook template ------------------------------
        gone = _stage(tmp / "retired")
        (gone / "goc" / "templates" / "hooks" / retired).unlink()
        _sync(gone)

        print(f"\n  REMOVED goc/templates/hooks/{retired}, then ran sync_plugin_assets.py\n")
        drifted = False
        for plugin in ("claude-plugin", "codex-plugin"):
            hooks_dir = gone / plugin / "hooks"
            shipped = (hooks_dir / retired).exists()
            registered = retired in _registered_scripts(hooks_dir / "hooks.json")
            print(f"    {plugin:<14} ships the file: {shipped!s:<5}  "
                  f"hooks.json registers it: {registered}")
            drifted |= registered and not shipped
        if not drifted:
            failures.append(
                "setup did not drift: retiring the template also cleared the "
                "registration, so this probe no longer measures anything"
            )
        print(f"\n    reported by goc validate's guards: {_reports(gone, retired)}")
        if not _reports(gone, retired):
            failures.append(f"a registration pointing at pruned {retired} goes unreported")

        # --- control: the shipped tree must stay clean --------------------------
        pristine = _stage(tmp / "pristine")
        noise = [e for e in _guard_errors(pristine) if "hook registration" in e]
        print(f"\n  CONTROL — untouched tree, hook-registration errors: {len(noise)}")
        for err in noise:
            print(f"    {err}")
        if noise:
            failures.append("the guard fires on the shipped tree — false positive")

    print()
    if failures:
        print("DEFECT PRESENT — the two plugin hooks.json registries are unguarded:")
        for f in failures:
            print(f"  - {f}")
        print(
            "\nThe hook list is derived from templates/hooks/*.py for the file copy and\n"
            "for `GOC_CLAUDE_HOOKS`, but the two payload registries that the DEFAULT\n"
            "install path actually reads are hand-maintained with no parity check."
        )
        return 1

    print("OK — a shipped-but-unregistered hook script and a registration pointing")
    print("at a pruned one are both reported, and the shipped tree stays clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
