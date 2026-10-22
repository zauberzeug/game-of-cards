#!/usr/bin/env python3
"""Reproduce: `goc validate` breaks in a consuming repo that keeps its own plugin.

`validate_plugin_mirror_parity` and `validate_plugin_hook_registration` were
gated on a payload-named folder (`claude-plugin/`, `codex-plugin/`) existing at
the project root, which a consuming repo may legitimately have for its own
Claude Code or Codex plugin. This script runs the card's falsification recipe
in a scratch repo, with the engine from this checkout:

1. `goc install --agents claude`, then `goc validate` (setup; must exit 0).
2. Add only `claude-plugin/.claude-plugin/plugin.json`; run `goc validate`.
3. Replace it with only `codex-plugin/skills/foo/SKILL.md`; run `goc validate`.
4. Control: only `openclaw-plugin/openclaw.plugin.json` (never crashed).
5. Recipe step 4: a consumer `claude-plugin/hooks/hooks.json` registering the
   consumer's own hook (which imports a helper module beside it) and a script
   kept outside `hooks/`. Runs `goc validate`, and also calls
   `validate_plugin_hook_registration()` in a fresh process, so that check's
   verdict is visible even while the mirror check crashes first.

Exit 1 while any scenario makes `goc validate` exit non-zero, print a
traceback, or report a plugin-mirror / hook-registration error against the
consumer's own files. Exit 0 once every scenario is clean. If scenarios 2 and 3
had exited 0 before the fix, the hypothesis would have been disproved.
"""

from __future__ import annotations

import json
import os
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
ENV = dict(os.environ, PYTHONPATH=str(ROOT))
PAYLOADS = ("claude-plugin", "codex-plugin", "openclaw-plugin")
CONSUMER_ERRORS = ("Traceback", "plugin mirror", "hook registration")


def goc(cwd: Path, *args: str) -> tuple[int, str]:
    """Run the engine as a consumer would: fresh process, `cwd` as the repo."""
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(cwd), env=ENV, capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def hook_check(cwd: Path) -> str:
    """`validate_plugin_hook_registration()` alone, as the engine sees `cwd`."""
    proc = subprocess.run(
        [sys.executable, "-c",
         "from goc import engine\n"
         "for e in engine.validate_plugin_hook_registration(): print(e)"],
        cwd=str(cwd), env=ENV, capture_output=True, text=True,
    )
    return (proc.stdout + proc.stderr).strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def reset(repo: Path) -> None:
    for name in PAYLOADS:
        shutil.rmtree(repo / name, ignore_errors=True)


def consumer_hook_plugin(repo: Path) -> None:
    """A consumer's own plugin: one hook plus a helper it imports, and a
    SessionStart command that runs a script kept outside `hooks/`."""
    write(repo / "claude-plugin" / ".claude-plugin" / "plugin.json",
          json.dumps({"name": "my-plugin", "version": "1.0.0"}))
    write(repo / "claude-plugin" / "hooks" / "format_on_save.py", "import _util\n")
    write(repo / "claude-plugin" / "hooks" / "_util.py", "X = 1\n")
    write(repo / "claude-plugin" / "scripts" / "warm_cache.py", "pass\n")
    write(repo / "claude-plugin" / "hooks" / "hooks.json", json.dumps({"hooks": {
        "PostToolUse": [{"matcher": "Edit|Write", "hooks": [{
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/format_on_save.py",
        }]}],
        "SessionStart": [{"hooks": [{
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/warm_cache.py",
        }]}],
    }}))


SCENARIOS = {
    "claude-plugin/.claude-plugin/plugin.json only": lambda repo: write(
        repo / "claude-plugin" / ".claude-plugin" / "plugin.json",
        json.dumps({"name": "my-plugin", "version": "1.0.0"}),
    ),
    "codex-plugin/skills/foo/SKILL.md only": lambda repo: write(
        repo / "codex-plugin" / "skills" / "foo" / "SKILL.md", "x\n",
    ),
    "openclaw-plugin/openclaw.plugin.json only (control)": lambda repo: write(
        repo / "openclaw-plugin" / "openclaw.plugin.json", "{}\n",
    ),
    "claude-plugin with its own hooks.json": consumer_hook_plugin,
}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "consumer"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
        code, out = goc(repo, "install", "--agents", "claude")
        if code != 0:
            raise SystemExit(f"setup failed: goc install exit {code}\n{out}")
        code, out = goc(repo, "validate")
        print(f"[setup] fresh install: goc validate -> exit {code}")
        if code != 0:
            raise SystemExit(f"setup failed: validate is red before any plugin folder\n{out}")

        failures: list[str] = []
        for step, (label, build) in enumerate(SCENARIOS.items(), start=2):
            reset(repo)
            build(repo)
            code, out = goc(repo, "validate")
            flagged = [
                line.strip() for line in out.splitlines()
                if any(marker in line for marker in CONSUMER_ERRORS)
                or line.startswith(("FileNotFoundError", "NotADirectoryError"))
            ]
            clean = code == 0 and not flagged
            print(f"\n[{step}] {label}: goc validate -> exit {code}"
                  + ("" if clean else "  <-- FAIL"))
            for line in flagged:
                print(f"      {line}")
            if not clean:
                failures.append(label)
            if label.startswith("claude-plugin with its own hooks.json"):
                verdict = hook_check(repo)
                print("      validate_plugin_hook_registration() alone -> "
                      + ("[] (silent)" if not verdict else "reports:"))
                for line in verdict.splitlines():
                    print(f"        {line}")
                if verdict:
                    failures.append(f"{label}: hook-registration check")

    print("\n=== verdict ===")
    if failures:
        print("defect present: goc validate is not inert in a consuming repo that "
              "keeps its own plugin under a payload folder name:")
        for label in failures:
            print(f"  - {label}")
        return 1
    print("clean: both plugin checks stay inert in a consuming repo with its own "
          "plugin folder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
