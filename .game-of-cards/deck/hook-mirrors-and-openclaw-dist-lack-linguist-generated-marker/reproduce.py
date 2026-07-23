#!/usr/bin/env python3
"""Check `.gitattributes` linguist-generated coverage of every auto-synced tree.

Enumerates the machine-written destinations straight from
`scripts/sync_plugin_assets.py`'s SYNC_PAIRS (plus the codex skill trees it
syncs via specialized functions, plus the committed esbuild output at
`openclaw-plugin/dist/`), then asks git for the effective
`linguist-generated` attribute of every tracked file inside them.

Invariant (the .gitattributes header's stated intent — "reviewers see the
authored change once instead of N times across the mirrors"): a tracked
file inside these trees is marked `linguist-generated=true` unless it is
one of the known *authored* files that merely live inside a synced dir
(`hooks.json` twins, the repo-local `tune-cadence` dev skill) — those must
NOT be marked, or authored changes would be collapsed in review.

Exits 0 in both states, printing PASS/FAIL per file class; exits 1 only if
git itself is unusable. The defect is present iff any GENERATED file
prints `unspecified` or any AUTHORED file prints `true`.
"""

import importlib.util
import subprocess
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
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location(
    "_goc_sync_assets", ROOT / "scripts" / "sync_plugin_assets.py"
)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

# Machine-written trees: dir-sync destinations + codex skill trees (synced by
# specialized functions, not pairs) + the committed esbuild bundle.
generated_dirs = sorted(
    {dst for _, dst, _, _ in sync.SYNC_PAIRS if dst.is_dir()}
    | {ROOT / "codex-plugin" / "skills", ROOT / ".codex" / "skills"}
    | {ROOT / "openclaw-plugin" / "dist"}
)

# Authored files that live inside synced dirs (protected via preserve_files
# or repo-local): collapsing THEIR diffs would hide real authored changes.
authored = {
    ROOT / "claude-plugin" / "hooks" / "hooks.json",
    ROOT / "codex-plugin" / "hooks" / "hooks.json",
    ROOT / ".claude" / "skills" / "tune-cadence" / "SKILL.md",
}


def tracked(d: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--", str(d)], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    return [ROOT / line for line in out]


def attr(paths: list[Path]) -> dict[Path, str]:
    rels = [str(p.relative_to(ROOT)) for p in paths]
    out = subprocess.run(
        ["git", "check-attr", "linguist-generated", "--", *rels],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    result = {}
    for line in out:
        path, _, value = (part.strip() for part in line.rsplit(":", 2))
        result[ROOT / path] = value
    return result


unmarked_generated: list[Path] = []
collapsed_authored: list[Path] = []
for d in generated_dirs:
    files = tracked(d)
    if not files:
        continue
    values = attr(files)
    bad = sorted(p for p, v in values.items() if p not in authored and v != "true")
    unmarked_generated += bad
    collapsed_authored += sorted(p for p, v in values.items() if p in authored and v == "true")
    marker = "OK  " if not bad else "MISS"
    print(f"{marker} {d.relative_to(ROOT)}: {len(files) - len(bad)}/{len(files)} marked generated")

for p in unmarked_generated:
    print(f"  unmarked generated file: {p.relative_to(ROOT)}")
for p in collapsed_authored:
    print(f"  authored file collapsed as generated: {p.relative_to(ROOT)}")

if unmarked_generated or collapsed_authored:
    print(
        f"DEFECT PRESENT: {len(unmarked_generated)} generated file(s) unmarked, "
        f"{len(collapsed_authored)} authored file(s) wrongly collapsed"
    )
else:
    print("DEFECT ABSENT: every auto-synced tree is marked, every authored file exempted")
