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

A registration has two halves, and the guard originally checked one. Which
*event* each script fires on is hand-maintained in all three registries and was
compared by nothing: a payload that binds the session primer to `Stop` and the
pattern check to `SessionStart` registers exactly the right scripts, and both
hooks keep exiting 0 (card
`nothing-checks-which-event-a-hook-is-bound-to-across-the-three-registries`).
The fixture below therefore registers every hook on the event
`GOC_CLAUDE_HOOKS` binds it to; the earlier synthetic `Event{i}` names were the
clearest statement that the event sat outside the contract under test.

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
from goc.install import claude_hook_bindings  # noqa: E402

PRIMER = "deck_session_start.py"
ROUTER = "deck_prompt_router.py"
PATTERN = "pattern_generalization_check.py"

#: A hook template `GOC_CLAUDE_HOOKS` does not know — the shape of a script
#: added to `templates/hooks/` before its event mapping is written.
PROBE = "probe_new_hook.py"
PROBE_EVENT = "PreToolUse"


def _reference_event(name: str) -> str:
    """The event `GOC_CLAUDE_HOOKS` binds `name` to — what a payload must match.

    Read from the live registry rather than restated here: a fixture that
    hard-codes the mapping stops testing the contract the moment the real one
    moves, which is the failure this whole file is about.
    """
    reference, _ = claude_hook_bindings()
    events = reference.get(name)
    return sorted(events)[0] if events else PROBE_EVENT


def _bind(*names: str) -> list[tuple[str, str]]:
    """Register each script on its reference event — the in-sync case."""
    return [(_reference_event(name), name) for name in names]


