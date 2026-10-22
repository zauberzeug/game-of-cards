"""Compare the plugin payload's declared dependencies with what its engine imports.

`claude-plugin/` ships whatever is tracked under it (the marketplace entry
installs `source: ./claude-plugin`). This script reads the dependency set the
payload's `pyproject.toml` / `uv.lock` declare, the set the root package
declares, the third-party modules the bundled engine actually imports, and
whether anything in the payload still reads the manifest.

Exits 0 when the payload declares no dependency the bundled engine does not
import (including when the manifest and lockfile are gone).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError("repo root (.game-of-cards/) not found")


ROOT = _repo_root()
PLUGIN = ROOT / "claude-plugin"


def _declared(pyproject: Path) -> list[str]:
    if not pyproject.is_file():
        return []
    text = pyproject.read_text(encoding="utf-8")
    block = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.S | re.M)
    if block is None:
        return []
    return re.findall(r'"([A-Za-z0-9_.-]+)', block.group(1))


def _locked(lock: Path) -> list[str]:
    if not lock.is_file():
        return []
    return re.findall(r'^name = "([^"]+)"', lock.read_text(encoding="utf-8"), re.M)


def _engine_imports(pkg: Path) -> set[str]:
    stdlib = set(sys.stdlib_module_names)
    found: set[str] = set()
    for path in pkg.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                top = name.split(".")[0]
                if top not in stdlib and top not in {"goc", "__future__"}:
                    found.add(top)
    return found


def main() -> int:
    module_of = {"pyyaml": "yaml"}
    plugin_deps = _declared(PLUGIN / "pyproject.toml")
    root_deps = _declared(ROOT / "pyproject.toml")
    locked = [n for n in _locked(PLUGIN / "uv.lock") if n != "goc-plugin-engine"]
    imported = _engine_imports(PLUGIN / "goc")
    wrapper = (PLUGIN / "bin" / "goc").read_text(encoding="utf-8")
    readers = [
        str(p.relative_to(ROOT))
        for p in PLUGIN.rglob("*")
        if p.is_file() and p.suffix in {"", ".json", ".sh", ".py"}
        and "pyproject" in p.read_text(encoding="utf-8", errors="replace")
        and "goc" not in p.relative_to(PLUGIN).parts[:1]
    ]

    print(f"claude-plugin/pyproject.toml dependencies : {plugin_deps or 'none (file absent or empty)'}")
    print(f"claude-plugin/uv.lock packages            : {locked or 'none (file absent)'}")
    print(f"root pyproject.toml dependencies          : {root_deps or '[] (pure stdlib)'}")
    print(f"third-party imports in claude-plugin/goc/ : {sorted(imported) or 'none'}")
    print(f"bin/goc runs uv                           : {'uv run' in wrapper}")
    print(f"payload files reading the manifest        : {readers or 'none'}")

    unused = sorted({d for d in plugin_deps + locked if module_of.get(d, d) not in imported})
    print()
    print(f"declared or locked but never imported     : {unused or 'none'}")
    return 1 if unused else 0


if __name__ == "__main__":
    sys.exit(main())
