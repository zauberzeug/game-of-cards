"""Reproduce: the shared DoD fenced-code mask (`_dod_fenced_mask`) toggles
`in_fence` on *any* fence delimiter, so a `~~~` line shown as illustrative text
inside a ```-opened code block is wrongly read as *closing* that block. The
mask then desynchronizes, and a genuine `- [ ]` item after the real closing
fence is misclassified as fenced — undercounting open boxes and letting
`goc done` close a card with unfinished work.

Per CommonMark §4.5, a fenced code block is closed only by a fence using the
*same* character with a run length >= the opener's. A `~~~` line cannot close a
```-opened block.

Run: uv run python .game-of-cards/deck/dod-scanners-treat-a-tilde-fence-as-closing-a-backtick-code-block/reproduce.py
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
# A backtick-fenced code block that illustrates a tilde fence as text, followed
# by a real, still-open DoD item after the genuine closing backtick fence.
dod = "\n".join(
    [
        "- [x] MECHANICAL: the one real, completed item",
        F,
        "an alternate fence syntax looks like:",
        "~~~",
        F,
        "- [ ] TDD: a genuine unfinished item that MUST block closure",
    ]
)

open_n, done_n = count_dod_boxes(dod)
indices = _dod_box_indices(dod.splitlines())
print(f"count_dod_boxes -> open={open_n} done={done_n}")
print(f"_dod_box_indices -> {indices}")

expected = (1, 1)
expected_indices = [0, 5]
if (open_n, done_n) == expected and indices == expected_indices:
    print("PASS: the ~~~ line inside the backtick block does not close it; "
          "the real open item after the closing fence is counted")
    sys.exit(0)
else:
    print(
        f"FAIL: expected open={expected[0]} done={expected[1]} "
        f"indices={expected_indices}; the ~~~ line falsely closed the backtick "
        f"fence, so the genuine `- [ ]` item is hidden and `goc done` would "
        f"close the card with unfinished work"
    )
    sys.exit(1)
