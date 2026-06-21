#!/usr/bin/env python3
"""Proof: the OpenClaw `index.ts` session-start reader treats an explicit
YAML null literal (`waiting_on: null` / `~` / `Null` / `NULL`) on an active
card as an impediment, so the hook announces a fully-resumable card as
`agent cannot resume.` — while the Python hook (and the engine) resolve the
same literal to "absent" and report the card as NOT impeded.

The reader at `openclaw-plugin/index.ts` does
`waitingOn = stripQuotes(frontmatterTail(line))` with no null-literal
resolution, so the raw token `"null"` survives as a truthy string and
`isImpeded("null", "", now)` returns true.

This script extracts the real TS functions from `index.ts` and runs them
under Node (the same extraction the regression test uses, so it stays
pinned to production source), then compares each cell to the Python hook's
`_is_impeded`. Divergence == the defect.

Skips the TS leg (and reports SKIP) if `node` / `--experimental-strip-types`
is unavailable.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
INDEX_TS = ROOT / "openclaw-plugin" / "index.ts"
HOOK_PY = ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py"

NULL_LITERALS = ["null", "Null", "NULL", "~"]
PINNED_NOW_ISO = "2026-05-29T12:00:00Z"


def _load_py_hook():
    spec = importlib.util.spec_from_file_location("_goc_deck_session_start", HOOK_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _py_impeded(mod, literal: str) -> bool:
    """Run the Python hook's _is_impeded against an active card whose
    waiting_on is the given explicit-null literal."""
    with tempfile.TemporaryDirectory() as d:
        readme = Path(d) / "README.md"
        readme.write_text(
            "---\n"
            "title: probe\n"
            "status: active\n"
            "human_gate: none\n"
            f"waiting_on: {literal}\n"
            "---\n\n# probe\n"
        )
        return mod._is_impeded(readme)


def _extract_const_line(src: str, name: str) -> str:
    m = re.search(rf"^const {re.escape(name)} = [^\n]+;$", src, re.MULTILINE)
    if not m:
        raise RuntimeError(f"const {name} not found in {INDEX_TS}")
    return m.group(0)


def _extract_fn(src: str, name: str) -> str:
    m = re.search(
        rf"^function {re.escape(name)}\b.*?(?=^\}}$)\}}$", src, re.DOTALL | re.MULTILINE
    )
    if not m:
        raise RuntimeError(f"function {name} not found in {INDEX_TS}")
    return m.group(0)


def _node_ok() -> bool:
    if shutil.which("node") is None:
        return False
    probe = subprocess.run(
        ["node", "--experimental-strip-types", "-e", "const x: number = 1;"],
        capture_output=True,
    )
    return probe.returncode == 0


def _ts_impeded_all() -> dict[str, bool]:
    """Run the real TS reader-extraction + isImpeded for every null literal."""
    src = INDEX_TS.read_text()
    pieces = [
        _extract_const_line(src, "ISO_DATE_RE"),
        _extract_const_line(src, "NULL_LITERALS"),
        _extract_fn(src, "stripQuotes"),
        _extract_fn(src, "frontmatterTail"),
        _extract_fn(src, "scalarOrEmpty"),
        _extract_fn(src, "parseWaitingUntil"),
        _extract_fn(src, "isImpeded"),
    ]
    literals_json = json.dumps(NULL_LITERALS)
    harness = "\n".join(pieces) + f"""

const NOW = new Date("{PINNED_NOW_ISO}");
const out = {{}};
for (const lit of {literals_json}) {{
  // Exactly what findActiveCards does for a `waiting_on:` frontmatter line.
  const waitingOn = scalarOrEmpty("waiting_on: " + lit);
  out[lit] = isImpeded(waitingOn, "", NOW);
}}
console.log(JSON.stringify(out));
"""
    with tempfile.TemporaryDirectory() as d:
        script = Path(d) / "probe.ts"
        script.write_text(harness)
        res = subprocess.run(
            ["node", "--experimental-strip-types", str(script)],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"node probe failed:\n{res.stderr}")
        return json.loads(res.stdout.strip())


def main() -> int:
    mod = _load_py_hook()
    py = {lit: _py_impeded(mod, lit) for lit in NULL_LITERALS}

    print("Active card with `waiting_on: <literal>` — is it announced as impeded?\n")
    print(f"{'literal':>8} | {'Python hook':>12} | {'OpenClaw TS':>12} | verdict")
    print("-" * 54)

    if not _node_ok():
        for lit in NULL_LITERALS:
            print(f"{lit:>8} | {str(py[lit]):>12} | {'(node n/a)':>12} | SKIP")
        print("\nSKIP: node / --experimental-strip-types unavailable; "
              "Python leg shown for reference (all should be impeded=False).")
        return 0

    ts = _ts_impeded_all()
    diverged = 0
    for lit in NULL_LITERALS:
        bad = py[lit] != ts[lit]
        diverged += bad
        verdict = "DIVERGES (bug)" if bad else "match"
        print(f"{lit:>8} | {str(py[lit]):>12} | {str(ts[lit]):>12} | {verdict}")

    print()
    if diverged:
        print(f"DEFECT CONFIRMED: {diverged}/{len(NULL_LITERALS)} explicit-null "
              "literals impede on the OpenClaw host but not under the Python hook.")
        print("Expected after fix: Python and OpenClaw TS agree (impeded=False) "
              "for every explicit-null literal.")
        return 1
    print("No divergence: the TS reader resolves explicit-null literals like the "
          "Python hook. (Fix has landed.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
