"""Reproduce the auto-detect defect.

`_claude_plugin_present()` in `goc/engine.py` must return True for every
known Claude Code plugin layout that contains a `game-of-cards*/.../skills/`
payload. The defect: the original implementation descends only two levels,
so the modern marketplace layout (`cache/<marketplace>/<plugin>/<version>/skills/`)
is missed and `effective_skills_source()` falls through to `vendored`.

Pre-fix expected: Case 1 fails, script exits 1.
Post-fix expected: all cases pass, script exits 0.
"""

import os
import shutil
import signal
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


sys.path.insert(0, str(_repo_root()))


def _reset(plugins: Path) -> None:
    """Wipe and recreate the plugins root between cases."""
    if plugins.exists() or plugins.is_symlink():
        shutil.rmtree(plugins, ignore_errors=True)
    plugins.mkdir(parents=True)


def main() -> int:
    # Isolate from the dev machine's real ~/.claude/plugins/ tree.
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp)
        os.environ["HOME"] = str(tmp)
        os.environ.pop("CLAUDE_PLUGIN_ROOT", None)

        from goc.engine import _claude_plugin_present

        plugins = tmp / ".claude" / "plugins"

        # Case 1 — the actual defect: versioned marketplace layout.
        _reset(plugins)
        (plugins / "cache" / "zauberzeug-claude" / "game-of-cards" / "0.0.18" / "skills").mkdir(parents=True)
        if _claude_plugin_present():
            print("PASS  versioned layout (cache/<mkt>/<plugin>/<ver>/skills/)")
        else:
            failures.append("FAIL  versioned layout (cache/<mkt>/<plugin>/<ver>/skills/) not detected")

        # Case 2 — legacy 2-level: <root>/<marketplace>/game-of-cards*/skills/.
        _reset(plugins)
        (plugins / "some-marketplace" / "game-of-cards-foo" / "skills").mkdir(parents=True)
        if _claude_plugin_present():
            print("PASS  2-level layout (<root>/<mkt>/game-of-cards*/skills/)")
        else:
            failures.append("FAIL  2-level layout not detected (regression)")

        # Case 3 — legacy direct: <root>/game-of-cards*/skills/.
        _reset(plugins)
        (plugins / "game-of-cards" / "skills").mkdir(parents=True)
        if _claude_plugin_present():
            print("PASS  direct layout (<root>/game-of-cards*/skills/)")
        else:
            failures.append("FAIL  direct layout not detected (regression)")

        # Case 4 — no game-of-cards*/skills/ subtree → must return False.
        _reset(plugins)
        (plugins / "some-other-plugin" / "skills").mkdir(parents=True)
        if _claude_plugin_present():
            failures.append("FAIL  no payload, but returned True (false positive)")
        else:
            print("PASS  no payload → False")

        # Case 5 — symlink loop must not hang; valid payload alongside must still be found.
        _reset(plugins)
        loop_root = plugins / "cache" / "loop"
        loop_root.mkdir(parents=True)
        (loop_root / "back").symlink_to(plugins / "cache", target_is_directory=True)
        (plugins / "cache" / "good-mkt" / "game-of-cards" / "0.0.1" / "skills").mkdir(parents=True)

        signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("symlink loop hung the scan")))
        signal.alarm(5)
        try:
            ok = _claude_plugin_present()
        except TimeoutError as exc:
            failures.append(f"FAIL  {exc}")
        else:
            signal.alarm(0)
            if ok:
                print("PASS  symlink loop did not hang; valid payload detected")
            else:
                failures.append("FAIL  symlink-loop case: valid payload alongside not detected")

    if failures:
        print("")
        for f in failures:
            print(f, file=sys.stderr)
        return 1
    print("\nAll cases PASS — _claude_plugin_present() detects every known layout.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
