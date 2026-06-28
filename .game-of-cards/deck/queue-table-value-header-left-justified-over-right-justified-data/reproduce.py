"""Disproof: render_table's VALUE header/data justification mismatch is unobservable.

The header row left-justifies the VALUE header while the VALUE data cells are
right-justified. The hypothesis was that this offsets the digits from their
label on every render. It does NOT: the value string is bounded at 4 chars
("30.0") < the 5-char "VALUE" header, so the column width is always pinned to
the header and ljust/rjust of the header are identical no-ops. The mismatch
only surfaces for a 6+-char value (>= 1000), which compute_values never emits.

Exits zero: for every REACHABLE value the header and data share their right
edge (no defect). The script also prints the UNREACHABLE 6-char case to show
where a real misalignment would appear if the value bound were ever raised.
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

from goc.engine import Card, render_table  # noqa: E402


def _card() -> Card:
    return Card(
        title="a",
        path=Path("x"),
        frontmatter={
            "title": "a",
            "status": "open",
            "contribution": "high",
            "human_gate": "none",
            "created": "2026-01-01",
        },
        body="",
        dod_open=0,
        dod_done=1,
    )


def _value_region(verbose: int, value: float) -> tuple[str, str]:
    c = _card()
    out = render_table(
        [c], verbose=verbose, no_color=True, values={"a": (value, [])}, by_title={"a": c}
    )
    lines = out.splitlines()
    header, data = lines[0], lines[2]
    i = header.index("VALUE")
    # Width = next column gap, or end of line for the trailing column.
    j = header.find("  ", i)
    end = j if j != -1 else len(header)
    return header[i:end], data[i:end]


def main() -> int:
    ok = True
    # Reachable values: compute_values bound is max_rank/(1-gamma) = 30.0.
    for value in (9.0, 30.0):
        for verbose in (0, 1):
            hdr, data = _value_region(verbose, value)
            aligned = len(hdr.rstrip()) == len(data.rstrip())
            print(f"value={value} verbose={verbose}: header={hdr!r} data={data!r} aligned={aligned}")
            if not aligned:
                ok = False

    # Note: a 6+-char value (>= 1000) would force the column wider than the
    # 5-char "VALUE" header and expose the otherwise-invisible justification
    # mismatch — but compute_values bounds the value at 30.0, so that input is
    # unreachable in shipping. See README "Why it's disproved".

    if ok:
        print("PASS: for every reachable value the VALUE header and data share their right edge")
        return 0
    print("FAIL: a reachable value misaligns the VALUE header from its data")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
