"""Reproduce: `--stage <value-with-hyphen>` is rejected even when the value is
in the stage enum, and the rejection message lists it as a valid choice.

`parse_stage_filter` branches on `"-" in stage_flag` before it ever checks
exact membership in `STAGE_ORDER`, so a hyphenated enum value can only ever be
read as a range `a-b` — and `a` ("pre") is not a stage, so it exits 2.

The shipped enum (`goc/schema.yaml`: `[null, alpha, beta, stable]`) has no
hyphenated value, so this is latent today. The probe therefore drives
`STAGE_ORDER` directly with the hyphenated enum a configurable-stage schema
would produce, then also prints the shipped enum so a reader can see which
half of the defect is live.

Exits non-zero while the ordering bug stands; zero once exact membership is
tested first.

    uv run python .game-of-cards/deck/<this-card>/reproduce.py
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stderr
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402

print("=== shipped stage enum (goc/schema.yaml) ===")
print(f"STAGE_ORDER = {engine.STAGE_ORDER}")
print("no hyphenated value today -> the defect is latent, not live\n")

# The enum a configurable-stage schema would produce. `support-custom-card-
# workflows-and-statuses` is the open story that makes stage_values project-
# supplied; `pre-alpha` is the obvious first hyphenated stage name.
ENUM = ["null", "pre-alpha", "alpha", "beta", "stable"]
engine.STAGE_ORDER = ENUM

print(f"=== with a hyphenated enum value: {ENUM} ===")
failures: list[str] = []
for spec in ("pre-alpha", "alpha", "alpha-stable"):
    err = io.StringIO()
    try:
        with redirect_stderr(err):
            got = engine.parse_stage_filter(spec)
        print(f"--stage {spec!r:14} -> {got}")
    except SystemExit as exc:
        message = err.getvalue().strip()
        print(f"--stage {spec!r:14} -> exit {exc.code}")
        print(f"                          {message}")
        if spec in ENUM:
            failures.append(
                f"--stage {spec!r} rejected although {spec!r} is in the enum"
            )
            if spec in message:
                failures.append(
                    f"...and the rejection message lists {spec!r} as a valid choice"
                )

print("\n=== verdict ===")
if failures:
    for f in failures:
        print(f"FAIL: {f}")
    print(
        "\n`parse_stage_filter` must test exact membership in STAGE_ORDER before\n"
        "it treats the argument as an `a-b` range, or no hyphenated stage value\n"
        "is addressable through --stage."
    )
    sys.exit(1)
print("PASS: hyphenated enum values are addressable through --stage")
