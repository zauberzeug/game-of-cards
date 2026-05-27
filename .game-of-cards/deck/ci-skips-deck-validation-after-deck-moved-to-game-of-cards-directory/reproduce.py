"""Reproduce: CI's `if [ -d deck ]` guard skips validation on the real deck.

The canonical deck moved to `.game-of-cards/deck/` (commit 9fa3a24), but
`.github/workflows/ci.yml` still guards its `goc validate` step on the legacy
root `deck/` path. This script confirms the guard evaluates False against the
current tree, so CI never validates the real deck.

Exits 0 once the CI workflow's deck-validate guard would resolve to the
canonical deck directory (the defect no longer fires); exits 1 while CI still
guards solely on the legacy root `deck/` path.
"""

import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


def main() -> int:
    root = _repo_root()
    legacy = root / "deck"
    canonical = root / ".game-of-cards" / "deck"

    legacy_exists = legacy.is_dir()
    canonical_exists = canonical.is_dir()
    card_count = (
        sum(1 for c in canonical.iterdir() if (c / "README.md").is_file())
        if canonical_exists
        else 0
    )

    # The CI guard as written today: `if [ -d deck ]`.
    ci_guard_passes = legacy_exists

    print(f"legacy root deck/ exists:          {legacy_exists}")
    print(
        f"canonical .game-of-cards/deck/:    {canonical_exists}"
        + (f" ({card_count} cards)" if canonical_exists else "")
    )
    print(
        f"CI guard `[ -d deck ]` evaluates:  {ci_guard_passes}  "
        + ("-> CI RUNS `goc validate`" if ci_guard_passes else "-> CI SKIPS `goc validate`")
    )

    # Inspect the actual workflow file to decide pass/fail.
    ci = root / ".github" / "workflows" / "ci.yml"
    ci_text = ci.read_text(encoding="utf-8") if ci.is_file() else ""
    guards_canonical = bool(
        re.search(r"-d\s+\.game-of-cards/deck", ci_text)
    )

    if canonical_exists and not guards_canonical:
        print("RESULT: DEFECT — CI never validates the real deck")
        return 1

    print("RESULT: OK — CI deck-validate guard resolves to the canonical deck")
    return 0


if __name__ == "__main__":
    sys.exit(main())
