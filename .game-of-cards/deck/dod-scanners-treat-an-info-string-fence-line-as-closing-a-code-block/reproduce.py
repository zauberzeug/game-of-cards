"""Reproduce: the shared DoD fenced-code mask (`_dod_fenced_mask`) closes a
fenced block on *any* same-character fence run of length >= the opener's, even
when that line carries an info string (a language tag, e.g. a ```yaml line).
Per CommonMark §4.5 a closing code fence "may not have an info string" — such a
line is content, not a close. The mask closes the block early, and the
illustrative `- [ ]` lines that follow are miscounted as real DoD items.

Run: uv run python .game-of-cards/deck/dod-scanners-treat-an-info-string-fence-line-as-closing-a-code-block/reproduce.py
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

from goc.engine import count_dod_boxes, _dod_box_indices  # noqa: E402

F = chr(96) * 3  # ```
# A backtick-fenced code block whose inner fence line carries an info string
# (```yaml). Per CommonMark that line is content, so the block stays open and
# the illustrative `- [ ]` example inside it must not be counted.
dod = "\n".join(
    [
        "- [x] MECHANICAL: the one real, completed item",
        F,
        "an example block:",
        F + "yaml",
        "- [ ] TDD: illustrative checkbox that must NOT count",
        F,
    ]
)

open_n, done_n = count_dod_boxes(dod)
indices = _dod_box_indices(dod.splitlines())
print(f"count_dod_boxes -> open={open_n} done={done_n}")
print(f"_dod_box_indices -> {indices}")

expected = (0, 1)
expected_indices = [0]
if (open_n, done_n) == expected and indices == expected_indices:
    print("PASS: the info-string fence line does not close the block; "
          "the illustrative `- [ ]` inside it is not counted")
    sys.exit(0)
else:
    print(
        f"FAIL: expected open={expected[0]} done={expected[1]} "
        f"indices={expected_indices}; the info-string fence line falsely "
        f"closed the block, so the illustrative `- [ ]` example is counted as "
        f"a real DoD item and would block closure"
    )
    sys.exit(1)
