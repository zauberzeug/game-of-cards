"""Regression guard: skill `!` preamble blocks must survive a host without `goc` on PATH.

The Claude Code host executes inline `!`...`` fences at skill load time and
aborts the ENTIRE skill load when a fence exits non-zero — the body, including
its own `goc: command not found` Preflight recovery guidance, never reaches the
agent. Two properties keep the load alive:

1. Every fence that invokes `goc` routes through the vendored bootstrap wrapper
   (`.claude/skills/_goc-bootstrap.sh`) when it exists, falling back to bare
   `goc` for plugin-mode loads where the plugin's `bin/` is on PATH.
2. Every fence is guarded (`|| true`, `|| echo ...`, or a trailing pipe into a
   zero-exit consumer) so a missing CLI degrades into error text inside the
   loaded body instead of aborting the load.

This test enforces (1) statically and (2) empirically: each extracted fence is
executed with a `goc` stub that fails like command-not-found (exit 127), both
with and without the bootstrap wrapper present, and must exit 0.

A third property keeps the load alive when the fence is *denied* rather than
failing: Claude Code aborts the load on a denied fence too, and a user's
`Bash(goc:*)` grant does not cover the compound routing of (1) (card
`denied-preamble-block-aborts-skill-load-before-the-preflight-routes-to-kickoff`).

3. A skill whose fences invoke `goc` pre-approves them: its frontmatter
   `allowed-tools` holds exactly one `Bash(<fence>)` entry per fence,
   verbatim, and nothing else. Entries are YAML single-quoted scalars, the one
   style with no backslash escapes, so they are read here exactly without a
   YAML library. Claude Code will not pre-approve command substitution, so
   such a fence must not contain `$(` or a backtick.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "goc" / "templates" / "skills"
BOOTSTRAP = ROOT / "goc" / "templates" / "bootstrap" / "_goc-bootstrap.sh"

_FENCE = re.compile(r"^\s*!`(.*)`\s*$")
# A bare `goc` command token — not part of `_goc-bootstrap.sh`, `.game-of-cards`,
# or an uppercase identifier like `GOC_WORKER`.
_GOC_TOKEN = re.compile(r"(?<![\w./-])goc(?![\w./-])")


def _iter_fences() -> list[tuple[str, int, str]]:
    fences: list[tuple[str, int, str]] = []
    for skill_md in sorted(SKILLS_DIR.rglob("SKILL.md")):
        for lineno, line in enumerate(skill_md.read_text().splitlines(), start=1):
            match = _FENCE.match(line)
            if match:
                fences.append((str(skill_md.relative_to(ROOT)), lineno, match.group(1)))
    return fences


def _invokes_goc(fence: str) -> bool:
    stripped = fence.replace("_goc-bootstrap.sh", "").replace(".game-of-cards", "")
    return bool(_GOC_TOKEN.search(stripped))


_ALLOWED_ENTRY = re.compile(r"^[ \t]+- '((?:[^']|'')*)'$")


def _allowed_tools(frontmatter: str) -> list[str] | None:
    """The unquoted `allowed-tools` entries, or None when the key is absent.

    Raises ValueError on an entry that is not a YAML single-quoted scalar.
    """
    lines = frontmatter.splitlines()
    if "allowed-tools:" not in lines:
        return None
    entries: list[str] = []
    for line in lines[lines.index("allowed-tools:") + 1 :]:
        if not line[:1].isspace():
            break
        match = _ALLOWED_ENTRY.match(line)
        if not match:
            raise ValueError(f"allowed-tools entry is not a single-quoted scalar: {line}")
        entries.append(match.group(1).replace("''", "'"))
    return entries


def preamble_rule_drift(text: str) -> list[str]:
    """Where a SKILL.md's `!` fences and its `allowed-tools` entries disagree."""
    frontmatter, body = "", text
    if text.startswith("---\n") and "\n---\n" in text[4:]:
        end = text.index("\n---\n", 4) + 1
        frontmatter, body = text[4:end], text[end:]
    fences = [m.group(1) for line in body.splitlines() if (m := _FENCE.match(line))]
    try:
        entries = _allowed_tools(frontmatter)
    except ValueError as exc:
        return [str(exc)]
    if entries is None:
        return [f"invokes goc without allowed-tools: !`{f}`" for f in fences if _invokes_goc(f)]
    rules = [f"Bash({fence})" for fence in fences]
    problems = [f"fence has no allowed-tools entry: {r}" for r in rules if r not in entries]
    problems += [f"allowed-tools entry matches no fence: {e}" for e in entries if e not in rules]
    problems += [f"duplicate allowed-tools entry: {e}" for e in sorted(set(entries)) if entries.count(e) > 1]
    problems += [
        f"fence uses command substitution Claude Code will not pre-approve: !`{f}`"
        for f in fences
        if "$(" in f or "`" in f
    ]
    return problems


