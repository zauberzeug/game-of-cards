"""Reproduce: AGENTS.md calls `.claude/settings.json` a per-repo permission
allow-list, but goc never writes permissions there — it merges hook
registrations into it.

Four checks, all read-only:

1. AGENTS.md's dogfood-sync paragraph labels `.claude/settings.json` a
   "project-specific permission allow-list" and groups it with the
   user-owned `.game-of-cards/` content stubs.
2. `goc/install.py` + `goc/engine.py` contain ZERO occurrences of
   `permissions` — goc neither reads nor writes that key.
3. This repo's own `.claude/settings.json` carries no `permissions` key,
   only `hooks` — and every registered command matches an entry in
   `GOC_CLAUDE_HOOKS`, i.e. goc wrote them.
4. `_merge_claude_settings` / the plugin-mode cleanup in `goc/install.py`
   both operate on `GOC_CLAUDE_HOOKS` against that file, so it is a
   goc-managed merge target rather than a hands-off per-repo file.

Exits non-zero while the mislabel stands; zero once AGENTS.md describes
the file as the hook-registration manifest it is.

    uv run python .game-of-cards/deck/<this-card>/reproduce.py
"""

from __future__ import annotations

import json
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
sys.path.insert(0, str(ROOT))

from goc.install import GOC_CLAUDE_HOOKS  # noqa: E402

failures: list[str] = []

# --- 1. The claim in AGENTS.md -------------------------------------------
agents_md = (ROOT / "AGENTS.md").read_text()
# Collapse wrapping so the check does not depend on where the line breaks.
flat = re.sub(r"\s+", " ", agents_md)
MISLABEL = "`.claude/settings.json` (project-specific permission allow-list)"
print("=== 1. AGENTS.md claim ===")
if MISLABEL in flat:
    line = next(
        i for i, ln in enumerate(agents_md.splitlines(), 1)
        if "project-specific permission" in ln
    )
    print(f"AGENTS.md:{line}: {MISLABEL}")
    print("  ...grouped with the user-owned `.game-of-cards/` content stubs as")
    print('  "NOT in the auto-sync — they\'re meant to be customized per repo".')
    failures.append("AGENTS.md still calls settings.json a permission allow-list")
else:
    print("claim absent — AGENTS.md no longer mislabels the file")

# --- 2. goc never touches a `permissions` key ----------------------------
print("\n=== 2. `permissions` occurrences in the engine ===")
for rel in ("goc/install.py", "goc/engine.py"):
    n = len(re.findall(r"permissions", (ROOT / rel).read_text()))
    print(f"{rel}: {n}")
    if n:
        failures.append(f"{rel} unexpectedly references `permissions`")

# --- 3. What this repo's settings.json actually contains -----------------
print("\n=== 3. .claude/settings.json contents ===")
settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
print(f"top-level keys: {sorted(settings)}")
print(f"has `permissions`: {'permissions' in settings}")
goc_commands = set(GOC_CLAUDE_HOOKS.values())
registered = [
    hook.get("command", "")
    for groups in settings.get("hooks", {}).values()
    for group in groups
    for hook in group.get("hooks", [])
]
print(f"registered hook commands: {len(registered)}")
for cmd in registered:
    tail = cmd.split("/")[-1]
    owned = any(tail == g.split("/")[-1] for g in goc_commands)
    print(f"  {tail:38s} in GOC_CLAUDE_HOOKS: {owned}")
    if not owned:
        failures.append(f"unexpected non-GoC hook registration: {tail}")

# --- 4. goc manages that file via GOC_CLAUDE_HOOKS -----------------------
print("\n=== 4. goc/install.py sites that write/strip GoC hook entries ===")
install_src = (ROOT / "goc" / "install.py").read_text().splitlines()
sites = [
    (i, ln.strip())
    for i, ln in enumerate(install_src, 1)
    if "GOC_CLAUDE_HOOKS" in ln and not ln.strip().startswith("#")
]
for i, ln in sites:
    print(f"goc/install.py:{i}: {ln}")
print(f"\nevents registered by goc: {sorted(GOC_CLAUDE_HOOKS)}")

print("\n=== verdict ===")
if failures:
    for f in failures:
        print(f"FAIL: {f}")
    print(
        "\nThe file is goc's Claude Code hook-registration manifest — a merge\n"
        "target install/upgrade write into and plugin-mode cleanup strips — not\n"
        "a per-repo permission allow-list. AGENTS.md's ownership paragraph\n"
        "misdescribes both what the file holds and who owns it."
    )
    sys.exit(1)
print("PASS: AGENTS.md describes .claude/settings.json accurately")