def _write_registry(hooks_dir: Path, bindings: list[tuple[str, str]]) -> None:
    """Write a Claude-shaped `hooks.json` registering exactly `bindings`."""
    hooks: dict[str, list] = {}
    for event, name in bindings:
        hooks.setdefault(event, []).append({"hooks": [{
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/" + name,
        }]})
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / "hooks.json").write_text(json.dumps({"hooks": hooks}))


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

    def _payloads(self, shipped: list[str], registered: list[tuple[str, str]]) -> None:
        for plugin in engine.PLUGIN_HOOK_REGISTRIES:
            hooks_dir = self.tmp / plugin / "hooks"
            _write_registry(hooks_dir, registered)
            for name in shipped:
                (hooks_dir / name).write_text("#\n")

    def _assert_each_payload_reports(self, errors: list[str], *fragments: str) -> None:
        """Every payload must carry one error containing all of `fragments`."""
        for plugin in engine.PLUGIN_HOOK_REGISTRIES:
            self.assertTrue(
                any(plugin in e and all(f in e for f in fragments) for e in errors),
                msg=f"{plugin}: no error carrying {fragments!r}; got {errors!r}",
            )

    def test_shipped_but_unregistered_script_is_reported(self) -> None:
        """The silent case: the payload carries a hook no command names."""
        self._templates(ROUTER, PROBE)
        self._payloads(shipped=[ROUTER, PROBE], registered=_bind(ROUTER))
        errors = engine.validate_plugin_hook_registration()
        self._assert_each_payload_reports(errors, PROBE, "never invoked")

    def test_registration_without_a_shipped_script_is_reported(self) -> None:
        """The loud case: retiring a template prunes the file, not the entry."""
        self._templates(ROUTER)
        self._payloads(shipped=[ROUTER], registered=_bind(ROUTER, PROBE))
        errors = engine.validate_plugin_hook_registration()
        self._assert_each_payload_reports(errors, PROBE, "does not ship")

    def test_matched_scripts_and_registrations_are_clean(self) -> None:
        self._templates(ROUTER, PROBE)
        self._payloads(shipped=[ROUTER, PROBE], registered=_bind(ROUTER, PROBE))
        self.assertEqual([], engine.validate_plugin_hook_registration())

    def test_swapped_events_are_reported(self) -> None:
        """The case the script-set difference cannot see: right scripts, wrong events.

        The session primer on `Stop` reprints the active-card reminder after
        every turn; the pattern check on `SessionStart` reminds nobody. Both
        exit 0, and the registered script set is exactly correct.
        """
        self._templates(PRIMER, PATTERN)
        self._payloads(
            shipped=[PRIMER, PATTERN],
            registered=[("Stop", PRIMER), ("SessionStart", PATTERN)],
        )
        errors = engine.validate_plugin_hook_registration()
        self._assert_each_payload_reports(
            errors, f"binds {PRIMER} to Stop", "binds it to SessionStart"
        )
        self._assert_each_payload_reports(
            errors, f"binds {PATTERN} to SessionStart", "binds it to Stop"
        )

    def test_event_no_registry_knows_is_reported(self) -> None:
        """A renamed or mistyped event binds the hook to something nothing fires."""
        self._templates(PRIMER)
        self._payloads(shipped=[PRIMER], registered=[("Resume", PRIMER)])
        errors = engine.validate_plugin_hook_registration()
        self._assert_each_payload_reports(
            errors, f"binds {PRIMER} to Resume", "binds it to SessionStart"
        )

    def test_extra_event_on_an_otherwise_correct_binding_is_reported(self) -> None:
        """Keeping the right event and adding a second one is still drift.

        The comparison is over event *sets*, so a payload that also fires the
        primer on `Stop` is caught even though the reference event is present.
        """
        self._templates(PRIMER)
        self._payloads(
            shipped=[PRIMER],
            registered=[("SessionStart", PRIMER), ("Stop", PRIMER)],
        )
        errors = engine.validate_plugin_hook_registration()
        self._assert_each_payload_reports(
            errors, f"binds {PRIMER} to SessionStart, Stop", "binds it to SessionStart"
        )

    def test_script_outside_the_reference_mapping_has_no_expected_event(self) -> None:
        """A template not yet in `GOC_CLAUDE_HOOKS` has no event to be checked against.

        The plugin check stays silent rather than guessing, because the missing
        `GOC_CLAUDE_HOOKS` entry is `validate_hook_registration`'s finding —
        asserted here so "one diagnosis per defect" is tested, not just claimed.
        """
        self._templates(PROBE)
        self._payloads(shipped=[PROBE], registered=[("Stop", PROBE)])
        self.assertEqual([], engine.validate_plugin_hook_registration())
        self.assertTrue(
            any(PROBE in e and "no event entry" in e
                for e in engine.validate_hook_registration()),
            msg="nothing reports a hook template missing from GOC_CLAUDE_HOOKS",
        )

    def test_codex_shell_wrapper_command_counts_as_a_registration(self) -> None:
        """Codex names the script three times inside one `sh -c` command.

        Basename collection has to collapse that to one registration, or every
        Codex hook reads as unregistered the moment the guard turns on.
        """
        self._templates(ROUTER)
        hooks_dir = self.tmp / "codex-plugin" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / ROUTER).write_text("#\n")
        (hooks_dir / "hooks.json").write_text(json.dumps({"hooks": {
            _reference_event(ROUTER): [
                {"hooks": [{"type": "command", "command": (
                    'sh -c \'p="${PLUGIN_ROOT}/hooks/' + ROUTER + '"; '
                    'if [ ! -f "$p" ]; then d="$(dirname "${PLUGIN_ROOT}")"; '
                    'p="$(ls -t "$d"/*/hooks/' + ROUTER + ' 2>/dev/null | head -n 1)"; fi; '
                    'exec python3 "$p"\''
                )}]}
            ]
        }}))
        self.assertEqual([], engine.validate_plugin_hook_registration())

    def test_absent_payload_root_is_inert(self) -> None:
        """Consuming repos have no `claude-plugin/`; the check must not fire."""
        self._templates(ROUTER)
        self.assertEqual([], engine.validate_plugin_hook_registration())

    def test_malformed_registries_are_reported_not_raised(self) -> None:
        """`hooks.json` is authored by hand, so every level can be the wrong shape."""
        self._templates(ROUTER)
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

    def test_shipped_tree_registers_every_hook_template_on_its_event(self) -> None:
        """The live payloads, not a fixture — this is what CI is protecting.

        `setUp` already registered the cleanup that restores both globals, so
        pointing them back at the repo here is safe.
        """
        engine.PACKAGE_DIR, engine.REPO_ROOT = ROOT / "goc", ROOT
        self.assertEqual(
            [],
            engine.validate_plugin_hook_registration(),
            msg="a hook template is unregistered in a plugin payload, a payload "
                "registration points at a script that is not shipped, or a "
                "payload binds a hook to a different event than GOC_CLAUDE_HOOKS",
        )


if __name__ == "__main__":
    unittest.main()
