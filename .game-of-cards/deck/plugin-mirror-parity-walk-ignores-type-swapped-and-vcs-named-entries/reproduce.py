"""Reproduce: the plugin-mirror parity walk passes four kinds of mirror drift.

Copies this repo's real `goc/` and `claude-plugin/` trees into a temp dir,
points `goc.engine.REPO_ROOT` at it, and calls
`validate_plugin_mirror_parity()` once per mirror shape, each on a fresh copy:

  a. type swap      — `claude-plugin/goc/engine.py` replaced by a directory
  b. broken symlink — `claude-plugin/goc/engine.py` replaced by a dangling link
  c. ignored name   — content drift inside a `goc/tags/` subtree
                      (`tags` is in `filecmp.DEFAULT_IGNORES`)
  d. outside link   — `claude-plugin/goc/engine.py` replaced by a WORKING
                      symlink to an identical file outside the payload

Each shape is drift a consumer would receive (a missing or broken file after
the marketplace extracts only `claude-plugin/`), so the tripwire should
report every one of them.

Exit codes: 0 = defect no longer fires (all four shapes reported),
1 = defect fires (at least one shape passes clean), 2 = the harness or a
precondition is broken. Two positive controls run first: the untouched copy
must report no drift, and a one-byte content edit to the mirrored
`engine.py` must be reported. If either fails, the probe cannot tell a blind
walk from a broken harness, so it exits 2.

Run with:  uv run python .game-of-cards/deck/plugin-mirror-parity-walk-ignores-type-swapped-and-vcs-named-entries/reproduce.py
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir() and (p / "goc" / "engine.py").is_file():
            return p
        p = p.parent
    raise RuntimeError("goc source tree not found")


REPO = _repo_root()
sys.path.insert(0, str(REPO))

import goc.engine as engine  # noqa: E402

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")


def _fresh_copy(tmp: Path) -> Path:
    root = Path(tempfile.mkdtemp(dir=tmp))
    shutil.copytree(REPO / "goc", root / "goc", ignore=IGNORE)
    shutil.copytree(REPO / "claude-plugin", root / "claude-plugin", ignore=IGNORE, symlinks=True)
    return root


def _parity(root: Path) -> list[str]:
    saved = engine.REPO_ROOT
    engine.REPO_ROOT = root
    try:
        return engine.validate_plugin_mirror_parity()
    finally:
        engine.REPO_ROOT = saved


def _type_swap(root: Path) -> None:
    target = root / "claude-plugin" / "goc" / "engine.py"
    target.unlink()
    target.mkdir()
    (target / "placeholder.txt").write_text("a directory where a file belongs\n")


def _broken_symlink(root: Path) -> None:
    target = root / "claude-plugin" / "goc" / "engine.py"
    target.unlink()
    os.symlink(root / "does-not-exist" / "engine.py", target)


def _ignored_name(root: Path) -> None:
    (root / "goc" / "tags").mkdir()
    (root / "claude-plugin" / "goc" / "tags").mkdir()
    (root / "goc" / "tags" / "module.py").write_text("VALUE = 1\n")
    (root / "claude-plugin" / "goc" / "tags" / "module.py").write_text("VALUE = 2\n")


def _outside_symlink(root: Path) -> None:
    target = root / "claude-plugin" / "goc" / "engine.py"
    outside = root / "outside"
    outside.mkdir()
    shutil.copyfile(target, outside / "engine.py")
    target.unlink()
    os.symlink(Path("..") / ".." / "outside" / "engine.py", target)
    assert target.is_symlink() and target.read_bytes() == (outside / "engine.py").read_bytes()


SHAPES = [
    ("a. type swap (file -> directory)", _type_swap),
    ("b. broken symlink in the mirror", _broken_symlink),
    ("c. content drift under goc/tags/", _ignored_name),
    ("d. working symlink to an outside file", _outside_symlink),
]


def main() -> int:
    if not (REPO / "claude-plugin" / "goc" / "engine.py").is_file():
        print("PRECONDITION: claude-plugin/goc/engine.py missing from the checkout")
        return 2
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)

        clean = _parity(_fresh_copy(tmp))
        print(f"control 1 — untouched copy        : {clean or 'no drift'}")
        if clean:
            print("HARNESS BROKEN: the untouched copy already reports drift")
            return 2

        root = _fresh_copy(tmp)
        with (root / "claude-plugin" / "goc" / "engine.py").open("a") as fh:
            fh.write("#")
        drift = _parity(root)
        print(f"control 2 — one-byte content edit : {drift or 'no drift'}")
        if not any("engine.py (differs)" in e for e in drift):
            print("HARNESS BROKEN: plain content drift was not reported")
            return 2

        missed = []
        for label, mutate in SHAPES:
            root = _fresh_copy(tmp)
            mutate(root)
            errors = _parity(root)
            print(f"{label:40}: {'REPORTED ' + repr(errors) if errors else 'passes clean'}")
            if not errors:
                missed.append(label)

    if missed:
        print(f"\nDEFECT PRESENT: {len(missed)} of {len(SHAPES)} mirror shapes pass the parity walk clean.")
        return 1
    print("\nDefect no longer fires: every mirror shape is reported.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
