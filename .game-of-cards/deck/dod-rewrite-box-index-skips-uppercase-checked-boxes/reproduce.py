"""Reproduce: _apply_dod_rewrite indexes DoD boxes with a case-sensitive
regex (`- \\[[ x]\\]`, lowercase `x` only), while the canonical counter
DOD_DONE_BOX is IGNORECASE. On a DoD whose first box is uppercase `- [X]`,
box_indices skips it, so the 0-based index space the LLM verdict targets
(item 0 = `[X] alpha`, item 1 = `[ ] beta`) is misaligned: a fix for idx 1
lands on the wrong physical line, and idx 0 is unreachable.

Exit 0 == box_indices agrees with the canonical counters AND an idx:1
          rewrite lands on the `beta` line (defect fixed).
Exit 1 == the regexes disagree and the rewrite misfires (defect fires).
"""
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


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

# DoD with an uppercase checked box first, an open box second.
DOD = "- [X] alpha\n- [ ] beta\n"

failures = 0

with tempfile.TemporaryDirectory() as d:
    card_dir = Path(d)
    readme = card_dir / "README.md"
    readme.write_text(
        engine.emit_frontmatter(
            {
                "title": "fixture",
                "summary": "s",
                "status": "open",
                "definition_of_done": DOD,
            },
            body="# fixture\n",
        )
    )
    card = engine.load_card(card_dir)

    # 1) The rewriter's box_indices must agree with the canonical
    #    (case-insensitive) box count used everywhere else in the engine.
    lines = DOD.splitlines()
    box_indices = engine._dod_box_indices(lines)
    n_canonical = len(engine.DOD_OPEN_BOX.findall(DOD)) + len(engine.DOD_DONE_BOX.findall(DOD))
    print(f"canonical box count (open+done, IGNORECASE): {n_canonical}")
    print(f"box_indices length (rewriter's view):        {len(box_indices)}")
    if len(box_indices) != n_canonical:
        failures += 1
        print("DEFECT: rewriter's box_indices disagrees with the canonical counter")
    else:
        print("OK: box counts agree")

    # 2) An idx:1 rewrite must land on the `beta` line, not misfire.
    engine._apply_dod_rewrite(card, [{"idx": 1, "fix": "- [ ] beta REWRITTEN"}])
    fm, _ = engine.parse_frontmatter(readme.read_text())
    result = fm.get("definition_of_done") or ""
    print("\nafter rewrite of idx 1:")
    print(result)
    alpha_intact = "alpha" in result and "alpha REWRITTEN" not in result
    beta_rewritten = "beta REWRITTEN" in result
    if not (alpha_intact and beta_rewritten):
        failures += 1
        print("DEFECT: idx:1 rewrite did not land cleanly on the `beta` box")
    else:
        print("OK: idx:1 rewrite landed on `beta`, `alpha` untouched")

print()
if failures:
    print(f"DEFECT: {failures} check(s) failed — uppercase box index misalignment")
    sys.exit(1)
print("OK: box indexing reconciled; uppercase `[X]` boxes are addressable")
sys.exit(0)
