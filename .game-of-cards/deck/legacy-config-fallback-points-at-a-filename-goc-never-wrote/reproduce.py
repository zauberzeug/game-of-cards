#!/usr/bin/env python3
"""legacy-config-fallback-points-at-a-filename-goc-never-wrote

`LEGACY_DECK_CONFIG_FILE` points at `.claude/config.yaml` (goc/engine.py:150),
but the pre-move config home was `.claude/deck-config.yaml` — the name
goc/install.py:1071 migrates on upgrade and the name commit fe651865 promised
to keep reading ("still reading legacy .claude/deck-config.yaml"). A legacy
repo's authored closure checks and `workflow.auto_commit: false` opt-out are
silently ignored by `load_deck_config()` until an upgrade happens to migrate
the file.

Exits ZERO when the real legacy filename is read (defect fixed);
exits NONZERO while the defect fires.
"""

import json
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


ROOT = _repo_root()
LEGACY_CONTENT = (
    "workflow:\n"
    "  auto_commit: false\n"
    "layer_2_project_dod:\n"
    "  - name: project-test-suite\n"
    '    cmd: "true"\n'
)
PROBE = "import json, goc.engine as e; print(json.dumps(e.load_deck_config()))"


def load_config_with(filename: str) -> dict:
    """Run engine.load_deck_config() in a sandbox repo whose only config
    lives at .claude/<filename>."""
    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        subprocess.run(["git", "init", "-q", "."], cwd=target, check=True)
        (target / ".game-of-cards" / "deck").mkdir(parents=True)
        (target / ".claude").mkdir()
        (target / ".claude" / filename).write_text(LEGACY_CONTENT)
        env = {**os.environ, "PYTHONPATH": str(ROOT)}
        out = subprocess.run(
            [sys.executable, "-c", PROBE],
            cwd=target, env=env, capture_output=True, text=True, check=True,
        )
        return json.loads(out.stdout)


def has_authored_check(config: dict) -> bool:
    return any(
        isinstance(check, dict) and check.get("name") == "project-test-suite"
        for check in config.get("layer_2_project_dod", [])
    )


def main() -> int:
    real_legacy = load_config_with("deck-config.yaml")  # what goc wrote pre-move
    wrong_name = load_config_with("config.yaml")  # what the engine looks for
    print("load_deck_config() with real legacy .claude/deck-config.yaml:")
    print(f"  {real_legacy}")
    print("load_deck_config() with the engine's expected .claude/config.yaml:")
    print(f"  {wrong_name}")
    if not has_authored_check(wrong_name):
        print("UNEXPECTED: control scenario failed — fallback loader itself broken")
        return 2
    if has_authored_check(real_legacy):
        print("PASS: legacy .claude/deck-config.yaml is read by the fallback")
        return 0
    print(
        "FAIL: authored legacy config silently ignored — layer-2 closure checks "
        "and the auto_commit opt-out vanish (the engine fallback reads a "
        "filename goc never wrote)"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
