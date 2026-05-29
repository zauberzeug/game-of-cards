"""Reproduce: next-card SKILL.md documents an `impact:` frontmatter field that
the schema does not define. The real field is `contribution`.

Exit code 0 means the defect is FIXED (no `impact: <level>` field-name drift
remains in next-card/pull-card SKILL bodies). Exit code 1 means the defect is
LIVE.
"""

import re
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


REPO = _repo_root()
sys.path.insert(0, str(REPO))

from goc import engine  # noqa: E402


def main() -> int:
    schema = engine.load_schema()
    schema_text = (REPO / "goc" / "schema.yaml").read_text()

    print("schema known fields:")
    print(f"  required: {schema.required_fields}")
    print(f"  optional: {schema.optional_fields}")
    print(f"  contribution_values: {schema.contribution_values}")
    has_impact_in_schema = re.search(r"\bimpact\b", schema_text) is not None
    print(f"  has 'impact' anywhere in schema.yaml? {has_impact_in_schema}")
    print()

    nc_path = REPO / "goc" / "templates" / "skills" / "next-card" / "SKILL.md"
    nc_lines = nc_path.read_text().splitlines()
    pat = re.compile(r"`impact:\s*(high|medium|low)`")
    nc_hits = [
        (i + 1, ln) for i, ln in enumerate(nc_lines) if pat.search(ln)
    ]
    print("next-card SKILL.md occurrences of 'impact: <level>' (drift):")
    for n, ln in nc_hits:
        print(f"  L{n}:   {ln.strip()}")
    print()

    pc_path = REPO / "goc" / "templates" / "skills" / "pull-card" / "SKILL.md"
    pc_lines = pc_path.read_text().splitlines()
    pc_pat = re.compile(r"impact:\s*(high|medium|low)")
    pc_hits = [
        (i + 1, ln) for i, ln in enumerate(pc_lines) if pc_pat.search(ln)
    ]
    print("pull-card SKILL.md occurrences of 'impact:<level>' (propagated example):")
    for n, ln in pc_hits:
        print(f"  L{n}:   {ln.strip()}")
    print()

    # Stage two scratch cards in a tmp deck and validate them.
    with tempfile.TemporaryDirectory() as td:
        deck = Path(td)

        # Card A: impact: high, no contribution.
        a = deck / "probe-impact-field-card"
        a.mkdir()
        (a / "README.md").write_text(
            "---\n"
            "title: probe-impact-field-card\n"
            "summary: \"\"\n"
            "status: open\n"
            "stage: null\n"
            "impact: high\n"  # the wrong field the next-card skill teaches
            "created: \"2026-05-29\"\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [ ] (placeholder)\n"
            "---\n"
            "\n# probe-impact-field-card\n"
        )
        (a / "log.md").write_text("")

        cards_a = [c for c in (engine.load_card(d) for d in sorted(deck.iterdir()) if d.is_dir()) if c is not None]
        titles_a = {c.title for c in cards_a}
        errs_a: list[str] = []
        for c in cards_a:
            errs_a.extend(engine.validate_card(c, schema, titles_a))
        print("card filed with impact: high and no contribution:")
        print(f"  validate errors: {errs_a}")
        print()

        # Card B: both impact and contribution.
        b = deck / "probe-both-fields-card"
        b.mkdir()
        (b / "README.md").write_text(
            "---\n"
            "title: probe-both-fields-card\n"
            "summary: \"\"\n"
            "status: open\n"
            "stage: null\n"
            "impact: high\n"  # silently accepted unknown field
            "contribution: high\n"
            "created: \"2026-05-29\"\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [ ] (placeholder)\n"
            "---\n"
            "\n# probe-both-fields-card\n"
        )
        (b / "log.md").write_text("")

        # Reload only card B (drop card A so its missing-contribution doesn't
        # also fire here).
        import shutil
        shutil.rmtree(a)
        cards_b = [c for c in (engine.load_card(d) for d in sorted(deck.iterdir()) if d.is_dir()) if c is not None]
        titles_b = {c.title for c in cards_b}
        b_errs = [
            e
            for c in cards_b
            if c.title == "probe-both-fields-card"
            for e in engine.validate_card(c, schema, titles_b)
        ]
        b_card = next(c for c in cards_b if c.title == "probe-both-fields-card")
        own_rank = engine.CONTRIBUTION_RANK.get(b_card.contribution, 0.0)
        print("card filed with BOTH impact: high AND contribution: high:")
        print(f"  validate errors (clean): {b_errs == []}")
        print(f"  computed value uses contribution=high (rank {own_rank}): {own_rank == 9.0}")
        print("  the impact field is silently accepted dead weight.")
        print()

    if nc_hits:
        print(
            f"FAIL: next-card SKILL.md documents {len(nc_hits)} `impact:` field-name "
            "occurrences but the schema has no `impact` field."
        )
        return 1

    print(
        "PASS: next-card SKILL.md no longer documents an `impact:` field — the "
        "drift is fixed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
