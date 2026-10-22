"""Regression guard: no plugin payload declares a Python package its bundled engine does not import.

`claude-plugin/` kept a `pyproject.toml` and a `uv.lock` for five months after
anything read them. They existed so the first `bin/goc` wrapper could run
`uv run --project` against the payload. The engine then dropped click and
pyyaml, and on 2026-05-09 the wrapper moved to `python3 -m goc.cli`, but both
files stayed behind and still declared click and pyyaml as the engine's
dependencies. Every marketplace install copied them into the user's plugin
cache, against the pure-stdlib contract the plugin README states
(`plugin-payload-still-declares-click-and-pyyaml-dependencies-the-engine-dropped`).

Neither side is restated here. A payload is a tracked directory that bundles
the engine as `<payload>/goc/`. The import set is read off that bundled copy
with `ast`, and the declared set off each Python dependency manifest or
lockfile the payload tracks, so a manifest a future runtime change leaves
behind turns the build red, and so does an engine change that strands one.
Only runtime declarations count: a build backend, a dev group or a lockfile's
transitive pins say nothing about what the engine imports. A manifest format
this file has no reader for fails outright instead of passing unread, since
nothing builds or installs a payload. The pre-fix `pyproject.toml` and
`uv.lock` are fed through the same check to prove it fires.
"""

from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from importlib.metadata import packages_distributions
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, which CI still covers
    tomllib = None

ROOT = Path(__file__).resolve().parents[1]

# Python dependency manifests and lockfiles, matched on the file name.
REQUIREMENTS = re.compile(r"requirements.*\.txt")
READABLE = re.compile(r"pyproject\.toml|uv\.lock|requirements.*\.txt")
UNREADABLE = re.compile(r"setup\.(py|cfg)|Pipfile(\.lock)?|(poetry|pdm)\.lock|pylock(\..+)?\.toml")

# `claude-plugin/pyproject.toml` as the fix removed it.
PRE_FIX_PYPROJECT = '''[project]
name = "goc-plugin-engine"
version = "0.0.0"
description = "Bundled GoC engine for the Claude Code plugin payload. Mirrors the goc/ package; do not edit directly — the byte-for-byte tripwire in .github/workflows/ci.yml fails on drift."
requires-python = ">=3.10"
dependencies = [
    "click>=8.1",
    "pyyaml>=6.0",
]

[project.scripts]
goc = "goc.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["goc"]

[tool.hatch.build.targets.wheel.force-include]
"goc/schema.yaml" = "goc/schema.yaml"
'''

# `claude-plugin/uv.lock` as the fix removed it, sdist and wheel hashes elided.
PRE_FIX_UV_LOCK = '''version = 1
revision = 3
requires-python = ">=3.10"

[[package]]
name = "click"
version = "8.3.3"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "colorama", marker = "sys_platform == 'win32'" },
]

[[package]]
name = "colorama"
version = "0.4.6"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "goc-plugin-engine"
version = "0.0.0"
source = { editable = "." }
dependencies = [
    { name = "click" },
    { name = "pyyaml" },
]

[package.metadata]
requires-dist = [
    { name = "click", specifier = ">=8.1" },
    { name = "pyyaml", specifier = ">=6.0" },
]

[[package]]
name = "pyyaml"
version = "6.0.3"
source = { registry = "https://pypi.org/simple" }
'''


def _git(cwd: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True
    ).stdout


def _git_checkout() -> bool:
    if shutil.which("git") is None:
        return False
    try:
        return _git(ROOT, "rev-parse", "--is-inside-work-tree").strip() == "true"
    except subprocess.CalledProcessError:
        return False


def tracked(root: Path) -> list[str]:
    """Tracked files that exist in the working tree, relative to `root`."""
    return sorted(p for p in _git(root, "ls-files", "-z").split("\0") if p and (root / p).is_file())


def payloads(files: list[str]) -> list[str]:
    """Top-level directories that bundle the engine as `<dir>/goc/`."""
    return sorted(p.split("/")[0] for p in files if re.fullmatch(r"[^/]+/goc/__init__\.py", p))


def third_party_imports(engine: Path) -> set[str]:
    """Top-level modules the engine imports that are neither stdlib nor goc itself."""
    modules: set[str] = set()
    for path in engine.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module.split(".")[0])
    return modules - set(sys.stdlib_module_names) - {"goc"}


def canonical(name: str) -> str:
    """PEP 503 normalization, so `PyYAML` and `pyyaml` name one distribution."""
    return re.sub(r"[-_.]+", "-", name).lower()


def imported_distributions(engine: Path) -> set[str]:
    """Canonical names of the distributions behind the engine's third-party imports.

    An installed module resolves through its distribution's metadata (`yaml` is
    PyYAML's); one that is not installed stands for a distribution of its own name.
    """
    providers = packages_distributions()
    return {canonical(dist) for module in third_party_imports(engine) for dist in providers.get(module, [module])}


def requirement_name(spec: str) -> str:
    """The distribution name a PEP 508 requirement string opens with."""
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
    return match.group(1) if match else spec.strip()


def declared(manifest: Path) -> list[str]:
    """The distributions a manifest or lockfile declares as runtime dependencies."""
    text = manifest.read_text(encoding="utf-8")
    if REQUIREMENTS.fullmatch(manifest.name):
        lines = (line.split(" #")[0].strip() for line in text.splitlines())
        return [requirement_name(line) for line in lines if line and not line.startswith(("#", "-"))]
    if tomllib is None:
        raise unittest.SkipTest(f"reading {manifest.name} needs tomllib (Python 3.11+)")
    data = tomllib.loads(text)
    if manifest.name == "pyproject.toml":
        project = data.get("project", {})
        specs = list(project.get("dependencies", []))
        for extra in project.get("optional-dependencies", {}).values():
            specs += extra
        return [requirement_name(spec) for spec in specs]
    # uv.lock: the project is the package locked from a local editable or
    # virtual source, and only its own entry lists what it declares.
    deps = []
    for package in data.get("package", []):
        if {"editable", "virtual"} & set(package.get("source", {})):
            deps += package.get("dependencies", [])
            for extra in package.get("optional-dependencies", {}).values():
                deps += extra
    return [dep["name"] for dep in deps]


