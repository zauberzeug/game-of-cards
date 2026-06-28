"""Reproduce: a pristine, never-user-edited config.yaml classifies as
`preserved` (= authored divergence) in the upgrade divergence report,
because `goc install` itself mutates the `skills_source:` key right
after copying the template.

The `upgrade` skill treats every `evolving` file with status
`preserved` as authored-divergence and drives an interactive 2-way LLM
reconcile (AskUserQuestion). So every consumer's *first* `goc upgrade`
gets a needless reconcile prompt for config.yaml.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
"""

import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import install  # noqa: E402


def main() -> int:
    repo = _repo_root()
    templates = install._templates_root()
    template_config = templates / "game_of_cards" / "config.yaml"

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        # Simulate `goc install`: copy the template config, then apply the
        # engine's own targeted skills_source rewrite (install.py:1545/1780).
        dest_goc = target / ".game-of-cards"
        dest_goc.mkdir(parents=True)
        dest_config = dest_goc / "config.yaml"
        dest_config.write_bytes(template_config.read_bytes())
        install._write_skills_source(target, "plugin")

        # The user has made ZERO edits. Now classify as the upgrade
        # divergence report does.
        status = install._classify_user_owned_file(template_config, dest_config)

        template_line = next(
            ln for ln in template_config.read_text().splitlines()
            if "skills_source" in ln
        )
        dest_line = next(
            ln for ln in dest_config.read_text().splitlines()
            if "skills_source" in ln
        )

        print("template skills_source line:", repr(template_line))
        print("installed skills_source line:", repr(dest_line))
        print("byte-identical to template:",
              dest_config.read_bytes() == template_config.read_bytes())
        print("divergence-report status:", status)
        print()

        ownership = "evolving"  # config.yaml is in _EVOLVING_USER_OWNED_FILES
        reconcile = ownership == "evolving" and status == "preserved"
        print(f"ownership={ownership!r} -> upgrade skill drives LLM reconcile:",
              reconcile)
        print()

        if status == "preserved" and reconcile:
            print("DEFECT CONFIRMED: a pristine config.yaml (no user edits) is")
            print("reported as `preserved` (authored divergence) and would")
            print("trigger a needless interactive reconcile on first upgrade.")
            return 0
        print("Defect NOT reproduced: status is", status)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
