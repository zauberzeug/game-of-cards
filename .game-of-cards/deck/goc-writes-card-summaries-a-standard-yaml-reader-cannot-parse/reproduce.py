#!/usr/bin/env python3
"""Proof that `emit_frontmatter` writes plain scalars strict YAML refuses.

Run:  uv run python .game-of-cards/deck/<this-card>/reproduce.py

Every value in CASES is illegal as a YAML *plain* scalar, so the pass/fail
predicate needs no third-party parser: a correct emitter renders each one
quoted. A value still emitted plain is the defect firing. Exits 0 once every
case emits quoted; exits 1 while any emits plain.

Parts 2-3 show where the plain output lands (the repo's own committed
pre-commit guard, and `goc validate` via the vendored parser). Part 4
cross-checks the "strict YAML refuses it" premise against PyYAML when it
happens to be importable — informational, never the pass/fail signal, because
PyYAML is deliberately not a dependency of this repo.
"""

from __future__ import annotations

import importlib.util
import sys
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
from goc._vendor import yaml_lite  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "goc_card_yaml_guard", ROOT / "scripts" / "check_card_frontmatter_yaml.py"
)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


# Each entry is a value a card `summary:` could legitimately hold, paired with
# whether the repo's committed guard is expected to catch the emitter's output.
# Every one of them is refused by strict YAML (Part 4 proves it); the ones
# marked `guard_catches=False` are additionally invisible to the guard, so they
# reach a consumer's YAML reader with nothing in this repo objecting.
CASES = [
    ("!important deck rewrite", "leading '!' — YAML reads it as a tag", True),
    ("%-based progress metric", "leading '%' — YAML reserves it for directives", True),
    ("- listed as a sub-item", "leading '- ' — YAML reads it as a sequence entry", True),
    ("? unclear which verb wrote it", "leading '? ' — YAML reads it as a complex key", True),
    ("|pipe-delimited output", "leading '|' that is not a complete block header", True),
    (">greater-than in a diff", "leading '>' that is not a complete block header", True),
    ("column\tseparated", "interior TAB — illegal in a YAML plain scalar", False),
]


def _frontmatter_block(value: str) -> str:
    """Emit a minimal card frontmatter block carrying `value` as the summary."""
    text = engine.emit_frontmatter(
        {"title": "probe-card", "summary": value, "status": "open"}
    )
    return text[len("---\n") : text.rindex("\n---\n") + 1]


def main() -> int:
    plain_failures = 0
    roundtrip_regressed = False

    print("=" * 72)
    print("Part 1 — emit_frontmatter renders these as plain (illegal) scalars")
    print("=" * 72)
    print(f"  emitter quote-trigger : engine._YAML_INDICATOR_FIRST = "
          f"{''.join(sorted(engine._YAML_INDICATOR_FIRST))!r}")
    print(f"  guard  quote-trigger  : guard.LEADING_INDICATORS    = "
          f"{''.join(guard.LEADING_INDICATORS)!r}")
    print(f"                          guard.SPACE_BOUND_INDICATORS = "
          f"{guard.SPACE_BOUND_INDICATORS!r}")
    print()

    for value, why, guard_catches in CASES:
        block = _frontmatter_block(value)
        emitted = next(l for l in block.splitlines() if l.startswith("summary:"))
        rendered = emitted[len("summary: "):]
        # The fix-detecting predicate, independent of any third-party parser:
        # every one of these values is illegal as a YAML *plain* scalar, so a
        # fixed emitter must render it quoted. Still plain == defect fires.
        plain = not rendered.startswith('"')
        flagged = bool(guard.flag_frontmatter(block))
        if plain:
            plain_failures += 1
        # Where it lands differs, and both landings are bad. Flagged: the
        # emitter wrote frontmatter this repo's own pre-commit hook rejects.
        # Not flagged: the emitter wrote frontmatter strict YAML rejects and
        # nothing in this repo objects — it ships to consumers.
        verdict = (
            "FLAGGED — emitter wrote what the commit hook rejects"
            if flagged
            else "not flagged — guard blind spot, ships silently"
        )
        if flagged != guard_catches:
            print(f"  [NOTE] guard coverage for {value!r} changed since filing")
        print(f"  [{'FAIL' if plain else ' ok ':^5}] {why}")
        print(f"         emitted: {emitted!r}")
        print(f"         guard  : {verdict}")

    print()
    print("=" * 72)
    print("Part 2 — the guard's own remedy is a loop")
    print("=" * 72)
    print("  guard failure message says: \"Quote the value — `emit_frontmatter`")
    print("  already produces the correct form.\"  Re-emitting the flagged value:")
    print()
    for value, _why, _catches in CASES[:1]:
        first = _frontmatter_block(value)
        # The operator hand-quotes it; the guard goes green.
        hand_fixed = first.replace(f"summary: {value}", f'summary: "{value}"')
        print(f"    hand-quoted : {hand_fixed.splitlines()[1]!r}")
        print(f"    guard       : "
              f"{'FLAGGED' if guard.flag_frontmatter(hand_fixed) else 'clean'}")
        # Any full-frontmatter re-emit verb round-trips through the emitter.
        reparsed = yaml_lite.safe_load(hand_fixed)
        re_emitted = _frontmatter_block(reparsed["summary"])
        print(f"    after re-emit: {re_emitted.splitlines()[1]!r}")
        regressed = bool(guard.flag_frontmatter(re_emitted))
        print(f"    guard       : {'FLAGGED again' if regressed else 'clean'}")
        if regressed:
            roundtrip_regressed = True
            print("    [FAIL] the emitter strips the quotes the guard demanded")

    print()
    print("=" * 72)
    print("Part 3 — the vendored parser (what goc validate reads) accepts them all")
    print("=" * 72)
    for value, _why, _catches in CASES:
        block = _frontmatter_block(value)
        try:
            parsed = yaml_lite.safe_load(block)
            got = parsed.get("summary")
            print(f"  vendored parser round-trips {value!r:32} -> "
                  f"{'faithful' if got == value else 'CHANGED'}")
        except Exception as exc:  # noqa: BLE001
            print(f"  vendored parser RAISED on {value!r}: {exc}")

    print()
    print("=" * 72)
    print("Part 4 — strict-YAML cross-check (skipped when PyYAML is absent)")
    print("=" * 72)
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        print("  PyYAML not installed — informational only. Part 1's plain-vs-quoted")
        print("  verdict is the pass/fail signal and does not need this section.")
    else:
        for value, _why, _catches in CASES:
            block = _frontmatter_block(value)
            try:
                yaml.safe_load(block)
                print(f"  strict YAML accepts {value!r}")
            except Exception as exc:  # noqa: BLE001
                head = str(exc).splitlines()[0]
                print(f"  strict YAML REFUSES {value!r:32} -> {head}")

    print()
    print("=" * 72)
    if plain_failures or roundtrip_regressed:
        print(f"DEFECT FIRES — {plain_failures}/{len(CASES)} value(s) emitted as a plain scalar "
              f"strict YAML refuses.")
        if roundtrip_regressed:
            print("               Re-emitting a hand-quoted card strips the quotes back "
                  "out,\n               so the guard's documented remedy never converges.")
        return 1
    print("Clean — emit_frontmatter quotes every strict-YAML-illegal plain scalar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
