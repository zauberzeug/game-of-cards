#!/usr/bin/env python3
"""Evidence for openclaw-plugin-manifest-config-options-do-not-behave-as-documented.

Two independent claims about `openclaw-plugin/openclaw.plugin.json`'s
`configSchema`, each checked mechanically against the implementation:

  CLAIM 1 (dead knob) — `deck_path` is declared as a settable config key
    but is read by nothing: not the TypeScript entry (`index.ts`), not the
    committed runtime bundle (`dist/index.js`), not the vendored Python
    engine. Since `additionalProperties: false` restricts the accepted key
    set to exactly what the schema declares, an operator who sets
    `deck_path` gets no validation error and no effect.

  CLAIM 2 (inverted default) — `pattern_generalization_check` is declared
    `"default": true`, while every other surface that states a default says
    OFF: `openclaw-plugin/README.md` ("Off by default") and `index.ts`
    ("Opt-in (default off)"), whose runtime gate skips the hook unless the
    value is explicitly `true`.

The check is deliberately generous about what counts as "read": any
mention of the key in snake_case or camelCase in any consumer file. A key
that fails even that bar is unambiguously unwired.

Run:   uv run python .game-of-cards/deck/<title>/reproduce.py
Exit 0 = defect reproduced; exit 1 = defect gone (both claims falsified).
"""

from __future__ import annotations

import json
import re
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
MANIFEST = ROOT / "openclaw-plugin" / "openclaw.plugin.json"
ENTRY = ROOT / "openclaw-plugin" / "index.ts"
BUNDLE = ROOT / "openclaw-plugin" / "dist" / "index.js"
README = ROOT / "openclaw-plugin" / "README.md"
ENGINE = ROOT / "goc" / "engine.py"

# Every surface that could plausibly consume a plugin config key: the
# authored entry, the bundle OpenClaw actually loads, and the engine the
# `goc` tool shells out to (a deck-location override would have to land in
# one of them).
CONSUMERS = (ENTRY, BUNDLE, ENGINE)


def key_readers(key: str) -> list[str]:
    """Consumer files that so much as mention `key` (snake_case or camelCase)."""
    camel = re.sub(r"_([a-z])", lambda m: m.group(1).upper(), key)
    hits = []
    for path in CONSUMERS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if key in text or camel in text:
            hits.append(str(path.relative_to(ROOT)))
    return hits


def main() -> int:
    schema = json.loads(MANIFEST.read_text(encoding="utf-8"))["configSchema"]
    props: dict = schema["properties"]

    print("openclaw.plugin.json configSchema")
    print(f"  additionalProperties : {schema.get('additionalProperties')!r}")
    print(f"  declared keys        : {', '.join(props)}")
    print()

    print("CLAIM 1 - declared config keys vs. code that reads them")
    dead = []
    for key in props:
        readers = key_readers(key)
        verdict = "READ by " + ", ".join(readers) if readers else "*** NEVER READ ***"
        print(f"  {key:32s} {verdict}")
        if not readers:
            dead.append(key)
    print(f"  -> dead knobs: {dead or 'none'}")
    print()

    print("CLAIM 2 - declared default vs. every surface that states one")
    declared = props["pattern_generalization_check"].get("default")
    print(f"  openclaw.plugin.json 'default'          : {declared!r}")

    readme_line = next(
        (
            ln.strip()
            for ln in README.read_text(encoding="utf-8").splitlines()
            if "pattern_generalization_check" in ln and "default" in ln.lower()
        ),
        "",
    )
    readme_says_off = "off by default" in readme_line.lower()
    print(f"  README.md says off by default           : {readme_says_off}")

    entry_text = ENTRY.read_text(encoding="utf-8")
    entry_says_off = "default off" in entry_text
    # The runtime gate: anything other than an explicit `true` short-circuits.
    gate = "ctx?.config?.pattern_generalization_check !== true" in entry_text
    print(f"  index.ts comments 'default off'         : {entry_says_off}")
    print(f"  index.ts gate skips unless === true     : {gate}")
    print()

    claim1 = dead == ["deck_path"]
    claim2 = declared is True and readme_says_off and entry_says_off and gate
    print(f"CLAIM 1 reproduced (deck_path is a dead knob)      : {claim1}")
    print(f"CLAIM 2 reproduced (default: true vs. default off) : {claim2}")
    if claim1 or claim2:
        print("\nDEFECT PRESENT")
        return 0
    print("\nDEFECT GONE - manifest configSchema now matches the implementation")
    return 1


if __name__ == "__main__":
    sys.exit(main())
