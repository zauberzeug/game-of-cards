"""Reproduce: `goc --json --slim` emits waiting_on but not waiting_until.

Picks an impeded card (waiting_on set) from the current deck and compares
the slim record against the full record. Exits non-zero while the slim
emitter is missing waiting_until; exits zero once the fix lands.
"""

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


def _run_json(slim: bool) -> list[dict]:
    cmd = ["uv", "run", "goc", "--status", "all", "--json"]
    if slim:
        cmd.append("--slim")
    out = subprocess.check_output(cmd, cwd=_repo_root())
    return json.loads(out)


def main() -> int:
    slim = _run_json(slim=True)
    full = _run_json(slim=False)

    impeded_slim = next((r for r in slim if r.get("waiting_on")), None)
    if impeded_slim is None:
        print("SKIP: no card in this deck carries a waiting_on overlay")
        return 0

    title = impeded_slim["title"]
    full_record = next(r for r in full if r["title"] == title)

    print(f"slim record for {title}:")
    print(f"  keys:           {sorted(impeded_slim.keys())}")
    print(f"  waiting_on:     {impeded_slim.get('waiting_on')!r}")
    print(
        f"  waiting_until:  "
        f"{impeded_slim.get('waiting_until', '<MISSING>')!r}"
        if "waiting_until" in impeded_slim
        else "  waiting_until:  <MISSING>"
    )
    print(f"full record (same card):")
    print(f"  waiting_on:     {full_record.get('waiting_on')!r}")
    print(f"  waiting_until:  {full_record.get('waiting_until')!r}")

    if "waiting_until" not in impeded_slim:
        print("FAIL: slim record drops waiting_until; full record keeps it")
        return 1
    print("OK: slim record exposes both halves of the impediment overlay")
    return 0


if __name__ == "__main__":
    sys.exit(main())
