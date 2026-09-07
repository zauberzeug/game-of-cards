"""Class-level re-run safety over goc's whole command surface.

Seven shipped defects share one shape: an operation that is correct the first
time it runs and wrong the second. Each was fixed with a test for that one
verb, so the property was enforced in arrears and a verb added later inherited
nothing. This module enforces it as a class instead: the surface list is
derived from the engine's own parser registration (plus the two verbs cli.py
intercepts before the parser exists), every surface is run twice against a
scratch repo, and the second run has to leave the recorded state alone.

Each surface declares one disposition, which is the whole of its re-run
contract:

    READ_ONLY  neither run may touch the tree
    NO_OP      second run exits 0 and touches nothing
    REFUSES    second run exits nonzero and touches nothing
    RE_EMITS   second run exits 0 and rewrites files with identical bytes
    APPENDS    second run exits 0 and only extends existing files

Adding a verb without adding a row here fails
`test_every_registered_surface_has_a_rerun_recipe`, which is the point: the
list is derived, so the omission cannot go unnoticed.
"""

from __future__ import annotations

import argparse
import difflib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Callable, NamedTuple

ROOT = Path(__file__).resolve().parents[1]

READ_ONLY = "READ_ONLY"
NO_OP = "NO_OP"
REFUSES = "REFUSES"
RE_EMITS = "RE_EMITS"
APPENDS = "APPENDS"


def _run(cwd: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(ROOT), env.get("PYTHONPATH")) if p
    )
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        # goc's interactive prompts fall back to their default answer off a
        # tty; DEVNULL keeps that path deterministic instead of inheriting
        # whatever stdin the test runner was started with.
        stdin=subprocess.DEVNULL,
        check=False,
    )


def _goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(cwd, [sys.executable, "-m", "goc.cli", *args])


def _stub(cwd: Path, code: str) -> subprocess.CompletedProcess[str]:
    return _run(cwd, [sys.executable, "-c", code])


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

CONFIG = """\
layer_2_project_dod: []
layer_3_goc_dod:
  - name: dod-100-percent
    kind: derived
workflow:
  auto_commit: false
"""

# A card written by hand rather than by `goc new`, so its relation lists are
# in the inline style `migrate-list-style` exists to convert. Without one the
# verb's first run is a no-op and the re-run comparison proves nothing.
INLINE_STYLE_CARD = """\
---
title: inline-style-probe-card
summary: "Carries inline-style relation lists so migrate-list-style has work to do."
status: open
stage: null
contribution: medium
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: [alpha-probe-card]
advanced_by: []
tags: [story]
definition_of_done: |
  - [ ] MECHANICAL: the probe exercises this card
---

# Inline style probe card

Probe fixture.
"""

LEGACY_CARD = """\
---
title: legacy-probe-card
summary: "Lives in the pre-.game-of-cards deck/ tree so goc migrate has work to do."
status: open
stage: null
contribution: medium
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story]
definition_of_done: |
  - [ ] MECHANICAL: the probe exercises this card
---

# Legacy probe card

Probe fixture.
"""


def _bare_repo(root: Path) -> None:
    """A repo goc can install into: git tree, project marker, nothing else."""
    subprocess.run(["git", "init", "-q", "."], cwd=root, check=True)
    for key, value in (("user.email", "probe@example.com"), ("user.name", "probe")):
        subprocess.run(["git", "config", key, value], cwd=root, check=True)
    (root / "pyproject.toml").write_text("# probe fixture\n", encoding="utf-8")


def _author(root: Path, title: str) -> None:
    """Fill in a `goc new` scaffold so it is no longer an unauthored draft."""
    path = root / ".game-of-cards" / "deck" / title / "README.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "- [ ] (replace with real criteria)",
        "- [ ] MECHANICAL: the probe exercises this card",
    ).replace("(write the design doc here)", "Probe fixture.")
    path.write_text(text, encoding="utf-8")


