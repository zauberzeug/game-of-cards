"""Reproduce: Codex plugin upgrade deletes the versioned cache dir that a
running session's hooks still point at.

Codex materializes the plugin at
`~/.codex/plugins/cache/game-of-cards/game-of-cards/<version>/` and expands
`${PLUGIN_ROOT}` in hooks.json commands when the session starts. `codex
plugin marketplace upgrade` replaces the version dir (0.0.26 -> 0.0.27), so
every hook fire in an already-running session execs a deleted script:

    python3 .../0.0.26/hooks/deck_prompt_router.py: [Errno 2] No such file

This script simulates that exact incident against the *committed*
codex-plugin/hooks/hooks.json: a cache with only 0.0.27 on disk while the
session's PLUGIN_ROOT still says 0.0.26. It exercises both plausible
substitution models (textual template replacement, and env-var expansion by
the shell). Exit 0 = every hook command survives the upgrade; exit 1 = the
defect fires.
"""

import json
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


REPO = _repo_root()
HOOK_SCRIPTS = (
    "deck_session_start.py",
    "deck_prompt_router.py",
    "pattern_generalization_check.py",
)


def hook_commands() -> dict:
    hooks_json = json.loads((REPO / "codex-plugin/hooks/hooks.json").read_text())
    commands = {}
    for event, groups in hooks_json["hooks"].items():
        for group in groups:
            for hook in group["hooks"]:
                commands[event] = hook["command"]
    return commands


def run(command: str, plugin_root: str, textual: bool) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin"}
    if textual:
        command = command.replace("${PLUGIN_ROOT}", plugin_root)
    else:
        env["PLUGIN_ROOT"] = plugin_root
    return subprocess.run(
        command, shell=True, env=env, input="{}",
        capture_output=True, text=True, timeout=30,
    )


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp) / "plugins/cache/game-of-cards/game-of-cards"
        new_root = cache / "0.0.27"
        (new_root / "hooks").mkdir(parents=True)
        for name in HOOK_SCRIPTS:
            # Stub that names the file it ran from, so the output proves
            # which install the command resolved.
            (new_root / "hooks" / name).write_text("print(__file__)\n")
        stale_root = str(cache / "0.0.26")  # deleted by the upgrade

        for event, command in hook_commands().items():
            for model in ("textual", "env"):
                result = run(command, stale_root, textual=(model == "textual"))
                ok = result.returncode == 0 and "0.0.27" in result.stdout
                status = "PASS" if ok else "FAIL"
                if not ok:
                    failures += 1
                detail = result.stdout.strip() or result.stderr.strip()
                print(f"{status}  {event} [{model} substitution]: {detail}")

    if failures:
        print(f"\n{failures} hook invocation(s) still break after an upgrade "
              "deletes the session's PLUGIN_ROOT.")
        return 1
    print("\nAll hook commands fall back to the surviving install — "
          "running sessions keep working across upgrades.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
