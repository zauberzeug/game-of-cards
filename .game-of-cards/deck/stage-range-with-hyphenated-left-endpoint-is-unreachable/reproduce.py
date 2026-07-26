"""Reproduce: a `--stage a-b` range whose LEFT endpoint is itself a hyphenated
stage value cannot be expressed, because the range branch splits on the FIRST
hyphen only.

`parse_stage_filter` does `a, b = stage_flag.split("-", 1)`, so with
`pre-alpha` in the enum the span `pre-alpha` .. `stable` — spelled
`pre-alpha-stable` — splits to ("pre", "alpha-stable"); "pre" is not a stage and
the call exits 2. The mirror span `null` .. `pre-alpha` (spelled
`null-pre-alpha`) happens to work, because the hyphenated value lands in the
right half, where a greedy first-hyphen split leaves it intact. So the syntax is
half-usable, which is the tell that the split position is arbitrary rather than
resolved against the enum.

The shipped enum (`goc/schema.yaml`: `[null, alpha, beta, stable]`) has no
hyphenated value, so this is latent today — the same reachability path as the
sibling card
`stage-filter-rejects-hyphenated-stage-values-its-own-error-lists-as-valid`
(exact-match-first, already fixed): it opens up the moment `stage_values`
becomes project-supplied.

Exits non-zero while the split position is unresolved; zero once every split
point is considered against the enum.

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

ENUM = ["null", "pre-alpha", "alpha", "beta", "stable"]
engine.STAGE_ORDER = ENUM

# spec -> expected span ("EXIT2" when the argument is genuinely not a stage or a
# range over two stages)
CASES = {
    "pre-alpha-stable": ["pre-alpha", "alpha", "beta", "stable"],
    "null-pre-alpha": ["null", "pre-alpha"],
    "alpha-stable": ["alpha", "beta", "stable"],
    "pre-alpha": ["pre-alpha"],
    "nope-alpha": "EXIT2",
    "alpha-nope": "EXIT2",
}

# An enum where one argument has TWO valid splits: `alpha-beta-stable` reads as
# both `alpha`..`beta-stable` and `alpha-beta`..`stable`. Resolving the split
# against the enum makes such an argument detectable — a first-hyphen split
# cannot see the second reading, so it silently returns one of the two spans.
AMBIGUOUS_ENUM = ["null", "alpha", "beta", "alpha-beta", "beta-stable", "stable"]
AMBIGUOUS_SPEC = "alpha-beta-stable"


def probe(spec: str, want: object) -> str | None:
    err = io.StringIO()
    try:
        with redirect_stderr(err):
            got: object = engine.parse_stage_filter(spec)
    except SystemExit as exc:
        got = f"exit {exc.code}"
        ok = want == "EXIT2" and exc.code == 2
    else:
        ok = got == want
    print(f"--stage {spec!r:20} -> {got!r:42} want {want!r}   {'ok' if ok else 'FAIL'}")
    return None if ok else f"--stage {spec!r} gave {got!r}, want {want!r}"


print(f"=== with a hyphenated enum value: {ENUM} ===")
failures: list[str] = []
for spec, want in CASES.items():
    failures.append(probe(spec, want))

engine.STAGE_ORDER = AMBIGUOUS_ENUM
print(f"\n=== with an enum that makes one argument ambiguous: {AMBIGUOUS_ENUM} ===")
failures.append(probe(AMBIGUOUS_SPEC, "EXIT2"))

failures = [f for f in failures if f]
print("\n=== verdict ===")
if failures:
    for f in failures:
        print(f"FAIL: {f}")
    print(
        "\nThe range branch must resolve its split position against STAGE_ORDER —\n"
        "try every hyphen position, not just the first — or a span whose left\n"
        "endpoint is a hyphenated stage value cannot be spelled at all."
    )
    sys.exit(1)
print("PASS: every span over the enum is expressible, ambiguity is reported")
