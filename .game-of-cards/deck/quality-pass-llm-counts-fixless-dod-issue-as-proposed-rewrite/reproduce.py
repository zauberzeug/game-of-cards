#!/usr/bin/env python3
"""Reproduce: _render_verdict counts a fixless DoD issue as a proposed rewrite.

A verdict with an OK title/summary and a single DoD issue that carries no
`fix` string returns has_rewrite == True, even though _apply_dod_rewrite
(which keys on `"idx" in issue and "fix" in issue`) would write nothing.

Buggy engine prints:  has_rewrite=True  applicable_fixes=0  -> OVER-COUNT
Fixed engine prints:  has_rewrite=False applicable_fixes=0  -> aligned
"""
import io
from contextlib import redirect_stdout

from goc.engine import _render_verdict

VERDICT = {
    "title": "some-card",
    "title_verdict": {"ok": True},
    "summary_verdict": {"ok": True},
    "dod_issues": [{"idx": 0, "issue": "this item is vague"}],  # no "fix"
}

# What the apply path (_apply_dod_rewrite) would actually write:
applicable_fixes = sum(
    1 for issue in VERDICT["dod_issues"] if "idx" in issue and "fix" in issue
)

buf = io.StringIO()
with redirect_stdout(buf):
    has_rewrite = _render_verdict(VERDICT)
rendered = buf.getvalue()

print(f"has_rewrite={has_rewrite}")
print(f"applicable_fixes={applicable_fixes}")
print(f"bogus 'fix: ?' advertised={'fix: ?' in rendered}")
over_count = has_rewrite and applicable_fixes == 0
print(f"OVER-COUNT BUG={over_count}")
assert not over_count, (
    "BUG: _render_verdict counted a fixless DoD issue as a proposed rewrite "
    "while the apply path would write nothing"
)
print("OK: render count agrees with the apply path")
