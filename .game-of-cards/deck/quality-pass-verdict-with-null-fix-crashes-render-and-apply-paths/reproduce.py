"""A `goc quality-pass --llm` verdict whose dod_issues entry carries
`"fix": null` (or any non-string) crashes both duplicated fixable-
predicate sites with a raw AttributeError — after the expensive LLM
subprocess already succeeded.
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

VERDICT = {
    "title": "some-card",
    "title_verdict": {"ok": True},
    "summary_verdict": {"ok": True},
    "dod_issues": [{"idx": 0, "issue": "not verifiable as written", "fix": None}],
}

crashes = 0

try:
    engine._render_verdict(VERDICT)
    print("_render_verdict: no crash (defect no longer fires)")
except AttributeError as exc:
    crashes += 1
    print(f"_render_verdict: AttributeError: {exc}")

CARD_TEXT = """---
title: some-card
status: open
definition_of_done: |
  - [ ] TDD: original item
---

# some-card
"""

with tempfile.TemporaryDirectory() as td:
    card_dir = Path(td) / "some-card"
    card_dir.mkdir()
    (card_dir / "README.md").write_text(CARD_TEXT)
    card = engine.load_card(card_dir)
    try:
        engine._apply_dod_rewrite(card, VERDICT["dod_issues"])
        print("_apply_dod_rewrite: no crash (defect no longer fires)")
    except AttributeError as exc:
        crashes += 1
        print(f"_apply_dod_rewrite: AttributeError: {exc}")

if crashes:
    print(f"\n[FAIL] {crashes}/2 sites crash on a null `fix` the prompt "
          "contract never forbids; the _cmd_quality_pass try/except wraps "
          "only the subprocess call, so this escapes as a traceback.")
    sys.exit(0)
print("\n[NO-REPRO] both sites tolerate non-string fix values.")
sys.exit(1)
