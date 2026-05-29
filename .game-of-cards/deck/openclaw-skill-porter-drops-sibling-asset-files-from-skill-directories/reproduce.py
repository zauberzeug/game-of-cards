"""Demonstrate that the OpenClaw skill porter and its drift guard ignore sibling
asset files.

Walks every skill dir under `goc/templates/skills/` (excluding host-specific
complements that the porter intentionally skips) and lists, per dir, every file
other than `SKILL.md` that is missing from `openclaw-plugin/skills/<name>/`.
Then invokes `drifted_skills()` and asserts it returns the empty list — proving
the drift guard does not report the missing siblings as drift.

Today this prints at least one missing path (`card-schema/schema.yaml`) while
`drifted_skills()` reports nothing. After the fix, both will be silent.

Run with:
    uv run python .game-of-cards/deck/openclaw-skill-porter-drops-sibling-asset-files-from-skill-directories/reproduce.py
"""

from __future__ import annotations

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

SRC_DIR = ROOT / "goc" / "templates" / "skills"
DST_DIR = ROOT / "openclaw-plugin" / "skills"
HOST_PREFIXES = ("claude-", "codex-")


def _portable_skill_dirs() -> list[Path]:
    return [
        d
        for d in sorted(SRC_DIR.iterdir())
        if d.is_dir()
        and not any(d.name.startswith(p) for p in HOST_PREFIXES)
        and (d / "SKILL.md").is_file()
    ]


def main() -> int:
    missing: list[str] = []
    for skill_dir in _portable_skill_dirs():
        for asset in sorted(skill_dir.rglob("*")):
            if asset.is_dir() or asset.name == "SKILL.md":
                continue
            if "__pycache__" in asset.parts:
                continue
            rel = asset.relative_to(SRC_DIR)
            dst = DST_DIR / rel
            if not dst.is_file():
                missing.append(str(rel))

    if missing:
        print(
            f"openclaw-plugin missing {len(missing)} file(s) present in goc/templates: "
            + ", ".join(missing)
        )
    else:
        print("openclaw-plugin has every sibling asset goc/templates ships.")

    import port_skills_to_openclaw as porter

    drifted = porter.drifted_skills()
    drift_rel = [p.relative_to(ROOT) for p in drifted]
    print(f"drifted_skills() reports: {drift_rel}   # CI guard sees nothing wrong"
          if not drifted
          else f"drifted_skills() reports: {drift_rel}")

    if missing and not drifted:
        print("DEFECT: sibling assets are missing AND the drift guard is silent.")
        return 0
    if not missing:
        print("OK: porter copied every sibling.")
        return 0
    print("PARTIAL: drift guard caught it but missing sibling(s) remain.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
