"""Reproduce: the vendored engine's __version__ is hijacked by a co-installed
game-of-cards distribution's metadata.

`goc/__init__.py` sets a `__version__` literal, then unconditionally
overwrites it with `importlib.metadata.version("game-of-cards")`. The
metadata lookup resolves the *distribution* record from the interpreter's
site-packages, not the package actually imported — so an engine loaded from
PYTHONPATH (the claude/codex/openclaw plugin wrappers all do this) reports
whatever version a coexisting pip/pipx install happens to be, not its own
literal.

This script proves it offline: it fabricates a `game_of_cards-9.9.9.dist-info`
directory (metadata only, no code) on the import path, imports the repo's own
`goc` package in a subprocess, and shows the repo engine reporting 9.9.9.

Exits 0 with a verdict either way:
  DEFECT REPRODUCED — metadata from the foreign dist-info won.
  DEFECT FIXED      — the engine kept its own literal.
"""

import ast
import os
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


def _literal_version(init_py: Path) -> str:
    for node in ast.parse(init_py.read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    return node.value.value
    raise RuntimeError("__version__ literal not found in goc/__init__.py")


def main() -> int:
    root = _repo_root()
    literal = _literal_version(root / "goc" / "__init__.py")

    with tempfile.TemporaryDirectory() as tmp:
        dist_info = Path(tmp) / "game_of_cards-9.9.9.dist-info"
        dist_info.mkdir()
        (dist_info / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: game-of-cards\nVersion: 9.9.9\n"
        )

        env = dict(os.environ)
        env["PYTHONPATH"] = f"{root}{os.pathsep}{tmp}"
        out = subprocess.run(
            [
                sys.executable,
                "-c",
                "import goc; print(goc.__file__); print(goc.__version__)",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        loaded_file, reported = out.stdout.strip().splitlines()

    print(f"engine imported from : {loaded_file}")
    print(f"__version__ literal  : {literal}")
    print(f"reported __version__ : {reported}")

    if Path(loaded_file).resolve() != (root / "goc" / "__init__.py").resolve():
        print("HARNESS ERROR: subprocess did not import the repo engine")
        return 1

    if reported == "9.9.9":
        print(
            "DEFECT REPRODUCED: the repo's own engine reports the co-installed "
            "distribution's metadata version, not its own literal"
        )
    elif reported == literal:
        print("DEFECT FIXED: engine kept its own literal despite foreign dist-info")
    else:
        print(f"HARNESS ERROR: unexpected reported version {reported!r}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
