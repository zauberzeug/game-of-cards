"""Reproduce: the decision/verdict coherence validator skips rubric-derived
decision headings.

`RESOLVED_DECISION_RE` anchors the resolved-decision heading as `## Decision`
followed by only optional horizontal whitespace and a newline — deliberately
to exclude the *pending* `## Decision required` section. But that anchor also
collaterally excludes the documented `## Decision (rubric-derived)` heading
that `Skill(create-card)` writes when the project rubric pre-resolves a
gate-`none` card (create-card/SKILL.md). So a rubric-derived decision that
re-scopes/reverses a prior verdict, left next to a stale negative-verdict
summary, never trips `validate_decision_verdict_coherence` — the safety net
the parent card built has a hole exactly where one class of resolved decision
lands.

Builds two in-memory cards that are identical except for the decision heading
(`## Decision` vs `## Decision (rubric-derived)`), each with re-scope language
in the decision body and a stale `refuted` summary. Runs the advisory
coherence validator over both.

Post-fix invariant (asserted below): BOTH the bare `## Decision` and the
`## Decision (rubric-derived)` cards are flagged, while the pending
`## Decision required` section is never flagged. Before the fix the
rubric-derived card was silently skipped; the git history of this file's
success condition is the red/green record.
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


REPO = _repo_root()
sys.path.insert(0, str(REPO))

from goc import engine  # noqa: E402


def _card(heading: str) -> engine.Card:
    body = (
        "# c\n\n"
        "Body text.\n\n"
        f"{heading}\n\n"
        "*Resolved 2026-06-15:* the approach is now viable; this reverses the\n"
        "earlier call.\n\n"
        "*Reasoning:* new evidence.\n"
    )
    return engine.Card(
        title="c",
        path=REPO,
        frontmatter={
            "title": "c",
            "status": "open",
            "summary": "REFUTED: the approach does not work.",
        },
        body=body,
        dod_open=0,
        dod_done=0,
    )


def _flagged(heading: str) -> bool:
    warnings = engine.validate_decision_verdict_coherence([_card(heading)])
    return any(w.klass == "DECISION_CONTRADICTS_VERDICT" for w in warnings)


def main() -> int:
    bare = _flagged("## Decision")
    rubric = _flagged("## Decision (rubric-derived)")
    required = _flagged("## Decision required")

    print(f"bare '## Decision'               flagged: {bare}")
    print(f"'## Decision (rubric-derived)'   flagged: {rubric}")
    print(f"'## Decision required' (pending) flagged: {required}")

    # Sanity: the pending section must never be treated as a resolved decision.
    if required:
        print("UNEXPECTED: pending '## Decision required' was flagged")
        return 1

    # Post-fix invariant: both shipped resolved forms are flagged.
    if bare and rubric:
        print("\nOK: both '## Decision' and '## Decision (rubric-derived)' "
              "resolved decisions are flagged; '## Decision required' is not.")
        return 0

    if bare and not rubric:
        print("\nBUG: rubric-derived resolved decision escapes the coherence "
              "validator (pre-fix behavior).")
    else:
        print("\nUNEXPECTED: bare '## Decision' was not flagged.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