def _new_card(root: Path, title: str, *, gate: str = "none", publish: bool = True) -> None:
    _goc(root, "new", title, "--summary", "Probe fixture card.", "--gate", gate)
    _author(root, title)
    if publish:
        _goc(root, "publish", title)


def _build_scratch_deck(root: Path) -> None:
    """A repo with a small, valid deck: two published cards plus one draft."""
    _bare_repo(root)
    (root / ".game-of-cards" / "deck").mkdir(parents=True)
    (root / ".game-of-cards" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    _new_card(root, "alpha-probe-card")
    _new_card(root, "beta-probe-card")
    _new_card(root, "draft-probe-card", publish=False)


#: Built once by `VerbRerunSafetyTest.setUpClass` and copied per surface.
#: Scaffolding it through `goc new` costs seven subprocesses; doing that for
#: each of two dozen surfaces dominated the module's runtime.
_DECK_TEMPLATE: Path | None = None


def _scratch_deck(root: Path) -> None:
    if _DECK_TEMPLATE is None:  # pragma: no cover - direct call outside the suite
        _build_scratch_deck(root)
        return
    shutil.copytree(_DECK_TEMPLATE, root, dirs_exist_ok=True)


def _deck_with_ticked_dod(root: Path) -> None:
    _scratch_deck(root)
    path = root / ".game-of-cards" / "deck" / "alpha-probe-card" / "README.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("- [ ] MECHANICAL", "- [x] MECHANICAL"),
        encoding="utf-8",
    )


def _deck_with_gated_card(root: Path) -> None:
    _scratch_deck(root)
    _new_card(root, "gated-probe-card", gate="decision")


def _deck_with_edge(root: Path) -> None:
    _scratch_deck(root)
    _goc(root, "advance", "alpha-probe-card", "--by", "beta-probe-card")


def _deck_with_half_edge(root: Path) -> None:
    """Drop one side of a wired edge so `repair-edges --apply` has work to do."""
    _deck_with_edge(root)
    path = root / ".game-of-cards" / "deck" / "alpha-probe-card" / "README.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "advanced_by:\n  - beta-probe-card\n", "advanced_by: []\n"
        ),
        encoding="utf-8",
    )


def _deck_with_inline_style_card(root: Path) -> None:
    _scratch_deck(root)
    card = root / ".game-of-cards" / "deck" / "inline-style-probe-card"
    card.mkdir()
    (card / "README.md").write_text(INLINE_STYLE_CARD, encoding="utf-8")
    (card / "log.md").write_text("", encoding="utf-8")


def _deck_with_legacy_tree(root: Path) -> None:
    _scratch_deck(root)
    card = root / "deck" / "legacy-probe-card"
    card.mkdir(parents=True)
    (card / "README.md").write_text(LEGACY_CARD, encoding="utf-8")
    (card / "log.md").write_text("", encoding="utf-8")


def _vendored_install(root: Path) -> None:
    """Install with skills in source control, the path that merges settings.json.

    `_merge_claude_settings` is reachable only from the vendored install, and it
    is the surface behind two of the seven instances this check generalizes, so
    `upgrade` is probed on the mode that actually re-runs the merge.
    """
    _bare_repo(root)
    _goc(root, "install", "--claude", "--local-skills")


# --------------------------------------------------------------------------
# the surface table
# --------------------------------------------------------------------------


class Surface(NamedTuple):
    expect: str
    argv: tuple[str, ...]
    fixture: Callable[[Path], None] = _scratch_deck
    note: str = ""


