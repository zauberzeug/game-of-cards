"""Reproduce: goc upgrade leaves stale prior-version hook registrations in
.claude/settings.json.

Both `_merge_claude_settings` and `_strip_goc_settings_entries` identify a
GoC-owned hook registration by its *current* command string
(`GOC_CLAUDE_HOOKS.values()`). A registration GoC shipped under a different
command string in a prior version (the direct consequence of renaming/repathing
a hook file) is invisible to both:

  - merge: dedup misses it, so the current command is appended as a DUPLICATE
    group while the stale one survives.
  - strip: removal misses it, so cleanup cannot delete it.

Exits non-zero while the defect is present.
"""
import json
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
from goc import install  # noqa: E402


def _commands(settings_path: Path, event: str) -> list[str]:
    data = json.loads(settings_path.read_text())
    return [
        h["command"]
        for g in data.get("hooks", {}).get(event, [])
        if isinstance(g, dict) and isinstance(g.get("hooks"), list)
        for h in g["hooks"]
        if isinstance(h, dict) and "command" in h
    ]


def main() -> int:
    event = "SessionStart"
    current = install.GOC_CLAUDE_HOOKS[event]
    # A plausible PRIOR-VERSION GoC command string: same shape, renamed file.
    stale = current.replace(
        "/deck_session_start.py", "/OLD_deck_session_start.py"
    )
    assert stale != current and stale not in install.GOC_CLAUDE_HOOKS.values()

    # A genuinely user-authored registration that must NEVER be touched.
    user_cmd = "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/my_own_hook.py"

    failures = []

    with tempfile.TemporaryDirectory() as d:
        # ---- merge side ----
        sp = Path(d) / "settings.json"
        sp.write_text(json.dumps({
            "hooks": {event: [
                {"hooks": [{"type": "command", "command": stale}]},
                {"hooks": [{"type": "command", "command": user_cmd}]},
            ]}
        }, indent=2))
        install._merge_claude_settings(sp)
        cmds = _commands(sp, event)
        print(f"merge: {event} commands after merge = {cmds}")
        if stale in cmds:
            failures.append("BUG: stale prior-version registration survived merge")
        if cmds.count(current) > 1:
            failures.append("BUG: current command appended as a duplicate group")
        if user_cmd not in cmds:
            failures.append("REGRESSION: user-authored registration lost on merge")

        # ---- strip side ----
        sp2 = Path(d) / "settings2.json"
        sp2.write_text(json.dumps({
            "hooks": {event: [
                {"hooks": [{"type": "command", "command": stale}]},
                {"hooks": [{"type": "command", "command": user_cmd}]},
            ]}
        }, indent=2))
        install._strip_goc_settings_entries(sp2)
        cmds2 = _commands(sp2, event)
        print(f"strip: {event} commands after strip = {cmds2}")
        if stale in cmds2:
            failures.append("BUG: stale prior-version registration survived strip")
        if user_cmd not in cmds2:
            failures.append("REGRESSION: user-authored registration removed by strip")

    print()
    if failures:
        for f in failures:
            print(f)
        print("\nDEFECT PRESENT")
        return 1
    print("ok: no stale prior-version registration survives; user content intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
