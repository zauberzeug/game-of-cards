"""Offline reproduction: the plugin-default `goc install` writes a
pre-commit stanza whose `entry: goc validate` (language: system) cannot
resolve on a host whose PATH has no global `goc` — the exact host shape
plugin mode is designed for.

Run: uv run python .game-of-cards/deck/install-writes-pre-commit-entry-that-fails-on-plugin-only-hosts/reproduce.py
Exits non-zero while the defect fires.
"""

import os
import shutil
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


def main() -> int:
    root = _repo_root()
    failed = False

    with tempfile.TemporaryDirectory() as tmp:
        consumer = Path(tmp) / "consumer"
        consumer.mkdir()
        subprocess.run(["git", "init", "-q", str(consumer)], check=True)

        env = dict(os.environ, PYTHONPATH=str(root))
        subprocess.run(
            [sys.executable, "-m", "goc.cli", "install", "--agents", "claude"],
            cwd=consumer,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        config = (consumer / ".game-of-cards" / "config.yaml").read_text()
        plugin_mode = "skills_source: plugin" in config
        print(f"[1] install pinned skills_source: plugin -> {plugin_mode}")

        pc = (consumer / ".pre-commit-config.yaml").read_text()
        entry = next(
            (line.split("entry:", 1)[1].strip() for line in pc.splitlines() if "entry:" in line),
            None,
        )
        print(f"[2] written .pre-commit-config.yaml entry: {entry!r} (language: system)")

        # pre-commit resolves a `language: system` entry's argv[0] via plain
        # PATH lookup. Model the plugin-only host: a PATH without any global
        # `goc` (plugin mode's bin/ prepend exists only inside Claude Code's
        # Bash tool, never for terminal/CI commits).
        bare_path = os.pathsep.join(["/usr/bin", "/bin"])
        resolved = shutil.which("goc", path=bare_path)
        print(f"[3] PATH used by pre-commit lookup has no 'goc': shutil.which -> {resolved}")

        if plugin_mode and entry and entry.split()[0] == "goc" and resolved is None:
            print(
                "[FAIL] plugin-default install wrote a pre-commit entry that "
                "cannot execute on this host"
            )
            failed = True
        else:
            print("[OK] written entry resolves (or install no longer writes a bare-goc entry)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
