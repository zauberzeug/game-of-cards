#!/usr/bin/env python3
"""Prove that goc.md's plugin sections contradict the shipped payload.

Each check reads a claim out of `goc.md` and compares it against the tree the
claim describes. Offline; no network, no git, no goc invocation.

Run:  uv run python .game-of-cards/deck/cli-reference-plugin-sections-describe-a-payload-goc-no-longer-ships/reproduce.py
"""

from __future__ import annotations

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


ROOT = _repo_root()
GOC_MD = (ROOT / "goc.md").read_text()

failures: list[str] = []


def check(label: str, claim_ok: bool, detail: str) -> None:
    verdict = "ok" if claim_ok else "FAIL"
    print(f"[{verdict}] {label}\n       {detail}")
    if not claim_ok:
        failures.append(label)


def _skill_dirs(rel: str) -> list[str]:
    return sorted(p.name for p in (ROOT / rel).iterdir() if p.is_dir())


# ---------------------------------------------------------------- claim 1
# goc.md: "Skills and hook scripts are **symlinks** into `goc/templates/`"
symlinks = sorted(
    str(p.relative_to(ROOT))
    for base in ("claude-plugin/skills", "claude-plugin/hooks")
    for p in (ROOT / base).rglob("*")
    if p.is_symlink()
)
claims_symlinks = "**symlinks** into `goc/templates/`" in GOC_MD
check(
    "claim 1 — plugin payload assets are symlinks",
    not claims_symlinks,
    f"goc.md asserts symlinks: {claims_symlinks}; actual symlinks under "
    f"claude-plugin/{{skills,hooks}}: {len(symlinks)} {symlinks}",
)

# ---------------------------------------------------------------- claim 2
# goc.md: "**11 GoC skills** (same as `goc install --agents claude`)"
claude_skills = _skill_dirs("claude-plugin/skills")
m = re.search(r"\*\*(\d+) GoC skills\*\* \(same as `goc install --agents claude`\)", GOC_MD)
claimed_claude = int(m.group(1)) if m else -1
check(
    "claim 2 — Claude plugin skill count",
    claimed_claude == len(claude_skills),
    f"goc.md claims {claimed_claude}; claude-plugin/skills/ has {len(claude_skills)}",
)

# ---------------------------------------------------------------- claim 3
# goc.md: "**13 GoC skills** ... (the `kickoff` skill is deferred ...)"
openclaw_skills = _skill_dirs("openclaw-plugin/skills")
m = re.search(r"\*\*(\d+) GoC skills\*\* as workspace-tier", GOC_MD)
claimed_openclaw = int(m.group(1)) if m else -1
kickoff_deferred = "the `kickoff` skill is deferred" in GOC_MD
kickoff_shipped = "kickoff" in openclaw_skills
check(
    "claim 3 — OpenClaw plugin skill count",
    claimed_openclaw == len(openclaw_skills),
    f"goc.md claims {claimed_openclaw}; openclaw-plugin/skills/ has {len(openclaw_skills)}",
)
check(
    "claim 4 — OpenClaw port defers the kickoff skill",
    not (kickoff_deferred and kickoff_shipped),
    f"goc.md says kickoff is deferred: {kickoff_deferred}; "
    f"openclaw-plugin/skills/kickoff exists: {kickoff_shipped}",
)

# ---------------------------------------------------------------- claim 5
# goc.md Claude "### Prerequisites": "The plugin shells to the `goc` CLI;
# install it first" — but claude-plugin/bin/goc runs the bundled engine.
prereq = GOC_MD[GOC_MD.index("### Prerequisites") : GOC_MD.index("### Install from the marketplace")]
demands_cli_install = "install it first" in prereq
wrapper = (ROOT / "claude-plugin" / "bin" / "goc").read_text()
bundles_engine = "python3 -m goc.cli" in wrapper or "-m goc.cli" in wrapper
vendored_engine = (ROOT / "claude-plugin" / "goc" / "engine.py").exists()
check(
    "claim 5 — Claude plugin requires a separate goc CLI install",
    not (demands_cli_install and bundles_engine and vendored_engine),
    f"goc.md demands a prior CLI install: {demands_cli_install}; "
    f"bin/goc runs the bundled engine: {bundles_engine}; "
    f"claude-plugin/goc/engine.py vendored: {vendored_engine}",
)

# ---------------------------------------------------------------- claim 6
# goc.md: unguarded bootstrap injection "produces an error message instead of
# card data" + "A future release will fix the bootstrap path to use
# `${CLAUDE_SKILL_DIR}`". Both are stale: every fence is `[ -f ]`-guarded with
# a bare-`goc` fallback, and CLAUDE_SKILL_DIR appears nowhere in the tree.
promises_skill_dir_fix = "CLAUDE_SKILL_DIR" in GOC_MD
skill_dir_used = any(
    "CLAUDE_SKILL_DIR" in p.read_text()
    for p in (ROOT / "goc" / "templates" / "skills").rglob("SKILL.md")
)
fences = [
    line
    for p in sorted((ROOT / "goc" / "templates" / "skills").rglob("SKILL.md"))
    for line in p.read_text().splitlines()
    # Only real injection fences, not prose that mentions the wrapper path.
    if line.lstrip().startswith("!`") and "_goc-bootstrap.sh" in line
]
unguarded = [
    f for f in fences if "if [ -f $b ]" not in f or not re.search(r"else\s+goc\b", f)
]
check(
    "claim 6 — bootstrap injection is unguarded, awaiting a CLAUDE_SKILL_DIR fix",
    not (promises_skill_dir_fix and not skill_dir_used and not unguarded),
    f"goc.md promises a CLAUDE_SKILL_DIR rewrite: {promises_skill_dir_fix}; "
    f"CLAUDE_SKILL_DIR used in any shipped skill: {skill_dir_used}; "
    f"bootstrap fences: {len(fences)}, unguarded: {len(unguarded)}",
)

print()
if failures:
    print(f"{len(failures)} stale claim(s) in goc.md: {failures}")
    sys.exit(1)
print("goc.md plugin sections agree with the shipped payload.")
