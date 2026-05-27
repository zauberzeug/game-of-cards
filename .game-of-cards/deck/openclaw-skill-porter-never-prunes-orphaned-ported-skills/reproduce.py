"""Reproduce: the OpenClaw skill porter never prunes orphaned ported skills.

`drifted_skills()` and the re-port pass in scripts/port_skills_to_openclaw.py
iterate only source skill dirs (goc/templates/skills/). A ported skill dir
under openclaw-plugin/skills/ that has no source counterpart (orphan, e.g.
after a source skill rename/delete) is invisible to both — `--check` stays
green and a re-port never removes it.

This script creates a synthetic orphan, exercises the porter, then cleans up.
It never mutates a committed ported skill. Exits 0 when the porter is
orphan-aware (flags + prunes), 1 when the defect is present.
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT / "scripts"))

import port_skills_to_openclaw as porter  # noqa: E402

ORPHAN_NAME = "zzz-audit-probe-orphan"


def main() -> int:
    orphan_dir = porter.DST_DIR / ORPHAN_NAME
    orphan_skill = orphan_dir / "SKILL.md"

    # Precondition: name must not collide with a real source skill.
    source_names = {d.name for d in porter._portable_skill_dirs()}
    assert ORPHAN_NAME not in source_names, "probe name unexpectedly matches a source skill"

    orphan_dir.mkdir(parents=True, exist_ok=True)
    orphan_skill.write_text("---\nname: orphan\n---\n# orphan\n", encoding="utf-8")
    try:
        flagged = any(ORPHAN_NAME in str(p) for p in porter.drifted_skills())

        porter.main([])  # full re-port (no --check)
        still_present = orphan_skill.exists()
    finally:
        # Clean up the synthetic orphan regardless of outcome.
        if orphan_skill.exists():
            orphan_skill.unlink()
        if orphan_dir.exists():
            try:
                orphan_dir.rmdir()
            except OSError:
                pass

    print(f"drifted_skills() flags orphan? {flagged}")
    print(f"orphan still present after re-port? {still_present}")

    failures = []
    if not flagged:
        failures.append("drifted_skills() did not flag the orphan (expected: flagged)")
    if still_present:
        failures.append("re-port did not prune the orphan (expected: removed)")

    if failures:
        print("\nDEFECT PRESENT — porter is orphan-blind:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("\nOK — porter flags and prunes orphaned ported skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
