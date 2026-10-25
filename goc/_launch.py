"""Run the engine that sits next to this file — never one the working directory offers.

The plugin wrappers (`claude-plugin/bin/goc`, `codex-plugin/bin/goc`), the OpenClaw
tool handler and the engine's own re-invocations start this file by its path instead of
`python3 -m goc.cli`. `-m` puts the working directory first on `sys.path`, ahead of the
bundled package and the standard library, so a consumer repo's top-level `goc/` package
would replace the engine, and a repo-root module named after something the engine imports
(`dataclasses.py`) would run in its place.

Started as a file, Python puts this file's own directory (the `goc/` package) first
instead. The assignment below swaps it for the directory that holds the package before
anything else is imported (`sys` is built in, and the package holds no module named
`os`), so neither the working directory nor the package's own modules ever sit in front
of the standard library. Works on Python 3.10; `-P` would need 3.11.

Card: plugin-goc-wrapper-lets-repo-local-python-replace-the-bundled-engine
"""

import os
import sys

sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import runpy  # noqa: E402  (only after sys.path[0] no longer points at the package)

runpy.run_module("goc.cli", run_name="__main__", alter_sys=True)
