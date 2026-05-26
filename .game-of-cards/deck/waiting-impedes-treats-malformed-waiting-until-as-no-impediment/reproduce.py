"""Reproduce: `waiting_impedes` early-returns False on a malformed
`waiting_until`, BEFORE consulting the `waiting_on` reason. A card with
an active reason plus a garbage date is therefore reported as NOT
impeded — it re-enters the pull/next queue — contradicting the
docstring's promise that a reason without a usable date is an
open-ended block.

Exit 0 == a malformed date falls through to the reason check, so a card
          with `waiting_on` set IS impeded (defect fixed). The valid
          future/elapsed and bare-reason / bare-date paths still behave.
Exit 1 == the malformed-date card is reported NOT impeded (defect fires).
"""
import sys
from datetime import date
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc.engine import Card, waiting_impedes  # noqa: E402


def _card(**overlay) -> Card:
    fm = {"status": "open", "human_gate": "none"}
    fm.update(overlay)
    return Card(title="t", path=Path("."), frontmatter=fm, body="", dod_open=0, dod_done=0)


TODAY = date(2026, 5, 26)

reason_plus_garbage = _card(waiting_on="external", waiting_until="not-a-date")
reason_no_date = _card(waiting_on="external")
no_overlay = _card()
future_date = _card(waiting_until="2026-12-31")
elapsed_date = _card(waiting_until="2026-01-01")
reason_plus_future = _card(waiting_on="external", waiting_until="2026-12-31")

results = {
    "reason + garbage date (defect case)": waiting_impedes(reason_plus_garbage, today=TODAY),
    "reason, no date (open-ended)":        waiting_impedes(reason_no_date, today=TODAY),
    "no overlay":                          waiting_impedes(no_overlay, today=TODAY),
    "bare future date (deferred)":         waiting_impedes(future_date, today=TODAY),
    "bare elapsed date (resurfaces)":      waiting_impedes(elapsed_date, today=TODAY),
    "reason + future date":                waiting_impedes(reason_plus_future, today=TODAY),
}
for label, val in results.items():
    print(f"  {label:38s} -> impeded={val}")
print()

expected = {
    "reason + garbage date (defect case)": True,   # malformed date treated as absent -> reason hides
    "reason, no date (open-ended)":        True,
    "no overlay":                          False,
    "bare future date (deferred)":         True,
    "bare elapsed date (resurfaces)":      False,
    "reason + future date":                True,
}

mismatches = {k: results[k] for k in expected if results[k] != expected[k]}
if mismatches:
    print(f"DEFECT: waiting_impedes returned unexpected values: {mismatches}")
    sys.exit(1)
print("OK: malformed waiting_until falls through to the reason check; all paths correct")
sys.exit(0)
