"""Reproduce: set_cadence.py's --help epilog advertises `<N>d (<=31)` while
interval_to_cron rejects any day interval above 30.

Exits 1 while the epilog's advertised day cap is rejected by the guard
(defect present); exits 0 once the advertised cap and the guard agree.
"""
import importlib.util
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


script = _repo_root() / "scripts" / "set_cadence.py"
spec = importlib.util.spec_from_file_location("set_cadence", script)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

m = re.search(r"<N>d \(<=(\d+)\)", script.read_text())
if not m:
    print("UNEXPECTED: epilog day-cap pattern `<N>d (<=NN)` not found")
    sys.exit(1)
cap = int(m.group(1))
print(f"epilog advertises day cap: {cap}")

try:
    cron = mod.interval_to_cron(f"{cap}d", 13)
    print(f"interval_to_cron('{cap}d') -> {cron!r}")
    print("OK: the advertised day cap is accepted by the guard")
    sys.exit(0)
except ValueError as e:
    print(f"interval_to_cron('{cap}d') -> ValueError: {e}")
    print("DEFECT: --help advertises a day interval the guard rejects")
    sys.exit(1)
