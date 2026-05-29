"""Reproduce: vendored install no longer bakes `uv` into hook commands.

Pre-fix, `GOC_CLAUDE_HOOKS` registered `uv run python …` for every
hook event, which fails for pipx-only consumers (no `uv` on PATH).
Post-fix, the registrations use plain `python3 …` and run cleanly
without `uv`.

Confirms:

1. Hook scripts at `goc/templates/hooks/*.py` import only stdlib.
2. Plugin hooks at `claude-plugin/hooks/hooks.json` use plain `python3`.
3. Vendored install registers `python3 ...` via `GOC_CLAUDE_HOOKS`
   in `goc/install.py` — matching the plugin payload.
4. With `uv` stripped from PATH, the rendered `python3 …` command
   runs cleanly (rc=0).
"""

from __future__ import annotations

import json
import os
import re
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))


def main() -> int:
    hooks_dir = ROOT / "goc" / "templates" / "hooks"
    third_party = []
    stdlib_only_names = []
    for hook in sorted(hooks_dir.glob("*.py")):
        text = hook.read_text()
        imports = re.findall(r"^(?:import|from)\s+([\w.]+)", text, re.MULTILINE)
        non_stdlib = [m for m in imports if m.split(".")[0] == "goc"]
        if non_stdlib:
            third_party.append((hook.name, non_stdlib))
        else:
            stdlib_only_names.append(hook.name)
    assert not third_party, f"unexpected goc imports: {third_party}"
    print(f"hook scripts use only stdlib: {', '.join(stdlib_only_names)}")

    plugin_hooks_json = json.loads(
        (ROOT / "claude-plugin" / "hooks" / "hooks.json").read_text()
    )
    plugin_commands = [
        entry["command"]
        for groups in plugin_hooks_json["hooks"].values()
        for group in groups
        for entry in group["hooks"]
    ]
    assert all(c.startswith("python3 ") for c in plugin_commands), plugin_commands
    print(f"plugin hooks already use python3 — no uv: {plugin_commands}")

    from goc.install import GOC_CLAUDE_HOOKS  # noqa: E402

    vendored = {event: cmd for event, cmd in GOC_CLAUDE_HOOKS.items()}
    assert all(cmd.startswith("python3 ") for cmd in vendored.values()), vendored
    assert not any("uv" in cmd.split() for cmd in vendored.values()), vendored
    print("vendored install uses python3: " + " ".join(f"{e}={c}" for e, c in vendored.items()))

    session_cmd = GOC_CLAUDE_HOOKS["SessionStart"]
    env = {k: v for k, v in os.environ.items() if k != "PATH"}
    env["PATH"] = "/usr/bin:/bin"
    env["CLAUDE_PROJECT_DIR"] = str(ROOT)
    proc = subprocess.run(
        ["/bin/sh", "-c", session_cmd],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"expected vendored hook to run cleanly without uv on PATH; rc={proc.returncode}, "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    print(
        f"without uv on PATH the vendored command runs cleanly: "
        f"rc={proc.returncode}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
