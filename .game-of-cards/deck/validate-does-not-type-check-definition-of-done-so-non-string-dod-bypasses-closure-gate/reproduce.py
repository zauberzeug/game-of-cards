"""Reproduce: goc validate never type-checks definition_of_done.

`validate_card` type-checks `tags` (must be a list) but never checks that
`definition_of_done` is a string. A card hand-edited to `definition_of_done: []`
or `null` validates clean — `count_dod_boxes` returns (0, 0), `dod_freeform`
becomes True, and the closure gate then treats the card as free-form prose,
letting `goc done --force` close it with zero verified criteria. A *done* card
with `definition_of_done: []` also escapes the done-with-unchecked guard
(which only fires when `dod_open > 0`).

Defect fires (exit 1) while the validator accepts a non-string DoD. After the
fix (a `definition_of_done: must be a string` check in `validate_card`), this
exits 0.
"""

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc.engine import Card, load_schema, validate_card  # noqa: E402

schema = load_schema()


def _card(dod) -> Card:
    fm = {
        "title": "x",
        "status": "open",
        "contribution": "medium",
        "created": "2026-05-27",
        "closed_at": None,
        "human_gate": "none",
        "tags": [],
        "definition_of_done": dod,
    }
    return Card(
        title="x",
        path=Path("x"),
        frontmatter=fm,
        body="",
        dod_open=0,
        dod_done=0,
    )


def _dod_type_error(dod) -> bool:
    errs = validate_card(_card(dod), schema, {"x"})
    return any("definition_of_done: must be a string" in e for e in errs)


def main() -> int:
    list_rejected = _dod_type_error([])
    null_rejected = _dod_type_error(None)
    string_accepted = not _dod_type_error("- [ ] do the thing")

    print(f"definition_of_done: []   rejected: {list_rejected}   (want True)")
    print(f"definition_of_done: null rejected: {null_rejected}   (want True)")
    print(f"definition_of_done: str  accepted: {string_accepted}   (control: True)")

    assert string_accepted, "control regressed: a real string DoD must validate clean"

    if not (list_rejected and null_rejected):
        print(
            "\nDEFECT: validate accepts a non-string definition_of_done, so a "
            "card with no real checkboxes slips through the closure gate."
        )
        return 1

    print("\nOK: a non-string definition_of_done is rejected by the validator.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
