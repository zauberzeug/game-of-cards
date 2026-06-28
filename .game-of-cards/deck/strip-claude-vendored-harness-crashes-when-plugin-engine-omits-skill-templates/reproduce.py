"""Reproduce: _strip_claude_vendored_harness crashes when the engine's
template tree omits skills/ (the shape of the bundled plugin payload).

The vendored->plugin migration cleanup iterates `templates/skills`
unconditionally. The plugin payload deliberately omits that subdir
(claude-plugin/goc/templates/ has no skills/), so confirming the
documented "switch skills_source to plugin, then goc upgrade" cleanup
raises FileNotFoundError before any cleanup happens.

Exit 0 == defect no longer fires (cleanup completes, user skills kept).
Exit 1 == defect reproduced (FileNotFoundError) or user skill destroyed.
"""

import shutil
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

real_templates = _repo_root() / "goc" / "templates"

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    templates = td / "templates"
    # Mimic the bundled plugin payload: every template subtree EXCEPT skills/.
    shutil.copytree(real_templates, templates, ignore=shutil.ignore_patterns("skills"))
    assert not (templates / "skills").exists(), "test setup: skills/ must be absent"

    target = td / "repo"
    goc_skill = target / ".claude" / "skills" / "deck"
    goc_skill.mkdir(parents=True)
    (goc_skill / "SKILL.md").write_text("goc-managed")
    user_skill = target / ".claude" / "skills" / "my-custom-skill"
    user_skill.mkdir(parents=True)
    (user_skill / "SKILL.md").write_text("user-authored")

    try:
        install._strip_claude_vendored_harness(target, templates)
    except FileNotFoundError as exc:
        print(f"REPRODUCED: FileNotFoundError during cleanup: {exc}")
        print("Cleanup crashed; vendored->plugin migration is broken from the plugin engine.")
        sys.exit(1)

    # No crash: the conservative fix must never destroy user-authored skills.
    if not user_skill.exists():
        print("REGRESSION: user-authored skill was destroyed by cleanup")
        sys.exit(1)

    print("OK: cleanup completed without crash; user-authored skill preserved")
    print(f"  my-custom-skill still present: {user_skill.exists()}")
    sys.exit(0)
