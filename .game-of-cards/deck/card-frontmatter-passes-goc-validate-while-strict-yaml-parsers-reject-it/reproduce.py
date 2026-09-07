#!/usr/bin/env python3
"""Show that this repo's deck carries cards no strict YAML parser can read.

Three claims, each printed with its own verdict line:

1. `yaml_lite` (goc's vendored parser, the one every goc surface uses) parses
   every card's frontmatter block. `goc validate` reports `OK` for all of them.
2. A strict YAML 1.1/1.2 parser refuses two of those same blocks outright.
3. The hazard shapes behind both refusals are statically detectable without a
   YAML dependency — `scripts/check_card_frontmatter_yaml.py` agrees with the
   strict parser card-for-card across the whole deck, with no false positive
   and no false negative.

Claim 3 loads the shipped guard itself rather than restating its rules, so this
script measures the guard that actually runs in CI and pre-commit; a change to
the guard's hazard set shows up here as a false positive or false negative
instead of silently diverging from a copy.

Claim 2 needs a reference implementation to be evidence rather than assertion,
so this script imports PyYAML. PyYAML is deliberately NOT a goc dependency
(`drop-third-party-runtime-dependencies-from-goc`), so it is imported lazily
and the script degrades to claims 1 and 3 when it is absent — the shipped guard
never needs it.

    uv run python .game-of-cards/deck/<this-card>/reproduce.py   # claims 1 + 3
    python3 .game-of-cards/deck/<this-card>/reproduce.py         # + claim 2
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

from goc._vendor import yaml_lite  # noqa: E402
from goc.engine import FRONTMATTER_RE  # noqa: E402

DECK = ROOT / ".game-of-cards" / "deck"


def _load_guard():
    """Load the shipped guard so this measures it, not a restatement of it."""
    spec = importlib.util.spec_from_file_location(
        "_goc_card_frontmatter_yaml_guard",
        ROOT / "scripts" / "check_card_frontmatter_yaml.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = _load_guard()


def main() -> int:
    try:
        import yaml  # noqa: PLC0415
    except ModuleNotFoundError:
        yaml = None

    lite_ok = 0
    lite_failed: list[str] = []
    strict_failed: list[tuple[str, str]] = []
    detected: list[tuple[str, list[str]]] = []

    for card_dir in sorted(DECK.iterdir()):
        readme = card_dir / "README.md"
        if not readme.is_file():
            continue
        match = FRONTMATTER_RE.match(readme.read_text(encoding="utf-8"))
        if not match:
            continue
        block = match.group(1) + match.group(2)

        try:
            yaml_lite.safe_load(block)
            lite_ok += 1
        except Exception as exc:  # noqa: BLE001 — any refusal is the datum
            lite_failed.append(f"{card_dir.name}: {exc}")

        if yaml is not None:
            try:
                yaml.safe_load(block)
            except yaml.YAMLError as exc:
                strict_failed.append((card_dir.name, str(exc).splitlines()[0]))

        found = [
            f"line {lineno}: {key}: {reason}"
            for lineno, key, reason in guard.flag_frontmatter(block)
        ]
        if found:
            detected.append((card_dir.name, found))

    scanned = lite_ok + len(lite_failed)
    print(f"cards with frontmatter scanned: {scanned}")

    print(f"\n[1] goc's vendored yaml_lite parses: {lite_ok}/{scanned}")
    for line in lite_failed:
        print(f"      REFUSED {line}")

    if yaml is None:
        print("\n[2] strict YAML parser: SKIPPED (PyYAML not importable here)")
    else:
        print(f"\n[2] strict YAML (PyYAML {yaml.__version__}) refuses: {len(strict_failed)}")
        for name, err in strict_failed:
            print(f"      REFUSED {name}")
            print(f"              {err}")

    print(f"\n[3] scripts/check_card_frontmatter_yaml.py flags: {len(detected)}")
    for name, found in detected:
        print(f"      FLAGGED {name}")
        for reason in found:
            print(f"              {reason}")

    if yaml is not None:
        flagged = {name for name, _ in detected}
        refused = {name for name, _ in strict_failed}
        print(f"\n      false positives (flagged, strict YAML fine): {sorted(flagged - refused)}")
        print(f"      false negatives (strict YAML refuses, unflagged): {sorted(refused - flagged)}")

    defect_present = bool(detected) or bool(strict_failed)
    print(
        f"\nVERDICT: {'DEFECT PRESENT' if defect_present else 'clean'} — "
        f"{len(detected)} card(s) pass `goc validate` while carrying frontmatter "
        "no strict YAML parser can read."
    )
    return 1 if defect_present else 0


if __name__ == "__main__":
    raise SystemExit(main())
