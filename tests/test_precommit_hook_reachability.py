"""Every whole-tree pre-commit hook must be reachable from any tree it checks.

Repo-local guard for `.pre-commit-config.yaml`. All four hooks declared there
are `pass_filenames: false` — each re-checks the entire repository and ignores
which files changed. Their `files:` key is therefore a *trigger*, not a scope,
and pre-commit skips a hook whose filtered file list comes out empty (`always_run`
defaults to false, and the run is reported as `(no files to check) Skipped`).

That made the local hook set narrower than the CI check set: `goc validate`
compares three plugin payloads and `scripts/sync_plugin_assets.py --check`
compares those three plus this repo's dogfood self-host copies, but only
`claude-plugin/` ever appeared in a `files:` pattern. A commit confined to any
of the other five mirrors fired nothing locally and failed CI on the next push.
See `commits-touching-only-generated-mirrors-skip-every-pre-commit-hook`.

The invariant pinned here is the general one, not the six paths that happened to
be broken: a `pass_filenames: false` hook must be triggered by a commit touching
*any* path, because that is the set of commits under which its verdict can
change. `always_run: true` is the only form that satisfies it without an
enumeration that drifts as the checks learn new surfaces.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".pre-commit-config.yaml"

# Representative paths from every tree a hook's check reads. `goc validate`
# walks the three plugin payloads via `validate_plugin_mirror_parity`; the sync
# script's `--check` mode compares those three plus `.claude/skills/`,
# `.claude/hooks/` and `.codex/skills/`. The deck path is the one surface the
# original filters did cover, kept here so the test would notice a fix that
# traded one gap for another.
GUARDED_PATHS = (
    "goc/engine.py",
    "goc/templates/skills/deck/SKILL.md",
    "claude-plugin/goc/engine.py",
    "codex-plugin/goc/engine.py",
    "codex-plugin/skills/deck/SKILL.md",
    "openclaw-plugin/goc/engine.py",
    ".claude/skills/deck/SKILL.md",
    ".claude/hooks/deck_session_start.py",
    ".codex/skills/deck/SKILL.md",
    ".game-of-cards/deck/some-card/README.md",
)

# Paths that belong to no check but are ordinary repo content: a hook that runs
# on these is not a bug, it is what `always_run: true` means. Listed so the
# test states plainly that unrelated commits also trigger the whole-tree hooks.
UNRELATED_PATHS = (
    "README.md",
    ".github/workflows/ci.yml",
    "tests/test_precommit_hook_reachability.py",
)

_ID_RE = re.compile(r"^\s*-\s+id:\s*(\S+)\s*$")
_FILES_RE = re.compile(r"^\s*files:\s*(\S.*?)\s*$")
_PASS_FILENAMES_RE = re.compile(r"^\s*pass_filenames:\s*(\S+)\s*$")
_ALWAYS_RUN_RE = re.compile(r"^\s*always_run:\s*(\S+)\s*$")
_TRUTHY = frozenset(("true", "yes", "on"))


def parse_hooks(text: str) -> list[dict]:
    """Return `[{id, files, pass_filenames, always_run}]` in declaration order.

    A line scanner rather than a YAML load on purpose: the repo ships no runtime
    YAML dependency (`drop-third-party-runtime-dependencies-from-goc`), and the
    three keys this reads are always plain scalars on their own line.
    """
    hooks: list[dict] = []
    for line in text.splitlines():
        m = _ID_RE.match(line)
        if m:
            hooks.append(
                {
                    "id": m.group(1),
                    "files": None,
                    "pass_filenames": True,
                    "always_run": False,
                }
            )
            continue
        if not hooks:
            continue
        m = _FILES_RE.match(line)
        if m:
            hooks[-1]["files"] = m.group(1)
            continue
        m = _PASS_FILENAMES_RE.match(line)
        if m:
            hooks[-1]["pass_filenames"] = m.group(1).lower() in _TRUTHY
            continue
        m = _ALWAYS_RUN_RE.match(line)
        if m:
            hooks[-1]["always_run"] = m.group(1).lower() in _TRUTHY
    return hooks


def triggers(hook: dict, path: str) -> bool:
    """Would a commit touching only `path` run this hook?

    Mirrors pre-commit's own rule: `always_run` forces the run; a hook with no
    `files:` filter matches every path; otherwise the filter is `re.search`ed
    against each candidate filename.
    """
    if hook["always_run"]:
        return True
    if hook["files"] is None:
        return True
    return re.search(hook["files"], path) is not None


class PreCommitHookReachability(unittest.TestCase):
    def setUp(self) -> None:
        self.hooks = parse_hooks(CONFIG.read_text(encoding="utf-8"))

    def test_config_declares_the_expected_hooks(self) -> None:
        """Guard the parser: a rename or reshape must not silently empty this test."""
        self.assertEqual(
            [h["id"] for h in self.hooks],
            [
                "sync-plugin-assets",
                "goc-validate",
                "card-language",
                "card-frontmatter-yaml",
            ],
        )

    def test_whole_tree_hooks_run_on_every_commit(self) -> None:
        """A `pass_filenames: false` hook checks the whole tree, so nothing may
        filter it out — including commits confined to a generated mirror."""
        whole_tree = [h for h in self.hooks if not h["pass_filenames"]]
        self.assertTrue(whole_tree, "expected at least one pass_filenames: false hook")
        for hook in whole_tree:
            for path in GUARDED_PATHS + UNRELATED_PATHS:
                with self.subTest(hook=hook["id"], path=path):
                    self.assertTrue(
                        triggers(hook, path),
                        f"hook {hook['id']!r} does not fire for a commit touching only "
                        f"{path!r} (files={hook['files']!r}, always_run="
                        f"{hook['always_run']!r}); pre-commit would report "
                        f"'(no files to check) Skipped' while CI still checks it",
                    )

    def test_every_guarded_mirror_triggers_some_hook(self) -> None:
        """The card's own framing: no tree a check reads may be invisible to all
        four hooks at once."""
        for path in GUARDED_PATHS:
            with self.subTest(path=path):
                firing = [h["id"] for h in self.hooks if triggers(h, path)]
                self.assertTrue(
                    firing,
                    f"a commit touching only {path!r} triggers no pre-commit hook, "
                    "so it lands clean locally and fails CI",
                )


if __name__ == "__main__":
    unittest.main()