SURFACES: dict[str, Surface] = {
    # Read-only verbs. `quality-pass` sits here because its mutating path is
    # `--llm`, which needs a model in the loop; the reporting pass it runs by
    # default writes nothing.
    "validate": Surface(READ_ONLY, ("validate",)),
    "show": Surface(READ_ONLY, ("show", "alpha-probe-card")),
    "triage": Surface(READ_ONLY, ("triage",)),
    "quality-pass": Surface(READ_ONLY, ("quality-pass", "--status", "all")),
    # Mutating deck verbs.
    "new": Surface(
        REFUSES,
        ("new", "delta-probe-card", "--summary", "Probe fixture card.", "--gate", "none"),
        note="a second scaffold under a taken title is a collision, not a no-op",
    ),
    "status": Surface(NO_OP, ("status", "beta-probe-card", "active")),
    "done": Surface(NO_OP, ("done", "alpha-probe-card"), _deck_with_ticked_dod),
    "attest": Surface(
        APPENDS,
        ("attest", "alpha-probe-card", "--non-interactive"),
        _deck_with_ticked_dod,
        note="log.md is a journal; a second attestation is a second event, "
        "and the check is that it extends the record rather than rewriting it",
    ),
    "decide": Surface(
        REFUSES,
        ("decide", "gated-probe-card", "--decision", "probe", "--because", "probe"),
        _deck_with_gated_card,
        note="the gate is already down, so there is no decision left to record",
    ),
    "publish": Surface(NO_OP, ("publish", "draft-probe-card")),
    "advance": Surface(
        RE_EMITS,
        ("advance", "alpha-probe-card", "--by", "beta-probe-card"),
        note="re-emits both endpoints unconditionally; the bytes are identical",
    ),
    "unadvance": Surface(
        RE_EMITS,
        ("unadvance", "alpha-probe-card", "--by", "beta-probe-card"),
        _deck_with_edge,
        note="re-emits both endpoints unconditionally; the bytes are identical",
    ),
    "wait": Surface(
        RE_EMITS,
        ("wait", "alpha-probe-card", "--reason", "external"),
        note="re-emits the card unconditionally; the bytes are identical",
    ),
    "repair-edges": Surface(NO_OP, ("repair-edges", "--apply"), _deck_with_half_edge),
    "move": Surface(
        REFUSES,
        ("move", "beta-probe-card", "gamma-probe-card"),
        note="the old title is gone after the first run, so the second cannot resolve it",
    ),
    "migrate": Surface(NO_OP, ("migrate", "--yes"), _deck_with_legacy_tree),
    "migrate-list-style": Surface(
        NO_OP, ("migrate-list-style",), _deck_with_inline_style_card
    ),
    # Verbs cli.py intercepts on argv[0]; they never reach the engine parser.
    "install": Surface(
        REFUSES,
        ("install", "--claude"),
        _bare_repo,
        note="refusing a second install with a `goc upgrade` hint is the "
        "contract pinned by tests/test_install.py",
    ),
    "upgrade": Surface(
        RE_EMITS,
        ("upgrade", "--claude", "--keep-local-skills"),
        _vendored_install,
        note="re-emits config.yaml, the version sentinel and the briefing "
        "files unconditionally; the bytes are identical",
    ),
}


def registered_surfaces() -> set[str]:
    """Every verb goc exposes, read off the two places verbs get registered.

    argparse has no public accessor for a parser's subcommands, so the
    subparser action is picked out of `_actions`; the alternative is
    hard-coding the list, which is the defect this module exists to prevent.
    """
    from goc.cli import INSTALL_VERBS
    from goc.engine import _build_parser

    verbs = set(INSTALL_VERBS)
    for action in _build_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            verbs.update(action.choices)
    return verbs


def _snapshot(root: Path) -> dict[str, tuple[int, str]]:
    """Every tracked path mapped to (mtime_ns, content).

    Content alone is too weak for the verbs that stamp a timestamp: two runs
    150ms apart write the same second, so a re-stamped `closed_at` — the
    `done-rerun-rewrites-closure-date` defect — compares equal. The mtime
    catches a rewrite whose bytes happen to match.
    """
    snap: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(".git/") or "__pycache__/" in rel:
            continue
        stat = path.stat()
        snap[rel] = (stat.st_mtime_ns, path.read_text(encoding="utf-8", errors="replace"))
    return snap


