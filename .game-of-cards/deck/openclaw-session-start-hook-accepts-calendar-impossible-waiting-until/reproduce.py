"""Reproduce the OpenClaw TS-port `parseWaitingUntil` calendar-leniency drift.

The Python engine (`goc.engine._waiting_until_instant` via `_is_iso_date`)
rejects a calendar-impossible-but-ISO-shaped `waiting_until` such as
`2026-02-30`, so `waiting_impedes` falls into its unparseable backstop and
keeps the card hidden from the queue. The OpenClaw session-start hook ports
this predicate to TypeScript in `openclaw-plugin/index.ts`, but
`parseWaitingUntil` parses with JS `Date.parse`, which is lenient: it rolls
`2026-02-30` forward to `2026-03-02` instead of returning null. The hook then
treats the card as no-longer-impeded (when the rolled date is in the past) and
re-announces a deferred card as a resumable active card at session start.

This script extracts the production `parseWaitingUntil` / `isImpeded` from
`index.ts` (the same extraction the regression test uses), runs them under
Node, and compares against the Python engine for the same inputs. It exits
zero only when the two agree — i.e. after the fix lands. Before the fix it
exits non-zero and prints the divergent cells.

Skips (exit 0 with a SKIP notice) if `node` with `--experimental-strip-types`
is unavailable, mirroring tests/test_openclaw_session_start_hook.py.
"""

from __future__ import annotations

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
sys.path.insert(0, str(ROOT))

from goc.engine import Card, waiting_impedes  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

INDEX_TS = ROOT / "openclaw-plugin" / "index.ts"

# now > the rolled-forward instant of 2026-02-30 (= 2026-03-02), so the bug
# manifests as "not impeded" in TS while Python keeps the card impeded.
NOW_ISO = "2026-05-29T12:00:00Z"
NOW_DT = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)

# (waiting_on, waiting_until) cells. The first two are calendar-impossible but
# ISO-shaped — the cells this card targets. The rest are controls.
CASES = [
    ("", "2026-02-30"),
    ("external", "2026-02-30"),
    ("", "2099-01-01"),       # control: valid future date, impeded
    ("external", "2000-01-01"),  # control: valid elapsed date, resurfaces
    ("", "2026-99-99"),       # control: regex-rejected, impeded (already correct)
]


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


def _ts_impeded() -> list[bool]:
    src = INDEX_TS.read_text(encoding="utf-8")
    extracted = "\n\n".join(
        [
            _extract_const_line(src, "ISO_DATE_RE"),
            _extract_const_line(src, "ISO_DATETIME_UTC_RE"),
            _extract_fn(src, "parseWaitingUntil"),
            _extract_fn(src, "isImpeded"),
        ]
    )
    cases_js = ",".join(f'["{w}","{u}"]' for w, u in CASES)
    driver = (
        extracted
        + f'\nconst NOW = new Date("{NOW_ISO}");\n'
        + f"const CASES = [{cases_js}];\n"
        + "console.log(JSON.stringify("
        + "CASES.map(([w,u]) => isImpeded(w, u, NOW))));\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "driver.ts"
        f.write_text(driver, encoding="utf-8")
        out = subprocess.run(
            ["node", "--experimental-strip-types", str(f)],
            capture_output=True,
            text=True,
        )
    if out.returncode != 0:
        raise RuntimeError(f"node driver failed:\n{out.stderr}")
    import json

    return json.loads(out.stdout.strip())


def _py_impeded(waiting_on: str, waiting_until: str) -> bool:
    card = Card(
        title="probe",
        path=Path("/tmp/probe"),
        frontmatter={
            "waiting_on": waiting_on or None,
            "waiting_until": waiting_until or None,
        },
        body="",
        dod_open=0,
        dod_done=0,
    )
    return waiting_impedes(card, today=NOW_DT)


def main() -> int:
    if not _node_ok():
        print("SKIP: node with --experimental-strip-types not available")
        return 0
    ts = _ts_impeded()
    print(f"now = {NOW_ISO}\n")
    print(f"{'waiting_on':<12} {'waiting_until':<14} {'python':<8} {'ts':<8} agree")
    print("-" * 52)
    mismatches = 0
    for (w, u), ts_val in zip(CASES, ts):
        py_val = _py_impeded(w, u)
        agree = py_val == ts_val
        if not agree:
            mismatches += 1
        print(
            f"{w or '(none)':<12} {u:<14} {str(py_val):<8} {str(ts_val):<8} "
            f"{'OK' if agree else 'MISMATCH'}"
        )
    print()
    if mismatches:
        print(
            f"FAIL: {mismatches} cell(s) diverge — the TS port un-defers cards the "
            "engine keeps impeded."
        )
        return 1
    print("PASS: TS port agrees with the engine on every cell.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
