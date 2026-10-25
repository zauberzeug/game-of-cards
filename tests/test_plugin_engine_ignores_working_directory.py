"""Regression guard for plugin-goc-wrapper-lets-repo-local-python-replace-the-bundled-engine.

Every way a plugin starts the bundled engine must run *that* engine, whatever the
working directory holds. `python -m goc.cli` put the working directory first on
`sys.path`: a consumer repo's own top-level `goc/` package replaced the engine, and a
repo-root module named after something the engine imports (`dataclasses.py`) ran
before it. The starts covered here:

- `claude-plugin/bin/goc` and `codex-plugin/bin/goc`, run by absolute path;
- the OpenClaw tool handler's command — `gocCommand` is extracted from
  `openclaw-plugin/index.ts` and run under node, the same pattern as
  `tests/test_openclaw_skill_serving.py`, and the committed esbuild output must
  carry the same form;
- the command the engine uses to re-invoke itself (`goc.engine._goc_command`).

Each start runs `--version` in a scratch directory that holds one impostor at a time
and must print the real version without the impostor leaving its marker.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_TS = ROOT / "openclaw-plugin" / "index.ts"
DIST_JS = ROOT / "openclaw-plugin" / "dist" / "index.js"
WRAPPERS = [ROOT / "claude-plugin" / "bin" / "goc", ROOT / "codex-plugin" / "bin" / "goc"]

IMPOSTORS = {
    "goc-package": {
        "goc/__init__.py": "import os\nopen(os.environ['IMPOSTOR_MARKER'], 'a').write('goc-package\\n')\n",
        "goc/cli.py": "print('IMPOSTOR-ENGINE')\n",
    },
    "stdlib-shadow": {
        "dataclasses.py": (
            "import os\nopen(os.environ['IMPOSTOR_MARKER'], 'a').write('stdlib-shadow\\n')\n"
            "raise RuntimeError('shadowed stdlib module from the working directory')\n"
        ),
    },
}


def _engine_version() -> str:
    text = (ROOT / "goc" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r"__version__\s*=\s*[\"']([^\"']+)[\"']", text)
    if not match:
        raise RuntimeError("goc/__init__.py carries no __version__")
    return match.group(1)


def _node_supports_strip_types() -> bool:
    if shutil.which("node") is None:
        return False
    probe = subprocess.run(
        ["node", "--experimental-strip-types", "-e", "const x: number = 1;"],
        capture_output=True,
    )
    return probe.returncode == 0


def _extract_top_level_function(src: str, name: str) -> str:
    pattern = rf"^(?:async )?function {re.escape(name)}\b.*?(?=^\}}$)\}}$"
    match = re.search(pattern, src, re.DOTALL | re.MULTILINE)
    if not match:
        raise AssertionError(f"function {name} not found in {INDEX_TS}")
    return match.group(0)


class _HostileWorkingDirectory(unittest.TestCase):
    """Runs a command in a scratch cwd holding one impostor at a time."""

    def run_in_each_hostile_cwd(self, argv: list[str], extra_env: dict[str, str] | None = None) -> None:
        for name, files in IMPOSTORS.items():
            with self.subTest(impostor=name), tempfile.TemporaryDirectory() as tmp:
                cwd = Path(tmp) / "consumer-repo"
                for rel, content in files.items():
                    path = cwd / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                marker = Path(tmp) / "impostor-ran.txt"
                env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
                env.update(extra_env or {})
                env["IMPOSTOR_MARKER"] = str(marker)
                result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
                ran = marker.read_text(encoding="utf-8").split() if marker.exists() else []
                self.assertEqual(ran, [], f"{argv} ran the impostor from its working directory")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"goc, version {_engine_version()}", result.stdout)


class PluginWrappersRunTheBundledEngine(_HostileWorkingDirectory):
    def test_claude_and_codex_wrappers(self) -> None:
        for wrapper in WRAPPERS:
            with self.subTest(wrapper=wrapper.relative_to(ROOT).as_posix()):
                self.assertTrue(wrapper.exists(), f"missing wrapper: {wrapper}")
                self.run_in_each_hostile_cwd([str(wrapper), "--version"])

    def test_wrappers_add_no_empty_pythonpath_element(self) -> None:
        # `"${PLUGIN_ROOT}:${PYTHONPATH:-}"` with PYTHONPATH unset left a trailing empty
        # element, which Python reads as the working directory.
        for wrapper in WRAPPERS:
            text = wrapper.read_text(encoding="utf-8")
            self.assertNotIn("${PYTHONPATH:-}", text, wrapper.relative_to(ROOT).as_posix())


class EngineReinvocationRunsTheSameEngine(_HostileWorkingDirectory):
    def test_goc_command(self) -> None:
        sys.path.insert(0, str(ROOT))  # this repo's own test process, not a plugin start
        try:
            from goc.engine import _goc_command
        finally:
            sys.path.remove(str(ROOT))
        self.run_in_each_hostile_cwd([*_goc_command(), "--version"])


@unittest.skipUnless(_node_supports_strip_types(), "node with --experimental-strip-types not available")
class OpenclawHandlerRunsTheVendoredEngine(_HostileWorkingDirectory):
    def openclaw_argv(self) -> list[str]:
        src = INDEX_TS.read_text(encoding="utf-8")
        program = "\n".join([
            'import { resolve } from "node:path";',
            f"const VENDORED_GOC_PATH = {json.dumps(str(ROOT / 'openclaw-plugin'))};",
            _extract_top_level_function(src, "gocCommand"),
            'console.log(JSON.stringify(gocCommand(["--version"])));',
        ])
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "goc-command.ts"
            script.write_text(program, encoding="utf-8")
            result = subprocess.run(
                ["node", "--experimental-strip-types", str(script)],
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_handler_command(self) -> None:
        argv = self.openclaw_argv()
        self.assertEqual(argv[0], "python3")
        python = shutil.which("python3") or sys.executable
        self.run_in_each_hostile_cwd(
            [python, *argv[1:]],
            {"PYTHONPATH": str(ROOT / "openclaw-plugin")},
        )

    def test_committed_bundle_matches_the_source(self) -> None:
        # The gateway loads dist/index.js, not index.ts.
        bundle = DIST_JS.read_text(encoding="utf-8")
        self.assertNotRegex(bundle, r'"python3",\s*"-m",\s*"goc\.cli"')
        self.assertIn('"_launch.py"', bundle)


class NoShippedStartUsesDashM(unittest.TestCase):
    """Static tripwire over the shipped starts; the behavioural tests above prove the fix."""

    SHAPES = (re.compile(r"-m\s+goc\.cli"), re.compile(r"[\"']-m[\"']\s*,\s*[\"']goc\.cli[\"']"))

    def offenders(self, text: str) -> list[str]:
        found = []
        for line in text.splitlines():
            code = line.strip()
            if code.startswith(("#", "//", "*")):
                continue
            if any(shape.search(code) for shape in self.SHAPES):
                found.append(code)
        return found

    def test_the_tripwire_sees_both_shapes(self) -> None:
        self.assertTrue(self.offenders('exec env PYTHONPATH="$R" "$PYTHON" -m goc.cli "$@"'))
        self.assertTrue(self.offenders('["python3", "-m", "goc.cli", ...args],'))
        self.assertTrue(self.offenders('move_cmd = [sys.executable, "-m", "goc.cli", "move"]'))
        self.assertFalse(self.offenders('exec "$PYTHON" "$PLUGIN_ROOT/goc/_launch.py" "$@"'))

    def test_shipped_starts(self) -> None:
        for path in [*WRAPPERS, INDEX_TS, DIST_JS, ROOT / "goc" / "engine.py"]:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertEqual(self.offenders(path.read_text(encoding="utf-8")), [])


if __name__ == "__main__":
    unittest.main()
