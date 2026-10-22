"""Lockstep guard: the three Codex SKILL.md mirror implementations agree.

The Codex normalization and the mirror walk around it exist in three
independent copies:

  1. `goc/install.py` — the writer (`_codex_skill_text` / `_write_codex_skill`),
  2. `scripts/sync_plugin_assets.py` — the mirror generator and its `--check`,
  3. `goc/engine.py` — nested inside `validate_plugin_mirror_parity`, the guard
     that actually SHIPS to consuming repos.

Two hardening fixes once reached only copies 1 and 2, leaving the shipped guard
the weakest of the three. This module pins all three to each other by behaviour,
so the next fix cannot reach two of three again — and it keeps holding if the
copies are later consolidated into one (the assertions are about output, not
about how many functions produce it).

See the card `a-third-copy-of-the-codex-skill-transform-lives-inside-goc-validate`.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import goc.engine as eng
from goc.install import _codex_skill_text, _write_codex_skill, skill_for_agent

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_SKILLS = ROOT / "goc" / "templates" / "skills"

#: SKILL.md shapes the transform has to agree on, including the ones that take
#: its early-return branches (no frontmatter, unterminated frontmatter) and the
#: `---`-in-description truncation all three copies share today.
CORPUS: dict[str, str] = {
    "plain": '---\nname: plain\ndescription: "a plain skill"\n---\n\n# Plain\n\nbody\n',
    "renamed": '---\nname: other-name\ndescription: "name overrides the dir"\n---\nbody\n',
    "no-frontmatter": "# Just a body\n\nno frontmatter here\n",
    "unterminated": "---\nname: unterminated\ndescription: never closed\n",
    "quotes-and-unicode": '---\nname: quotes\ndescription: "he said \\"go\\" — ünïcode"\n---\nbody\n',
    "dashes-in-description": '---\nname: dashes\ndescription: "a --- b"\n---\nbody\n',
    "no-description": "---\nname: nodesc\n---\nbody\n",
}


def _load_sync():
    """Import scripts/sync_plugin_assets.py without putting scripts/ on sys.path."""
    spec = importlib.util.spec_from_file_location(
        "_goc_sync_assets_lockstep", ROOT / "scripts" / "sync_plugin_assets.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _install_render(src: Path, *, skill_name: str) -> str:
    """The writer's render, with its `None` ("copy verbatim") sentinel resolved."""
    rendered = _codex_skill_text(src, skill_name=skill_name)
    return src.read_text() if rendered is None else rendered


class CodexTransformLockstepTest(unittest.TestCase):
    """Copies 1 and 2 are directly callable — compare their output head-on."""

    def setUp(self) -> None:
        self.sync = _load_sync()

    def test_corpus_renders_identically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for skill_name, text in CORPUS.items():
                src = Path(tmp) / skill_name / "SKILL.md"
                src.parent.mkdir(parents=True)
                src.write_text(text)
                with self.subTest(skill=skill_name):
                    self.assertEqual(
                        _install_render(src, skill_name=skill_name),
                        self.sync._codex_skill_text(src, skill_name=skill_name),
                        msg="goc/install.py and scripts/sync_plugin_assets.py "
                            "render this SKILL.md differently",
                    )

    def test_shipped_templates_render_identically(self) -> None:
        skills = [
            p for p in sorted(TEMPLATE_SKILLS.iterdir())
            if p.is_dir() and skill_for_agent(p.name, "codex")
        ]
        self.assertTrue(skills, msg="no codex-eligible skill templates found")
        for skill in skills:
            src = skill / "SKILL.md"
            with self.subTest(skill=skill.name):
                self.assertEqual(
                    _install_render(src, skill_name=skill.name),
                    self.sync._codex_skill_text(src, skill_name=skill.name),
                )


