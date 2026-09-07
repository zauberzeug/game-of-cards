"""Regression guard for `engine.validate_plugin_hook_registration`.

`validate_hook_registration` enforces script-to-registration parity for
`GOC_CLAUDE_HOOKS`, the registry the vendored `--local-skills` install writes
into `.claude/settings.json`. The DEFAULT install writes `skills_source:
plugin`, where the registry is the payload's own `hooks.json` — hand-maintained,
preserved by `scripts/sync_plugin_assets.py` and excluded from
`validate_plugin_mirror_parity`'s byte comparison. Until the validator under
test existed, no mechanism compared it to `goc/templates/hooks/*.py`, so a hook
template could ship into both payloads as a file no host ever invokes with every
tripwire in the repo green (card
`plugin-payload-hooks-json-never-registers-a-newly-added-hook-script`).

Per `static-source-guards-never-prove-they-can-catch-an-offender`, a guard must
demonstrate it catches an offender rather than merely reporting a clean tree:
every offender case below is driven, not asserted-clean.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402

PROBE = "probe_new_hook.py"
SHIPPED = "deck_prompt_router.py"


def _write_registry(hooks_dir: Path, scripts: list[str]) -> None:
    """Write a Claude-shaped `hooks.json` registering exactly `scripts`."""
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / "hooks.json").write_text(json.dumps({
        "hooks": {
            f"Event{i}": [{"hooks": [{
                "type": "command",
                "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/" + name,
            }]}]
            for i, name in enumerate(scripts)
        }
    }))


class PluginHookRegistrationTest(unittest.TestCase):
    """Drives the validator against a synthetic tree.

    Only the shapes the validator reads are built — the template hook dir and
    the two payload hook dirs — so a case states its own drift in full.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "goc" / "templates" / "hooks").mkdir(parents=True)
        self._patch()

    def _patch(self) -> None:
        package, repo = engine.PACKAGE_DIR, engine.REPO_ROOT
        engine.PACKAGE_DIR, engine.REPO_ROOT = self.tmp / "goc", self.tmp
        self.addCleanup(setattr, engine, "PACKAGE_DIR", package)
        self.addCleanup(setattr, engine, "REPO_ROOT", repo)

    def _templates(self, *names: str) -> None:
        for name in names:
            (self.tmp / "goc" / "templates" / "hooks" / name).write_text("#\n")

    def _payloads(self, shipped: list[str], registered: list[str]) -> None:
        for plugin in engine.PLUGIN_HOOK_REGISTRIES:
            hooks_dir = self.tmp / plugin / "hooks"
            _write_registry(hooks_dir, registered)
            for name in shipped:
                (hooks_dir / name).write_text("#\n")

    def test_shipped_but_unregistered_script_is_reported(self) -> None:
        """The silent case: the payload carries a hook no command names."""
        self._templates(SHIPPED, PROBE)
        self._payloads(shipped=[SHIPPED, PROBE], registered=[SHIPPED])
        errors = engine.validate_plugin_hook_registration()
        for plugin in engine.PLUGIN_HOOK_REGISTRIES:
            self.assertTrue(
                any(PROBE in e and plugin in e and "never invoked" in e for e in errors),
                msg=f"{plugin} ships an unregistered {PROBE} unreported; got {errors!r}",
            )

    def test_registration_without_a_shipped_script_is_reported(self) -> None:
        """The loud case: retiring a template prunes the file, not the entry."""
        self._templates(SHIPPED)
        self._payloads(shipped=[SHIPPED], registered=[SHIPPED, PROBE])
        errors = engine.validate_plugin_hook_registration()
        for plugin in engine.PLUGIN_HOOK_REGISTRIES:
            self.assertTrue(
                any(PROBE in e and plugin in e and "does not ship" in e for e in errors),
                msg=f"{plugin} registers a pruned {PROBE} unreported; got {errors!r}",
            )

    def test_matched_scripts_and_registrations_are_clean(self) -> None:
        self._templates(SHIPPED, PROBE)
        self._payloads(shipped=[SHIPPED, PROBE], registered=[SHIPPED, PROBE])
        self.assertEqual([], engine.validate_plugin_hook_registration())

    def test_codex_shell_wrapper_command_counts_as_a_registration(self) -> None:
        """Codex names the script three times inside one `sh -c` command.

        Basename collection has to collapse that to one registration, or every
        Codex hook reads as unregistered the moment the guard turns on.
        """
        self._templates(SHIPPED)
        hooks_dir = self.tmp / "codex-plugin" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / SHIPPED).write_text("#\n")
        (hooks_dir / "hooks.json").write_text(json.dumps({"hooks": {"SessionStart": [
            {"hooks": [{"type": "command", "command": (
                'sh -c \'p="${PLUGIN_ROOT}/hooks/' + SHIPPED + '"; '
                'if [ ! -f "$p" ]; then d="$(dirname "${PLUGIN_ROOT}")"; '
                'p="$(ls -t "$d"/*/hooks/' + SHIPPED + ' 2>/dev/null | head -n 1)"; fi; '
                'exec python3 "$p"\''
            )}]}
        ]}}))
        self.assertEqual([], engine.validate_plugin_hook_registration())

    def test_absent_payload_root_is_inert(self) -> None:
        """Consuming repos have no `claude-plugin/`; the check must not fire."""
        self._templates(SHIPPED)
        self.assertEqual([], engine.validate_plugin_hook_registration())

    def test_malformed_registries_are_reported_not_raised(self) -> None:
        """`hooks.json` is authored by hand, so every level can be the wrong shape."""
        self._templates(SHIPPED)
        cases = {
            "not json at all": "{oops",
            "root is a list": "[]",
            "hooks is a list": '{"hooks": []}',
            "event maps to a string": '{"hooks": {"SessionStart": "nope"}}',
            "group is not a mapping": '{"hooks": {"SessionStart": ["nope"]}}',
            "group has no hooks list": '{"hooks": {"SessionStart": [{}]}}',
            "entry is not a mapping": '{"hooks": {"SessionStart": [{"hooks": [1]}]}}',
            "command is not a string": '{"hooks": {"SessionStart": [{"hooks": [{"command": 7}]}]}}',
        }
        hooks_dir = self.tmp / "claude-plugin" / "hooks"
        hooks_dir.mkdir(parents=True)
        for label, payload in cases.items():
            with self.subTest(shape=label):
                (hooks_dir / "hooks.json").write_text(payload)
                errors = engine.validate_plugin_hook_registration()
                self.assertTrue(
                    any("hook registration" in e for e in errors),
                    msg=f"{label!r} produced no diagnostic; got {errors!r}",
                )

    def test_shipped_tree_registers_every_hook_template(self) -> None:
        """The live payloads, not a fixture — this is what CI is protecting.

        `setUp` already registered the cleanup that restores both globals, so
        pointing them back at the repo here is safe.
        """
        engine.PACKAGE_DIR, engine.REPO_ROOT = ROOT / "goc", ROOT
        self.assertEqual(
            [],
            engine.validate_plugin_hook_registration(),
            msg="a hook template is unregistered in a plugin payload, or a "
                "payload registration points at a script that is not shipped",
        )


if __name__ == "__main__":
    unittest.main()
