"""Proof: the pattern-generalization mutation detector misses git
commit/add when the git invocation is not the literal first word of a
compound, chained, subshell, or env-prefixed Bash command.

The Stop hook (`goc/templates/hooks/pattern_generalization_check.py`) is
meant to fire the generalization self-assessment on any turn that
committed code via Bash. `_is_broad_git_mutation` tokenizes the whole
command and requires `tokens[0] == "git"`, so any command where `git`
isn't the first token slips through and the hook silently never fires.

Run on a clean checkout:
    uv run python .game-of-cards/deck/<title>/reproduce.py

Exits non-zero while the defect is present (prints each missed shape),
exits zero once the detector inspects every simple-command segment.
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

from goc.templates.hooks.pattern_generalization_check import (  # noqa: E402
    _is_broad_git_mutation,
)

# Compound / chained / subshell / env-prefixed commands that DO mutate the
# index via a broad git invocation. Every one should fire the detector.
SHOULD_FIRE = [
    "cd subdir && git commit -m x",
    "git add foo.py && git commit -m x",
    "false || git commit -m x",
    "( cd repo && git commit -m x )",
    "GIT_EDITOR=true git commit",
    "cd build && git add -A",
]

# Baselines that must keep their current verdict (regression guard).
MUST_STAY_TRUE = ["git commit -m x", "git add -A", "git add .", 'git commit -m "a|b"']
MUST_STAY_FALSE = ["git status", "git add foo.py", "git add -- foo.py", "ls && pwd"]

missed = [c for c in SHOULD_FIRE if not _is_broad_git_mutation(c)]
false_pos = [c for c in MUST_STAY_FALSE if _is_broad_git_mutation(c)]
false_neg = [c for c in MUST_STAY_TRUE if not _is_broad_git_mutation(c)]

print("Compound/chained commands the detector SHOULD fire on:")
for c in SHOULD_FIRE:
    verdict = _is_broad_git_mutation(c)
    print(f"  {str(verdict):5} {'  ' if verdict else '<-MISS'}  {c!r}")

print("\nBaseline positives (must stay True):")
for c in MUST_STAY_TRUE:
    print(f"  {str(_is_broad_git_mutation(c)):5}  {c!r}")

print("\nBaseline negatives (must stay False):")
for c in MUST_STAY_FALSE:
    print(f"  {str(_is_broad_git_mutation(c)):5}  {c!r}")

if missed or false_pos or false_neg:
    print(f"\nFAIL: {len(missed)} missed mutation(s); "
          f"{len(false_pos)} false-positive(s); {len(false_neg)} regressed baseline(s).")
    sys.exit(1)

print("\nPASS: every compound/chained git mutation is detected; baselines intact.")
sys.exit(0)