class CodexMirrorWalkLockstepTest(unittest.TestCase):
    """Copy 3 is nested inside `validate_plugin_mirror_parity`, so it is pinned
    by behaviour: the engine's verdict on a mirror must match both the writer
    that produced it and the sync check that also inspects it.
    """

    SKILL = "foo-skill"
    SIBLING = "reference.md"
    SIBLING_TEXT = "alpha\nbeta\n"
    SKILL_MD = '---\nname: foo-skill\ndescription: "a test skill"\n---\n\n# Foo\n\nbody\n'
    HOOK = "# hook\n"
    BOOTSTRAP = '#!/bin/sh\nexec goc "$@"\n'

    def _tree(self, tmp: str) -> Path:
        """A minimal REPO_ROOT whose codex payload is in sync, written by the
        real writer (`_write_codex_skill`) rather than by a restated transform.
        """
        cwd = Path(tmp)
        src = cwd / "goc" / "templates" / "skills" / self.SKILL
        src.mkdir(parents=True)
        (src / "SKILL.md").write_text(self.SKILL_MD)
        (src / self.SIBLING).write_text(self.SIBLING_TEXT)

        hooks = cwd / "goc" / "templates" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "deck_prompt_router.py").write_text(self.HOOK)
        bootstrap = cwd / "goc" / "templates" / "bootstrap"
        bootstrap.mkdir(parents=True)
        (bootstrap / "_goc-bootstrap.sh").write_text(self.BOOTSTRAP)
        (cwd / "goc" / "__init__.py").write_text("# goc package\n")

        mirror = cwd / "codex-plugin" / "skills" / self.SKILL
        mirror.mkdir(parents=True)
        _write_codex_skill(src / "SKILL.md", mirror / "SKILL.md", skill_name=self.SKILL)
        (mirror / self.SIBLING).write_text(self.SIBLING_TEXT)
        (cwd / "codex-plugin" / "skills" / "_goc-bootstrap.sh").write_text(self.BOOTSTRAP)

        codex_hooks = cwd / "codex-plugin" / "hooks"
        codex_hooks.mkdir(parents=True)
        (codex_hooks / "deck_prompt_router.py").write_text(self.HOOK)
        deep = cwd / "codex-plugin" / "goc"
        (deep / "templates" / "hooks").mkdir(parents=True)
        (deep / "templates" / "hooks" / "deck_prompt_router.py").write_text(self.HOOK)
        (deep / "templates" / "bootstrap").mkdir(parents=True)
        (deep / "templates" / "bootstrap" / "_goc-bootstrap.sh").write_text(self.BOOTSTRAP)
        (deep / "__init__.py").write_text("# goc package\n")
        return cwd

    def _engine(self, cwd: Path) -> str:
        old = eng.REPO_ROOT
        try:
            eng.REPO_ROOT = cwd
            errors = eng.validate_plugin_mirror_parity()
        finally:
            eng.REPO_ROOT = old
        return " ".join(e for e in errors if "codex-plugin/skills" in e)

    def _sync(self, cwd: Path) -> str:
        sync = _load_sync()
        old = sync.ROOT
        try:
            sync.ROOT = cwd
            paths = sync._check_codex_skill_tree(
                cwd / "codex-plugin" / "skills",
                preserve_files=frozenset({"_goc-bootstrap.sh"}),
            )
        finally:
            sync.ROOT = old
        return " ".join(str(p.relative_to(cwd)) for p in paths)

    def test_writer_output_satisfies_both_checks(self) -> None:
        """The engine's nested transform agrees with the writer's: a mirror
        `_write_codex_skill` just produced is drift-free to both readers.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self._tree(tmp)
            self.assertEqual("", self._engine(cwd))
            self.assertEqual("", self._sync(cwd))

    def test_untransformed_skill_is_drift_to_both(self) -> None:
        """Negative control for the assertion above — the clean verdict has to
        actually discriminate, or it would pass for any transform at all.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self._tree(tmp)
            (cwd / "codex-plugin" / "skills" / self.SKILL / "SKILL.md").write_text(
                self.SKILL_MD
            )
            self.assertIn("SKILL.md", self._engine(cwd))
            self.assertIn("SKILL.md", self._sync(cwd))

    def test_crlf_sibling_is_drift_to_both(self) -> None:
        """`read_text()` applies universal-newline translation, so a CRLF mirror
        copy reads identical to its LF source. Both walks compare siblings by
        bytes; the engine's copy missed that fix once.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self._tree(tmp)
            sib = cwd / "codex-plugin" / "skills" / self.SKILL / self.SIBLING
            sib.write_bytes(self.SIBLING_TEXT.replace("\n", "\r\n").encode())
            self.assertEqual(
                self.SIBLING_TEXT, sib.read_text(),
                msg="precondition: the CRLF copy must still read text-identical",
            )
            self.assertIn(self.SIBLING, self._engine(cwd))
            self.assertIn(self.SIBLING, self._sync(cwd))

    def test_empty_orphan_dir_is_drift_to_both(self) -> None:
        """git masks empty dirs and both walks skip dirs when looking at files,
        so an orphan with no source counterpart rots in the payload unless the
        dir walk reports it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self._tree(tmp)
            (cwd / "codex-plugin" / "skills" / "zzz-orphan-dir").mkdir()
            self.assertIn("zzz-orphan-dir", self._engine(cwd))
            self.assertIn("zzz-orphan-dir", self._sync(cwd))

    def test_nonempty_orphan_dir_reports_its_files_not_the_dir(self) -> None:
        """A non-empty orphan already surfaces through its own files; reporting
        the directory as well would double-count it. Both walks agree on that.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self._tree(tmp)
            orphan = cwd / "codex-plugin" / "skills" / "zzz-orphan-dir"
            orphan.mkdir()
            (orphan / "stale.md").write_text("stale\n")
            engine, sync = self._engine(cwd), self._sync(cwd)
            for verdict in (engine, sync):
                self.assertIn("zzz-orphan-dir/stale.md", verdict)
            self.assertEqual(1, engine.count("zzz-orphan-dir"), msg=engine)
            self.assertEqual(1, sync.count("zzz-orphan-dir"), msg=sync)


if __name__ == "__main__":
    unittest.main()
