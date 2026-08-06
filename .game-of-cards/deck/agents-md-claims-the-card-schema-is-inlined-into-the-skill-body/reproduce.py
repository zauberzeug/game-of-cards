"""Prove AGENTS.md misdescribes how `goc/schema.yaml` reaches installed skills.

The `## Code architecture` bullet claims the schema is "inlined into the
`card-schema` skill body at install time". Four independent surfaces say
otherwise; this script checks each and exits non-zero while the claim stands.

Run: uv run python .game-of-cards/deck/agents-md-claims-the-card-schema-is-inlined-into-the-skill-body/reproduce.py
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
sys.path.insert(0, str(ROOT))

from goc.install import _iter_skill_assets  # noqa: E402

STALE_CLAIM = "inlined into the `card-schema`"
# Every top-level key of goc/schema.yaml. If the schema were inlined into the
# skill body, SKILL.md would carry these.
SCHEMA_KEYS = (
    "schema_version",
    "required_fields",
    "optional_fields",
    "title_pattern",
    "status_values",
    "canonical_tags",
)

engine_schema = ROOT / "goc" / "schema.yaml"
template_schema = ROOT / "goc" / "templates" / "skills" / "card-schema" / "schema.yaml"
skill_body = ROOT / "goc" / "templates" / "skills" / "card-schema" / "SKILL.md"
agents_md = ROOT / "AGENTS.md"

failures: list[str] = []

# 1. The claim is live in AGENTS.md.
agents_text = agents_md.read_text()
claim_lines = [
    i for i, line in enumerate(agents_text.splitlines(), 1) if STALE_CLAIM in line
]
print(f"[1] AGENTS.md lines asserting {STALE_CLAIM!r}: {claim_lines}")
if claim_lines:
    failures.append("AGENTS.md still claims the schema is inlined into the skill body")

# 2. `goc install` plans a *sibling file* write, not a body substitution.
assets = [str(p) for p in _iter_skill_assets(ROOT / "goc" / "templates" / "skills", "claude")]
sibling = "card-schema/schema.yaml"
print(f"[2] `_iter_skill_assets` plans a verbatim copy of {sibling!r}: {sibling in assets}")
if sibling not in assets:
    failures.append("install no longer copies the sibling schema — re-derive this card")

# 3. The skill body carries none of the schema's keys — nothing is inlined.
body = skill_body.read_text()
present = [k for k in SCHEMA_KEYS if k in body]
print(f"[3] schema keys found inside card-schema/SKILL.md: {present or 'none'}")
if present:
    failures.append("SKILL.md does contain schema keys — the claim may be accurate")

# 4. The skill body names the real mechanism, contradicting AGENTS.md.
sibling_sentence = "ships as the sibling `schema.yaml`"
print(f"[4] SKILL.md says {sibling_sentence!r}: {sibling_sentence in body}")

# 5. AGENTS.md contradicts itself: the porter paragraph calls it a verbatim copy.
verbatim_lines = [
    i
    for i, line in enumerate(agents_text.splitlines(), 1)
    if "card-schema/schema.yaml" in line
]
print(f"[5] AGENTS.md lines calling the same file a sibling verbatim copy: {verbatim_lines}")

# 6. No script syncs goc/schema.yaml into the template copy — the duplication is
#    hand-maintained and only caught after the fact by a test.
sync_text = (ROOT / "scripts" / "sync_plugin_assets.py").read_text()
print(f"[6] scripts/sync_plugin_assets.py mentions schema.yaml: {'schema.yaml' in sync_text}")
print(
    f"[6] goc/schema.yaml and the template copy are byte-identical today: "
    f"{engine_schema.read_bytes() == template_schema.read_bytes()}"
)

print()
if failures:
    for f in failures:
        print(f"FAIL: {f}")
    sys.exit(1)
print("PASS: AGENTS.md describes the sibling-copy mechanism accurately.")
