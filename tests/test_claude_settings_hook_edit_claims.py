"""Regression guard: AGENTS.md must say what goc does with a hand edit to the goc-owned hook entries.

The AGENTS.md paragraph that names `.claude/settings.json` the hook-registration
manifest said the goc-owned `hooks` entries are changed in `goc/install.py`
"and `goc validate` enforces the parity". No validate step compares those
entries with `GOC_CLAUDE_HOOKS`, so a consumer's dropped or repointed
registration passes it
(`agents-md-says-goc-validate-checks-hook-entries-in-claude-settings`). The
clause came from an earlier repair of the same paragraph, whose guard
(`ClaudeSettingsOwnershipAccuracyTest`) pinned the names that repair added and
nothing else it asserted.

These tests make that hand edit in a scratch `--local-skills` install, run
`goc validate` and a same-version `goc upgrade`, and check every clause the
paragraph now states about them against what happened. Every check runs both
ways, so it fails when the engine moves as well as when the page does:

- the paragraph says the edit passes `goc validate` exactly while it does, and
  credits `goc validate` with catching it only while it does;
- it says `goc upgrade` re-adds the missing entries exactly while it does;
- it says the repointed entry stays behind, and links the open card that tracks
  that, exactly while the entry survives the upgrade — so whoever lands that
  card's fix has to update this page.

Each check is fed the pre-fix wording verbatim, and the current wording with
every observation flipped, to prove it fires.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc.install import GOC_CLAUDE_HOOKS  # noqa: E402

DOC = ROOT / "AGENTS.md"
PARAGRAPH_ANCHOR = "`.claude/settings.json` is the"
STALE_ENTRY_CARD = "goc-upgrade-leaves-stale-prior-version-hook-registrations-in-claude-settings"

# Any two goc-owned registrations will do; take them from the registry so a
# renamed event cannot leave the fixture editing an entry that is not there.
REPOINTED_EVENT, DROPPED_EVENT = list(GOC_CLAUDE_HOOKS)[:2]

PRE_FIX_SENTENCE = (
    "So its ownership is shared — the `hooks` entries whose command matches"
    " `GOC_CLAUDE_HOOKS` are goc-owned (change them in `goc/install.py`, not"
    " in `.claude/settings.json`, and `goc validate` enforces the parity);"
    " any other key the repo adds is yours."
)

_PASSES_VALIDATE = re.compile(r"passes `goc validate`")
_CREDITS_VALIDATE = re.compile(r"`goc validate` (?:enforces|catches|rejects|flags|reports)")
_UPGRADE_READDS = re.compile(r"`goc upgrade` re-adds")
_STAYS_BEHIND = re.compile(r"stays behind")

_CHECKS = ("validate", "upgrade", "repointed")


@dataclasses.dataclass(frozen=True)
class Observations:
    validate_catches_edit: bool
    upgrade_restores_entries: bool
    repointed_entry_survives: bool


# What the engine did when the card was filed: the pre-fix sentence contradicts it.
FILED = Observations(
    validate_catches_edit=False,
    upgrade_restores_entries=True,
    repointed_entry_survives=True,
)


def _env(home: Path) -> dict[str, str]:
    drop = {"CLAUDECODE", "CLAUDE_CODE", "CLAUDE_PROJECT_DIR", "CLAUDE_PLUGIN_ROOT", "GOC_WORKER", "GOC_WORKTREE_DECK"}
    env = {k: v for k, v in os.environ.items() if k not in drop and not k.startswith("GIT_")}
    env["PYTHONPATH"] = str(ROOT)
    # An empty home: no enabled plugin and no plugin cache can reach the run.
    env["HOME"] = str(home)
    return env


def _goc(repo: Path, home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=repo, env=_env(home), capture_output=True, text=True, check=False,
    )


def _commands(repo: Path) -> dict[str, list[str]]:
    settings = json.loads((repo / ".claude" / "settings.json").read_text())
    return {
        event: [h.get("command") for group in groups for h in group.get("hooks", [])]
        for event, groups in settings.get("hooks", {}).items()
    }


def _ran(result: subprocess.CompletedProcess[str], what: str) -> None:
    """A setup step must succeed, or the observations mean nothing."""
    if result.returncode != 0:
        raise AssertionError(f"{what} failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}")


def observe(tmp: Path) -> Observations:
    repo, home = tmp / "consumer", tmp / "home"
    repo.mkdir()
    home.mkdir()
    _ran(_goc(repo, home, "install", "--agents", "claude", "--local-skills"), "goc install --local-skills")
    _ran(_goc(repo, home, "validate"), "goc validate on the fresh install")

    path = repo / ".claude" / "settings.json"
    settings = json.loads(path.read_text())
    del settings["hooks"][DROPPED_EVENT]
    repointed = re.sub(r"([\w.-]+)\.py\b", r"\1_renamed.py", GOC_CLAUDE_HOOKS[REPOINTED_EVENT])
    for group in settings["hooks"][REPOINTED_EVENT]:
        for hook in group["hooks"]:
            if hook.get("command") == GOC_CLAUDE_HOOKS[REPOINTED_EVENT]:
                hook["command"] = repointed
    path.write_text(json.dumps(settings, indent=2) + "\n")

    edited = _goc(repo, home, "validate")
    _ran(_goc(repo, home, "upgrade"), "same-version goc upgrade")
    after = _commands(repo)
    return Observations(
        validate_catches_edit=edited.returncode != 0,
        upgrade_restores_entries=all(cmd in after.get(event, []) for event, cmd in GOC_CLAUDE_HOOKS.items()),
        repointed_entry_survives=repointed in after.get(REPOINTED_EVENT, []),
    )


def settings_paragraph(text: str) -> str:
    """The `.claude/settings.json` ownership paragraph, unwrapped."""
    for para in re.split(r"\n\s*\n", text):
        flat = re.sub(r"\s+", " ", para).strip()
        if PARAGRAPH_ANCHOR in flat:
            return flat
    raise AssertionError(f"AGENTS.md has no paragraph containing {PARAGRAPH_ANCHOR!r}")


def problems(paragraph: str, obs: Observations) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    says_passes = bool(_PASSES_VALIDATE.search(paragraph))
    if obs.validate_catches_edit and says_passes:
        found.append(("validate", "says the hand edit passes `goc validate`, but validate now rejects it"))
    if not obs.validate_catches_edit and not says_passes:
        found.append(("validate", "`goc validate` exits 0 on the hand edit; the paragraph must say it passes"))
    if not obs.validate_catches_edit and _CREDITS_VALIDATE.search(paragraph):
        found.append(("validate", "credits `goc validate` with catching the hand edit, but it exits 0"))
    if bool(_UPGRADE_READDS.search(paragraph)) != obs.upgrade_restores_entries:
        found.append(("upgrade", (
            "a same-version `goc upgrade` re-adds the missing entries; the paragraph must say so"
            if obs.upgrade_restores_entries
            else "says `goc upgrade` re-adds the missing entries, but a same-version upgrade no longer does"
        )))
    says_stays = bool(_STAYS_BEHIND.search(paragraph))
    links = STALE_ENTRY_CARD in paragraph
    if obs.repointed_entry_survives and not (says_stays and links):
        found.append(("repointed", f"the repointed entry survives the upgrade; say it stays behind and link {STALE_ENTRY_CARD}"))
    if not obs.repointed_entry_survives and (says_stays or links):
        found.append(("repointed", f"the upgrade now removes the repointed entry; drop the stays-behind clause and the {STALE_ENTRY_CARD} link"))
    return found


def _flipped(obs: Observations) -> Observations:
    return Observations(
        validate_catches_edit=not obs.validate_catches_edit,
        upgrade_restores_entries=not obs.upgrade_restores_entries,
        repointed_entry_survives=not obs.repointed_entry_survives,
    )


class ClaudeSettingsHookEditClaimsTest(unittest.TestCase):
    observed: Observations

    @classmethod
    def setUpClass(cls) -> None:
        with tempfile.TemporaryDirectory(prefix="goc-settings-edit-") as tmp:
            cls.observed = observe(Path(tmp))

    def test_paragraph_matches_what_goc_does_with_the_edit(self) -> None:
        found = problems(settings_paragraph(DOC.read_text()), self.observed)
        self.assertEqual(
            found, [],
            f"AGENTS.md's `.claude/settings.json` paragraph contradicts what goc does with a hand"
            f" edit to the goc-owned hook entries (observed {self.observed}):\n"
            + "\n".join(f"  [{check}] {msg}" for check, msg in found),
        )

    def test_pre_fix_wording_fires_every_check(self) -> None:
        fired = {check for check, _msg in problems(PRE_FIX_SENTENCE, FILED)}
        self.assertEqual(fired, set(_CHECKS))

    def test_current_wording_fires_every_check_once_the_engine_flips(self) -> None:
        # E.g. once a validate check reads the consumer's settings, or the
        # stale-entry card's fix removes the repointed entry, the page must move.
        paragraph = settings_paragraph(DOC.read_text())
        fired = {check for check, _msg in problems(paragraph, _flipped(self.observed))}
        self.assertEqual(fired, set(_CHECKS))


if __name__ == "__main__":
    unittest.main()
