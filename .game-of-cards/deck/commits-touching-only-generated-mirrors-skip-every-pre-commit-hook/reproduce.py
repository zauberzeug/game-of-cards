#!/usr/bin/env python3
"""Reproduce: a commit that edits only generated mirrors skips every pre-commit hook.

Every hook in `.pre-commit-config.yaml` is `pass_filenames: false` — each one
re-checks the whole tree regardless of what changed. But each is also gated on a
`files:` regex, and pre-commit skips a hook whose filtered file list is empty
(unless `always_run: true`). Several trees that the hooks *do* check are absent
from every filter, so a change confined to them fires nothing.

This script is static: it reads the hook filters out of `.pre-commit-config.yaml`
and asks, for each mirror path that `goc validate` / `sync_plugin_assets.py
--check` are known to guard, whether ANY hook would be triggered by a commit
touching only that path. No pre-commit installation is required, and no files are
modified.

Exit 0 once every guarded path triggers at least one hook (either because the
filters were widened or because the hooks became `always_run: true`).
Exit 1 while any guarded path is invisible to every hook.
"""

from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
CONFIG = ROOT / ".pre-commit-config.yaml"

# Paths each hook's check actually reads, but which no `files:` filter names.
# `goc validate` runs validate_plugin_mirror_parity over the three plugin
# payloads (claude-plugin/, codex-plugin/, openclaw-plugin/); the sync script's
# --check mode compares those three plus this repo's dogfood self-host copies
# under .claude/skills/, .claude/hooks/ and .codex/skills/.
GUARDED_PATHS = [
    "codex-plugin/goc/engine.py",
    "codex-plugin/skills/deck/SKILL.md",
    "openclaw-plugin/goc/engine.py",
    ".claude/skills/deck/SKILL.md",
    ".codex/skills/deck/SKILL.md",
    ".claude/hooks/deck_session_start.py",
]

_ID_RE = re.compile(r"^\s*-\s+id:\s*(\S+)\s*$")
_FILES_RE = re.compile(r"^\s*files:\s*(\S.*?)\s*$")
_ALWAYS_RUN_RE = re.compile(r"^\s*always_run:\s*(\S+)\s*$")


def parse_hooks(text: str) -> list[dict]:
    """Return [{id, files, always_run}] in file order.

    Deliberately a line scanner rather than a YAML load: the repo ships no
    runtime YAML dependency, and the two keys this needs are always plain
    scalars on their own line in this config.
    """
    hooks: list[dict] = []
    for line in text.splitlines():
        m = _ID_RE.match(line)
        if m:
            hooks.append({"id": m.group(1), "files": None, "always_run": False})
            continue
        if not hooks:
            continue
        m = _FILES_RE.match(line)
        if m:
            hooks[-1]["files"] = m.group(1)
            continue
        m = _ALWAYS_RUN_RE.match(line)
        if m:
            hooks[-1]["always_run"] = m.group(1).lower() in ("true", "yes", "on")
    return hooks


def triggers(hook: dict, path: str) -> bool:
    """Would a commit touching only `path` run this hook?

    Mirrors pre-commit's own rule: `always_run` forces the hook to run; a hook
    with no `files:` filter matches everything; otherwise the filter is a
    `re.search` against each candidate filename.
    """
    if hook["always_run"]:
        return True
    pattern = hook["files"]
    if pattern is None:
        return True
    return re.search(pattern, path) is not None


def main() -> int:
    text = CONFIG.read_text(encoding="utf-8")
    hooks = parse_hooks(text)

    print(f"hooks declared in {CONFIG.relative_to(ROOT)}:")
    for h in hooks:
        shown = h["files"] if h["files"] is not None else "(no filter)"
        print(f"  {h['id']:<24} always_run={str(h['always_run']):<5} files={shown}")
    print()

    uncovered = []
    for path in GUARDED_PATHS:
        firing = [h["id"] for h in hooks if triggers(h, path)]
        status = ", ".join(firing) if firing else "NOTHING FIRES"
        print(f"  {path:<40} -> {status}")
        if not firing:
            uncovered.append(path)
    print()

    if uncovered:
        print(
            f"FAIL: {len(uncovered)} guarded path(s) trigger no pre-commit hook, "
            "so a commit confined to them passes locally and fails CI:"
        )
        for path in uncovered:
            print(f"  - {path}")
        return 1

    print("OK: every guarded path triggers at least one pre-commit hook.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
