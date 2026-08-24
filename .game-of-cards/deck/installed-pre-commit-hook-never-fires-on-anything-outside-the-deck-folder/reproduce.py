#!/usr/bin/env python3
"""Reproduce: the pre-commit hook `goc install` writes only fires on deck edits.

`goc/install.py`'s `PRE_COMMIT_HOOK` declares `pass_filenames: false` — the hook
re-checks the whole repository and ignores which files changed — but also
`files: ^\\.game-of-cards/deck/.*$`. pre-commit skips a hook whose filtered file
list comes out empty (`always_run` defaults to false), so in a consuming repo the
gate is silent for every path outside the deck folder, including the two skill
trees `goc validate` itself walks in `skills_source: vendored` mode.

This script is static and modifies nothing: it reads the shipped hook block out
of `goc/install.py`, then asks — using pre-commit's own rule — whether a commit
touching only each surface `goc validate` reads would trigger it.

Exit 1 while any surface the hook's own check reads cannot trigger it.
Exit 0 once every surface does (e.g. the block gains `always_run: true`).
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
INSTALL_PY = ROOT / "goc" / "install.py"

# Surfaces that change what `goc validate` reports in a consuming repo, with the
# reason each one does. Only the first is inside the shipped `files:` pattern.
# Deliberately NOT listed: the consumer's `.claude/hooks/` and the `hooks` block
# of `.claude/settings.json`. `validate_hook_registration` checks the *package's*
# templates against `GOC_CLAUDE_HOOKS`; it never reads the consumer's copies, so
# a stale hook script there is not something this gate would have caught.
VALIDATED_SURFACES = [
    (".game-of-cards/deck/some-card/README.md", "validate_card / validate_deck_directories"),
    (".claude/skills/deck/SKILL.md", "validate_skill_dir_parity, in skills_source: vendored"),
    (".codex/skills/deck/SKILL.md", "validate_skill_dir_parity, in skills_source: vendored"),
    (".game-of-cards/config.yaml", "sets skills_source -> whether the parity check runs at all"),
    (".claude/settings.json", "effective_skills_source reads it when skills_source is auto/unset"),
]

_BLOCK_RE = re.compile(r'^PRE_COMMIT_HOOK\s*=\s*"""\\?\n(.*?)^"""', re.MULTILINE | re.DOTALL)
_FILES_RE = re.compile(r"^\s*files:\s*(\S.*?)\s*$", re.MULTILINE)
_PASS_FILENAMES_RE = re.compile(r"^\s*pass_filenames:\s*(\S+)\s*$", re.MULTILINE)
_ALWAYS_RUN_RE = re.compile(r"^\s*always_run:\s*(\S+)\s*$", re.MULTILINE)
_TRUTHY = frozenset(("true", "yes", "on"))


def shipped_hook() -> dict:
    """Parse the `PRE_COMMIT_HOOK` literal into {files, pass_filenames, always_run}."""
    m = _BLOCK_RE.search(INSTALL_PY.read_text(encoding="utf-8"))
    if m is None:
        raise SystemExit(f"could not find PRE_COMMIT_HOOK literal in {INSTALL_PY}")
    block = m.group(1)
    files = _FILES_RE.search(block)
    pass_filenames = _PASS_FILENAMES_RE.search(block)
    always_run = _ALWAYS_RUN_RE.search(block)
    return {
        "block": block,
        # The literal is a Python string with escaped backslashes; unescape so the
        # pattern is the one pre-commit would actually compile.
        "files": files.group(1).replace("\\\\", "\\") if files else None,
        "pass_filenames": pass_filenames.group(1).lower() in _TRUTHY if pass_filenames else True,
        "always_run": always_run.group(1).lower() in _TRUTHY if always_run else False,
    }


def triggers(hook: dict, path: str) -> bool:
    """pre-commit's rule: always_run forces the run, an absent filter matches all."""
    if hook["always_run"]:
        return True
    if hook["files"] is None:
        return True
    return re.search(hook["files"], path) is not None


def main() -> int:
    hook = shipped_hook()
    print(f"PRE_COMMIT_HOOK as shipped by {INSTALL_PY.relative_to(ROOT)}:")
    print(hook["block"].rstrip())
    print()
    print(
        f"  pass_filenames={hook['pass_filenames']}  "
        f"always_run={hook['always_run']}  files={hook['files']!r}"
    )
    print()

    if hook["pass_filenames"]:
        print("SKIP: the shipped hook is not a whole-tree check; this defect does not apply.")
        return 0

    unreachable = []
    for path, reader in VALIDATED_SURFACES:
        fires = triggers(hook, path)
        print(f"  {path:<44} {'fires' if fires else 'SKIPPED':<8} ({reader})")
        if not fires:
            unreachable.append((path, reader))
    print()

    if unreachable:
        print(
            f"FAIL: the hook is pass_filenames: false (it checks the whole repo) but "
            f"{len(unreachable)} surface(s) its own check reads cannot trigger it:"
        )
        for path, reader in unreachable:
            print(f"  - {path}  ({reader})")
        return 1

    print("OK: every surface goc validate reads can trigger the shipped hook.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