class VerbRerunSafetyTest(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        global _DECK_TEMPLATE
        cls._template_dir = tempfile.TemporaryDirectory()
        _DECK_TEMPLATE = Path(cls._template_dir.name)
        _build_scratch_deck(_DECK_TEMPLATE)

    @classmethod
    def tearDownClass(cls) -> None:
        global _DECK_TEMPLATE
        _DECK_TEMPLATE = None
        cls._template_dir.cleanup()

    def test_every_registered_surface_has_a_rerun_recipe(self) -> None:
        registered = registered_surfaces()
        self.assertEqual(
            registered,
            set(SURFACES),
            "the recipe table and goc's registered verbs have diverged — add a "
            "row to SURFACES declaring what a second run of the new verb does "
            "(a verb with no row is a verb nothing re-runs)",
        )

    def test_every_registered_surface_is_rerun_safe(self) -> None:
        for name in sorted(SURFACES):
            surface = SURFACES[name]
            with self.subTest(surface=name, expect=surface.expect):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    surface.fixture(root)
                    self.assert_rerun_safe(
                        name,
                        surface.expect,
                        root,
                        lambda root=root, surface=surface: _goc(root, *surface.argv),
                    )

    def test_the_rerun_check_catches_an_offender(self) -> None:
        """A guard that has only ever seen a clean tree proves nothing.

        Each stub below violates exactly one clause of one disposition, and
        each has to make `assert_rerun_safe` fail.
        """
        offenders = (
            ("rewrites content on the second run", NO_OP, _APPEND_LINE),
            ("rewrites identical bytes on the second run", NO_OP, _RETOUCH),
            ("succeeds where the contract says it refuses", REFUSES, _ONCE_ONLY),
            ("overwrites the journal it should extend", APPENDS, _CLOBBER_JOURNAL),
            ("changes content where only a re-emit is allowed", RE_EMITS, _APPEND_LINE),
        )
        for label, expect, code in offenders:
            with self.subTest(offender=label, expect=expect):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    _scratch_deck(root)
                    with self.assertRaises(self.failureException):
                        self.assert_rerun_safe(
                            f"stub ({label})",
                            expect,
                            root,
                            lambda root=root, code=code: _stub(root, code),
                        )

    # ----------------------------------------------------------------- core

    def assert_rerun_safe(
        self,
        name: str,
        expect: str,
        root: Path,
        run: Callable[[], subprocess.CompletedProcess[str]],
    ) -> None:
        initial = _snapshot(root)
        self.assertTrue(
            initial, f"{name}: the fixture wrote nothing — the probe would be vacuous"
        )

        first = run()
        before = _snapshot(root)
        second = run()
        after = _snapshot(root)

        if expect == READ_ONLY:
            self._assert_untouched(name, "the first run", initial, before)
            self._assert_exit(name, "the first run", first, expect_zero=True)
        else:
            self._assert_exit(name, "the first run", first, expect_zero=True)
            self.assertNotEqual(
                initial,
                before,
                f"{name}: the first run changed nothing, so the second run "
                f"proves nothing — fix the fixture, not the assertion",
            )

        if expect == REFUSES:
            self._assert_exit(name, "the second run", second, expect_zero=False)
        else:
            self._assert_exit(name, "the second run", second, expect_zero=True)

        if expect in (READ_ONLY, NO_OP, REFUSES):
            self._assert_untouched(name, "the second run", before, after)
        elif expect == RE_EMITS:
            self._assert_same_bytes(name, before, after)
            self.assertTrue(
                [p for p in before if p in after and before[p][0] != after[p][0]],
                f"{name}: declared {RE_EMITS} but the second run rewrote nothing "
                f"— it is stricter than its recipe claims, so declare it {NO_OP}",
            )
        elif expect == APPENDS:
            self._assert_extends(name, before, after)
        else:  # pragma: no cover - guarded by the recipe table
            self.fail(f"{name}: unknown disposition {expect!r}")

    # ------------------------------------------------------------ clauses

    def _assert_exit(
        self,
        name: str,
        which: str,
        result: subprocess.CompletedProcess[str],
        *,
        expect_zero: bool,
    ) -> None:
        detail = f"\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        if expect_zero:
            self.assertEqual(
                result.returncode, 0, f"{name}: {which} failed{detail}"
            )
        else:
            self.assertNotEqual(
                result.returncode,
                0,
                f"{name}: {which} was expected to refuse but exited 0{detail}",
            )

    def _assert_same_bytes(
        self,
        name: str,
        before: dict[str, tuple[int, str]],
        after: dict[str, tuple[int, str]],
    ) -> None:
        self.assertEqual(
            sorted(after), sorted(before),
            f"{name}: the second run added or removed files\n"
            f"  added:   {sorted(set(after) - set(before))}\n"
            f"  removed: {sorted(set(before) - set(after))}",
        )
        for path in sorted(set(before) & set(after)):
            if before[path][1] != after[path][1]:
                self.fail(
                    f"{name}: the second run rewrote {path}\n"
                    + _diff(before[path][1], after[path][1])
                )

    def _assert_untouched(
        self,
        name: str,
        which: str,
        before: dict[str, tuple[int, str]],
        after: dict[str, tuple[int, str]],
    ) -> None:
        self._assert_same_bytes(name, before, after)
        retouched = [p for p in before if p in after and before[p][0] != after[p][0]]
        self.assertEqual(
            retouched, [],
            f"{name}: {which} rewrote these files with identical bytes: "
            f"{retouched}. A same-bytes rewrite hides a re-stamped timestamp, "
            f"so it counts as a change here; if it is deliberate, declare the "
            f"surface {RE_EMITS}.",
        )

    def _assert_extends(
        self,
        name: str,
        before: dict[str, tuple[int, str]],
        after: dict[str, tuple[int, str]],
    ) -> None:
        self.assertEqual(
            sorted(set(before) - set(after)), [],
            f"{name}: the second run removed "
            f"{sorted(set(before) - set(after))} — an append-only surface may "
            f"extend the record, never drop it",
        )
        grew = False
        for path in sorted(before):
            old, new = before[path][1], after[path][1]
            if not new.startswith(old):
                self.fail(
                    f"{name}: the second run rewrote history in {path} instead "
                    f"of extending it\n" + _diff(old, new)
                )
            grew = grew or len(new) > len(old)
        self.assertTrue(
            grew,
            f"{name}: declared {APPENDS} but the second run appended nothing — "
            f"it is stricter than its recipe claims, so declare it {NO_OP}",
        )


def _diff(old: str, new: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            old.splitlines(), new.splitlines(),
            fromfile="after run 1", tofile="after run 2", lineterm="",
        )
    )


# Stub surfaces for test_the_rerun_check_catches_an_offender. They run through
# the same subprocess-and-snapshot path as the real verbs, so what they prove
# about the check transfers.
_CARD = "'.game-of-cards/deck/alpha-probe-card/{}'"
_APPEND_LINE = (
    "import pathlib\n"
    f"p = pathlib.Path({_CARD.format('log.md')})\n"
    "p.write_text(p.read_text() + 'stub line\\n')\n"
)
_RETOUCH = (
    "import pathlib\n"
    f"p = pathlib.Path({_CARD.format('README.md')})\n"
    "p.write_text(p.read_text())\n"
)
_ONCE_ONLY = (
    "import pathlib\n"
    f"p = pathlib.Path({_CARD.format('log.md')})\n"
    "t = p.read_text()\n"
    "if 'stub line' not in t:\n"
    "    p.write_text(t + 'stub line\\n')\n"
)
_CLOBBER_JOURNAL = (
    "import pathlib\n"
    f"p = pathlib.Path({_CARD.format('log.md')})\n"
    "t = p.read_text()\n"
    "p.write_text('clobbered\\n' if 'stub line' in t else t + 'stub line\\n')\n"
)


if __name__ == "__main__":
    unittest.main()
