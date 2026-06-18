"""Reproduce: `goc install --dry-run` / `goc upgrade --dry-run` promise a
`.pre-commit-config.yaml` append that the real run skips in a non-git dir.

`_plan_writes` (goc/install.py) appends the pre-commit write unconditionally,
but the executor `_append_precommit_hook` returns early when `.git` is absent.
So the dry-run plan lists a write — and inflates the "N writes planned" count
— that the real run will never perform when the target is not a git repo.

Run on a clean checkout:
    uv run python .game-of-cards/deck/dry-run-plan-promises-pre-commit-append-that-real-install-skips-in-non-git-dir/reproduce.py
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

from goc import install as I  # noqa: E402

templates = I._templates_root()

with tempfile.TemporaryDirectory() as td:
    target = Path(td) / "consumer"
    target.mkdir()
    # No `git init` — this is a non-git directory.
    assert not (target / ".git").exists()

    plan = I._plan_writes(
        target=target,
        templates=templates,
        agents=["claude"],
        local_skills_agents=set(),
        briefing_target="AGENTS.md",
    )
    planned_precommit = [
        w for w in plan if w.path.name == ".pre-commit-config.yaml"
    ]
    print(f"  dry-run plan size: {len(plan)} writes")
    print(f"  plan lists .pre-commit-config.yaml append: {bool(planned_precommit)}")

    # What the executor actually does in a non-git dir:
    precommit = target / ".pre-commit-config.yaml"
    I._append_precommit_hook(precommit)
    print(f"  executor created .pre-commit-config.yaml: {precommit.exists()}")

print()
if planned_precommit and not precommit.exists():
    print(
        "DEFECT REPRODUCED: dry-run plan promises a .pre-commit-config.yaml "
        "append the real run skips when .git is absent (plan/executor disagree)."
    )
    sys.exit(1)
print("No defect: plan and executor agree on the pre-commit append.")
sys.exit(0)
