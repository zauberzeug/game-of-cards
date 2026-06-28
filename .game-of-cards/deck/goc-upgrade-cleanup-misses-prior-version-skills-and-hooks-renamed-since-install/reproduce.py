"""Reproduce: goc upgrade cleanup leaves prior-version GoC skills and hooks
on disk because the GoC-ownership discriminator is the current-template name
intersection.

Strategy: build a synthetic templates tree that ships ONE skill (`kickoff`),
build a synthetic `.claude/skills/` tree that has BOTH `kickoff` (current)
AND `bootstrap` (prior-version GoC, e.g. before the bootstrap→kickoff
rename), then run `_strip_claude_vendored_harness` and observe what
remains. The bug: `bootstrap/` survives despite being GoC-owned content
from an earlier release.
"""

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

import tempfile
import textwrap

from goc.install import _strip_claude_vendored_harness


def _seed_templates(templates: Path) -> None:
    """Build a minimal templates tree with one current skill: `kickoff`."""
    skills = templates / "skills"
    skills.mkdir(parents=True)
    kickoff = skills / "kickoff"
    kickoff.mkdir()
    (kickoff / "SKILL.md").write_text(
        textwrap.dedent(
            """\
            ---
            name: kickoff
            description: current GoC onboarding skill
            ---

            body
            """
        )
    )
    # Minimal agent shim so `_load_agent_shim(templates, "claude")` works.
    agents = templates / "agents" / "claude"
    agents.mkdir(parents=True)
    (agents / "manifest.json").write_text(
        textwrap.dedent(
            """\
            {
              "name": "claude",
              "skills": {"target": ".claude/skills", "frontmatter": "native"},
              "files": [],
              "settings_json": ".claude/settings.json"
            }
            """
        )
    )


def _seed_consumer(target: Path) -> None:
    """A consuming repo that vendored both the current skill (`kickoff`)
    and an older skill (`bootstrap`) — `bootstrap` was renamed to
    `kickoff` between GoC versions per the closed card
    `rename-bootstrap-to-kickoff-as-onboarding-dialog`.
    """
    claude_skills = target / ".claude" / "skills"
    claude_skills.mkdir(parents=True)
    for name, body in [
        ("kickoff", "current GoC skill\n"),
        ("bootstrap", "prior-version GoC skill (renamed to kickoff)\n"),
    ]:
        d = claude_skills / name
        d.mkdir()
        (d / "SKILL.md").write_text(
            textwrap.dedent(
                f"""\
                ---
                name: {name}
                description: {body.strip()}
                ---

                body
                """
            )
        )


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        templates = td_path / "templates"
        target = td_path / "consumer"

        _seed_templates(templates)
        _seed_consumer(target)

        # Pre-state: both dirs present.
        kickoff_dir = target / ".claude" / "skills" / "kickoff"
        bootstrap_dir = target / ".claude" / "skills" / "bootstrap"
        assert kickoff_dir.is_dir(), "kickoff missing in seeded consumer"
        assert bootstrap_dir.is_dir(), "bootstrap missing in seeded consumer"

        _strip_claude_vendored_harness(target, templates)

        kickoff_survives = kickoff_dir.is_dir()
        bootstrap_survives = bootstrap_dir.is_dir()

        print(f"current-template skill removed by cleanup: {not kickoff_survives}")
        print(f"prior-version skill survives cleanup:      {bootstrap_survives}")

        # Bug signature: the prior-version skill survives. The current
        # skill is correctly removed (the cleanup is otherwise intact).
        if bootstrap_survives and not kickoff_survives:
            print("\nBUG REPRODUCED: prior-version GoC content survives cleanup")
            print("because the discriminator is the current-templates name set,")
            print("which does not include skills that have been renamed/removed.")
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(main())
