#!/usr/bin/env python3
"""Reproduce: the Claude agent manifest declares a `guidance` block,
`_load_agent_shim` builds it into `AgentShim.guidance`, but no consumer
ever reads that attribute. The briefing flow uses hardcoded module
constants instead.

Exits non-zero (defect present) when:
  - the manifest declares a non-empty `guidance` array, AND
  - `AgentShim.guidance` carries non-empty data, AND
  - no read site for `.guidance` on an `AgentShim` instance exists in
    the source tree.

Exits zero (defect fixed) when either fix lands:
  - Option A: the schema field is gone — manifest no longer declares
    `guidance`, and `AgentShim` has no `guidance` attribute.
  - Option B: the field is wired up — at least one read site exists.
"""

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

from goc.install import _load_agent_shim  # noqa: E402

templates = ROOT / "goc" / "templates"

claude_manifest = json.loads(
    (templates / "agents" / "claude" / "manifest.json").read_text()
)
codex_manifest = json.loads(
    (templates / "agents" / "codex" / "manifest.json").read_text()
)
print(f"claude manifest['guidance']: {claude_manifest.get('guidance')!r}")
print(f"codex  manifest['guidance']: {codex_manifest.get('guidance')!r}")
print()

claude_shim = _load_agent_shim(templates, "claude")
codex_shim = _load_agent_shim(templates, "codex")
claude_guidance = getattr(claude_shim, "guidance", None)
codex_guidance = getattr(codex_shim, "guidance", None)
print(f"claude AgentShim.guidance: {claude_guidance!r}")
print(f"codex  AgentShim.guidance: {codex_guidance!r}")
print()

# Search source tree for read sites of `.guidance` on AgentShim instances,
# excluding the two write sites (field declaration + kwarg at construction).
read_pattern = re.compile(r"\.guidance\b")
write_site_substrings = (
    "guidance: tuple",  # field declaration in AgentShim
    "guidance=guidance",  # kwarg at construction
)

search_roots = [ROOT / "goc", ROOT / "tests", ROOT / "scripts"]
read_hits = []
for root in search_roots:
    if not root.exists():
        continue
    for path in root.rglob("*.py"):
        rel = path.relative_to(ROOT)
        # Skip mirror trees under plugin payloads.
        parts = rel.parts
        if "claude-plugin" in parts or "codex-plugin" in parts or "openclaw-plugin" in parts:
            continue
        try:
            text = path.read_text()
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if not read_pattern.search(line):
                continue
            if any(sig in line for sig in write_site_substrings):
                continue
            if "GuidanceBlock" in line:
                continue
            # Heuristically skip the build loop ("for guidance_spec in raw.get(...)")
            # and the assignment "guidance = tuple(..." which are write sites.
            if line.lstrip().startswith(("guidance =", "for guidance_spec")):
                continue
            read_hits.append((str(rel), lineno, line.strip()))

print(f"Source-tree read sites of `.guidance` on AgentShim: {len(read_hits)}")
for site in read_hits:
    print(f"  {site}")
print()

# Hardcoded constant reads — the actual briefing flow.
install_text = (ROOT / "goc" / "install.py").read_text()
const_reads = re.findall(
    r"AGENTS_GUIDANCE\.\w+|CLAUDE_GUIDANCE\.\w+", install_text
)
print(f"Hardcoded module-constant reads in install.py: {len(const_reads)}")
for hit in const_reads:
    print(f"  {hit}")
print()

# Verdict.
manifest_declares = bool(claude_manifest.get("guidance"))
shim_field_populated = bool(claude_guidance)
defect_present = manifest_declares and shim_field_populated and not read_hits

if defect_present:
    print(
        "VERDICT: defect confirmed — the manifest's `guidance` block is "
        "built into AgentShim.guidance but never read; the briefing flow "
        "uses hardcoded constants instead."
    )
    sys.exit(1)

if not manifest_declares and claude_guidance in (None, ()):
    print("VERDICT: defect fixed via Option A (schema removed).")
elif read_hits:
    print("VERDICT: defect fixed via Option B (field is now consumed).")
else:
    print("VERDICT: defect not reproduced — schema and consumers are consistent.")
sys.exit(0)
