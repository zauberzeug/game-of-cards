"""Reproduce: openclaw.plugin.json omits the ported `upgrade` skill.

Compares the ported skill-dir set under openclaw-plugin/skills/ to the
manifest's `skills` array and checks the description's skill count.
Exits non-zero while the defect is present, zero once the manifest is
brought in sync.
"""
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


def main() -> int:
    root = _repo_root()
    plugin = root / "openclaw-plugin"
    manifest = json.loads((plugin / "openclaw.plugin.json").read_text())

    ported = {
        d.name
        for d in (plugin / "skills").iterdir()
        if d.is_dir() and d.name != "__pycache__"
    }
    registered = {s.split("/", 1)[-1] for s in manifest.get("skills", [])}

    print(
        f"ported skill dirs ({len(ported)}): "
        + ", ".join(sorted(ported))
    )
    print(
        f"manifest skills ({len(registered)}): "
        + ", ".join(sorted(registered))
    )

    missing = ported - registered
    extra = registered - ported
    print(f"ported but NOT registered in manifest: {missing or '{}'}")
    print(f"registered but NOT ported: {extra or '{}'}")

    m = re.search(r"(\d+)\s+deck skills", manifest.get("description", ""))
    claimed = int(m.group(1)) if m else None
    print(f"manifest description claims: {claimed} deck skills "
          f"(actual ported: {len(ported)})")

    ok = not missing and not extra and claimed == len(ported)
    print("DEFECT CONFIRMED" if not ok else "OK — manifest in sync")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