class SkillPreambleBlockTest(unittest.TestCase):
    def test_fences_found(self) -> None:
        fences = _iter_fences()
        self.assertGreaterEqual(len(_iter_fences()), 15, fences)
        self.assertTrue(any(_invokes_goc(f) for _, _, f in fences))

    def test_goc_fences_route_through_bootstrap(self) -> None:
        offenders = [
            f"{path}:{lineno}: !`{fence}`"
            for path, lineno, fence in _iter_fences()
            if _invokes_goc(fence) and "_goc-bootstrap.sh" not in fence
        ]
        self.assertFalse(
            offenders,
            msg=(
                "Found `!` fence(s) invoking bare `goc` without routing through "
                ".claude/skills/_goc-bootstrap.sh. On hosts where `goc` is not on "
                "PATH (this dogfood repo, vendored installs before pipx install) "
                "the fence fails and Claude Code aborts the whole skill load. Use: "
                "b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b "
                "<args>; else goc <args>; fi 2>&1 || true\n  " + "\n  ".join(offenders)
            ),
        )

    def _run_fences(self, workdir: Path) -> list[str]:
        """Execute every fence in `workdir` with a failing `goc` stub on PATH."""
        stub_dir = workdir / "_stub-bin"
        stub_dir.mkdir(exist_ok=True)
        stub = stub_dir / "goc"
        stub.write_text('#!/bin/sh\necho "goc: command not found" >&2\nexit 127\n')
        stub.chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = f"{stub_dir}:{env.get('PATH', '/usr/bin:/bin')}"
        failures: list[str] = []
        for path, lineno, fence in _iter_fences():
            result = subprocess.run(
                ["/bin/bash", "-c", fence],
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                failures.append(
                    f"{path}:{lineno}: exit {result.returncode}\n"
                    f"    fence: !`{fence}`\n"
                    f"    stderr: {result.stderr.strip()[:200]}"
                )
        return failures

    def test_fences_exit_zero_without_goc_or_bootstrap(self) -> None:
        # Plugin-shaped host gone wrong: no vendored bootstrap, no working goc.
        with tempfile.TemporaryDirectory() as tmp:
            failures = self._run_fences(Path(tmp))
        self.assertFalse(
            failures,
            msg=(
                "Fence(s) exit non-zero on a host without goc — Claude Code would "
                "abort the skill load before the body's recovery guidance is "
                "delivered:\n  " + "\n  ".join(failures)
            ),
        )

    def test_fences_exit_zero_with_bootstrap_but_no_cli(self) -> None:
        # Vendored fresh-clone host: bootstrap present, CLI still missing.
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            skills = workdir / ".claude" / "skills"
            skills.mkdir(parents=True)
            shutil.copy2(BOOTSTRAP, skills / "_goc-bootstrap.sh")
            failures = self._run_fences(workdir)
        self.assertFalse(
            failures,
            msg=(
                "Fence(s) exit non-zero on a vendored host whose CLI is missing — "
                "the bootstrap's install hint must land in the loaded body, not "
                "abort the load:\n  " + "\n  ".join(failures)
            ),
        )


_ROUTED = "b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b; else goc; fi 2>&1 || true"
_CAT = "cat .game-of-cards/hooks/x.md 2>/dev/null || true"


def _skill(entries: list[str] | None, fences: list[str]) -> str:
    frontmatter = "---\nname: x\ndescription: y\n"
    if entries is not None:
        frontmatter += "allowed-tools:\n" + "".join(f"  - {e}\n" for e in entries)
    return frontmatter + "---\n\n" + "".join(f"!`{f}`\n\n" for f in fences)


def _quoted(rule: str) -> str:
    return "'" + rule.replace("'", "''") + "'"


class SkillAllowedToolsParityTest(unittest.TestCase):
    def test_every_skill_pre_approves_exactly_its_fences(self) -> None:
        problems = [
            f"{skill_md.relative_to(ROOT)}: {problem}"
            for skill_md in sorted(SKILLS_DIR.rglob("SKILL.md"))
            for problem in preamble_rule_drift(skill_md.read_text(encoding="utf-8"))
        ]
        self.assertEqual([], problems)

    def test_guard_catches_planted_drift(self) -> None:
        exact = [_quoted(f"Bash({_ROUTED})"), _quoted(f"Bash({_CAT})")]
        self.assertEqual([], preamble_rule_drift(_skill(exact, [_ROUTED, _CAT])))
        cases = {
            "goc fence, no allowed-tools": _skill(None, [_ROUTED]),
            "fence without entry": _skill(exact[:1], [_ROUTED, _CAT]),
            "stale entry": _skill(exact + [_quoted("Bash(goc --gone)")], [_ROUTED, _CAT]),
            "entry off by one space": _skill([_quoted(f"Bash({_ROUTED} )")], [_ROUTED]),
            "duplicate entry": _skill(exact + exact[:1], [_ROUTED, _CAT]),
            "double-quoted entry": _skill([f'"Bash({_CAT})"'], [_CAT]),
            "command substitution": _skill(
                [_quoted("Bash(n=$(goc --json); echo $n || true)")],
                ["n=$(goc --json); echo $n || true"],
            ),
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.assertNotEqual([], preamble_rule_drift(text))

    def test_single_quote_escapes_round_trip(self) -> None:
        fence = "echo 'it''s' || true"
        self.assertEqual(
            [], preamble_rule_drift(_skill([_quoted(f"Bash({fence})")], [fence]))
        )


if __name__ == "__main__":
    unittest.main()