def manifest_problems(root: Path) -> list[str]:
    """One line per runtime declaration in a payload that its bundled engine never imports."""
    files = tracked(root)
    problems = []
    for payload in payloads(files):
        manifests = [
            rel for rel in files
            if rel.startswith(f"{payload}/") and (READABLE.fullmatch(Path(rel).name) or UNREADABLE.fullmatch(Path(rel).name))
        ]
        if not manifests:
            continue
        imported = imported_distributions(root / payload / "goc")
        for rel in manifests:
            if UNREADABLE.fullmatch(Path(rel).name):
                problems.append(f"{rel}: no reader for this format, and nothing builds or installs a payload")
                continue
            for dist in sorted(set(declared(root / rel)), key=canonical):
                if canonical(dist) not in imported:
                    problems.append(f"{rel} lists {dist}, which {payload}/goc/ never imports")
    return problems


def scratch_problems(manifests: dict[str, str], engine: str | Path, payload: str = "plugin") -> list[str]:
    """`manifest_problems` over a scratch repo tracking one payload.

    `engine` is the bundled package to copy, or the source of a one-file stub.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundled = root / payload / "goc"
        if isinstance(engine, Path):
            shutil.copytree(engine, bundled, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            bundled.mkdir(parents=True)
            (bundled / "__init__.py").write_text(engine, encoding="utf-8")
        for name, text in manifests.items():
            (root / payload / name).write_text(text, encoding="utf-8")
        _git(root, "init", "-q")
        _git(root, "add", "-A")
        return manifest_problems(root)


@unittest.skipUnless(_git_checkout(), "not a git checkout")
class PayloadManifestTest(unittest.TestCase):
    def test_the_engine_bundling_payloads_are_found(self) -> None:
        """An empty payload list would make the check below vacuous."""
        self.assertIn("claude-plugin", payloads(tracked(ROOT)))

    def test_no_payload_lists_a_package_its_engine_does_not_import(self) -> None:
        self.assertEqual(manifest_problems(ROOT), [])


@unittest.skipUnless(shutil.which("git"), "git not on PATH")
@unittest.skipIf(tomllib is None, "reading TOML needs tomllib (Python 3.11+)")
class PreFixManifestFiresTest(unittest.TestCase):
    def test_pre_fix_manifest_and_lockfile_are_flagged_against_the_real_engine(self) -> None:
        problems = scratch_problems(
            {"pyproject.toml": PRE_FIX_PYPROJECT, "uv.lock": PRE_FIX_UV_LOCK},
            engine=ROOT / "claude-plugin" / "goc",
            payload="claude-plugin",
        )
        self.assertEqual(
            problems,
            [
                f"claude-plugin/{name} lists {dist}, which claude-plugin/goc/ never imports"
                for name in ("pyproject.toml", "uv.lock")
                for dist in ("click", "pyyaml")
            ],
        )


@unittest.skipUnless(shutil.which("git"), "git not on PATH")
@unittest.skipIf(tomllib is None, "reading TOML needs tomllib (Python 3.11+)")
class ManifestFormatTest(unittest.TestCase):
    # Each declares click at runtime, plus entries that must not count: an
    # option line, a build backend, a dev group and a transitive lock pin.
    FORMATS = {
        "requirements.txt": "# runtime\n-r base.txt\nclick>=8.1  # the CLI framework\n",
        "pyproject.toml": (
            '[project]\nname = "plugin"\nversion = "0"\ndependencies = ["click>=8.1"]\n\n'
            '[build-system]\nrequires = ["hatchling"]\n\n[dependency-groups]\ndev = ["pytest"]\n'
        ),
        "uv.lock": (
            'version = 1\nrequires-python = ">=3.10"\n\n'
            '[[package]]\nname = "click"\nversion = "8.3.3"\nsource = { registry = "https://pypi.org/simple" }\n'
            'dependencies = [{ name = "colorama" }]\n\n'
            '[[package]]\nname = "colorama"\nversion = "0.4.6"\nsource = { registry = "https://pypi.org/simple" }\n\n'
            '[[package]]\nname = "plugin"\nversion = "0"\nsource = { editable = "." }\n'
            'dependencies = [{ name = "click" }]\n'
        ),
    }

    def test_each_format_flags_a_package_the_engine_does_not_import(self) -> None:
        for name, text in self.FORMATS.items():
            with self.subTest(manifest=name):
                self.assertEqual(
                    scratch_problems({name: text}, engine="import json\n"),
                    [f"plugin/{name} lists click, which plugin/goc/ never imports"],
                )

    def test_a_package_the_engine_imports_is_not_flagged(self) -> None:
        for name, text in self.FORMATS.items():
            with self.subTest(manifest=name):
                self.assertEqual(scratch_problems({name: text}, engine="import click.testing\n"), [])

    def test_a_format_without_a_reader_fails_outright(self) -> None:
        self.assertEqual(
            scratch_problems({"setup.py": "from setuptools import setup\n\nsetup()\n"}, engine="import click\n"),
            ["plugin/setup.py: no reader for this format, and nothing builds or installs a payload"],
        )


if __name__ == "__main__":
    unittest.main()
