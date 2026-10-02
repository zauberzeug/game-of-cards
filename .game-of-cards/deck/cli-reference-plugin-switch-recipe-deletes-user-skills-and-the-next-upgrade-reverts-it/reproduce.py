#!/usr/bin/env python3
"""Follow goc.md's vendored -> plugin switch recipe and check where the repo ends up.

Reads the recipe out of goc.md § "Coexistence with the repo-local harness"
rather than restating it, so the same script reproduces the defect against the
old text and confirms the fix against the new one:

  - a hand-delete recipe ("remove `.claude/skills/`, `.claude/hooks/`, and the
    GoC hook entries from `.claude/settings.json`") is applied literally;
  - a config recipe (`skills_source: <value>` in `.game-of-cards/config.yaml`,
    then `goc upgrade`) sets the key and runs `goc upgrade`, answering `y` to
    the cleanup prompt.

Fixture: a scratch `goc install --local-skills` repo holding one user-authored
skill. After the recipe, one more routine `goc upgrade` runs with empty stdin
(goc.md § "Upgrade an install" recommends one after every CLI upgrade) — the
recipe has to survive it.

Exits 0 when the repo ends in plugin mode with the user skill intact, 1 when it
does not (the defect), 2 when goc.md gives neither recipe shape. An optional
argument names a different copy of goc.md to read the recipe from, e.g. the
pre-fix text: `git show <rev>:goc.md > /tmp/goc.md && reproduce.py /tmp/goc.md`.
"""

from __future__ import annotations

import json
import os
import re
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

from goc.install import GOC_CLAUDE_HOOKS, _strip_goc_settings_entries, skill_for_agent  # noqa: E402

SECTION = "### Coexistence with the repo-local harness"
USER_SKILL = "my-own-skill"
USER_SKILL_BODY = "---\nname: my-own-skill\ndescription: a skill the repo wrote itself\n---\n\nbody\n"
GOC_SKILLS = sorted(
    p.name
    for p in (ROOT / "goc" / "templates" / "skills").iterdir()
    if p.is_dir() and skill_for_agent(p.name, "claude")
)
GOC_HOOK_FILES = sorted(
    m.group(1) for cmd in GOC_CLAUDE_HOOKS.values() if (m := re.search(r"(\.claude/hooks/[\w.-]+\.py)", cmd))
)


def _section(doc: Path) -> str:
    text = doc.read_text()
    start = text.index(SECTION)
    end = text.find("\n## ", start + len(SECTION))
    return text[start : end if end != -1 else len(text)]


def _goc(repo: Path, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=repo,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
    )


def _goc_commands(settings: Path) -> list[str]:
    if not settings.is_file():
        return []
    hooks = json.loads(settings.read_text()).get("hooks", {})
    goc = set(GOC_CLAUDE_HOOKS.values())
    return sorted(
        h["command"]
        for groups in hooks.values()
        for group in groups
        for h in group.get("hooks", [])
        if h.get("command") in goc
    )


def _state(repo: Path) -> dict[str, object]:
    skills = repo / ".claude" / "skills"
    pin = re.search(r"^skills_source:\s*(\S+)", (repo / ".game-of-cards" / "config.yaml").read_text(), re.M)
    user = skills / USER_SKILL / "SKILL.md"
    return {
        "user skill intact": user.is_file() and user.read_text() == USER_SKILL_BODY,
        "GoC skill dirs": sum((skills / name).is_dir() for name in GOC_SKILLS),
        "GoC hook scripts": sum((repo / rel).is_file() for rel in GOC_HOOK_FILES),
        "GoC settings hook entries": len(_goc_commands(repo / ".claude" / "settings.json")),
        "skills_source": pin.group(1) if pin else None,
    }


def _report(step: str, repo: Path) -> dict[str, object]:
    state = _state(repo)
    print(f"  {step:<44} {state}")
    return state


def main() -> int:
    section = _section(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "goc.md")
    hand_delete = re.search(r"remove `\.claude/skills/`", section, re.I)
    # The config recipe is the numbered steps, not any `skills_source:` mention:
    # the section also names the `vendored` pin the repo starts from.
    steps = re.findall(r"^\d+\. (.+)$", section, re.M)
    switch = [m.group(1) for step in steps if (m := re.match(r"Set `skills_source: (\w+)`", step))]
    upgrade_step = any("`goc upgrade`" in step and "answer `y`" in step for step in steps)
    if hand_delete:
        recipe = "hand-delete .claude/skills/, .claude/hooks/ and the GoC settings entries"
    elif switch and upgrade_step:
        recipe = f"set skills_source: {switch[0]}, then goc upgrade (answer y)"
    else:
        print("goc.md's coexistence section gives no recognisable switch recipe.")
        return 2
    print(f"goc.md recipe: {recipe}")

    work = Path(tempfile.mkdtemp(prefix="goc-switch-"))
    try:
        repo = work / "consumer"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
        install = _goc(repo, "install", "--local-skills", "--agents", "claude")
        if install.returncode:
            print(install.stdout + install.stderr)
            return 2
        (repo / ".claude" / "skills" / USER_SKILL).mkdir()
        (repo / ".claude" / "skills" / USER_SKILL / "SKILL.md").write_text(USER_SKILL_BODY)
        _report("install --local-skills + one user skill", repo)

        if hand_delete:
            shutil.rmtree(repo / ".claude" / "skills")
            shutil.rmtree(repo / ".claude" / "hooks")
            _strip_goc_settings_entries(repo / ".claude" / "settings.json")
            _report("hand-delete", repo)
            ran = _goc(repo, "upgrade")
        else:
            config = repo / ".game-of-cards" / "config.yaml"
            config.write_text(
                re.sub(r"^skills_source:.*$", f"skills_source: {switch[0]}", config.read_text(), flags=re.M)
            )
            ran = _goc(repo, "upgrade", stdin="y\n")
        _report(f"the recipe's goc upgrade (exit {ran.returncode})", repo)

        routine = _goc(repo, "upgrade")
        end = _report(f"one more routine goc upgrade (exit {routine.returncode})", repo)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    in_plugin_mode = (
        end["skills_source"] == "plugin"
        and end["GoC skill dirs"] == 0
        and end["GoC hook scripts"] == 0
        and end["GoC settings hook entries"] == 0
    )
    if in_plugin_mode and end["user skill intact"]:
        print("\nOK: the documented recipe ends in plugin mode with the user skill intact.")
        return 0
    if not end["user skill intact"]:
        print("\nFAIL: the documented recipe deleted the repo's own skill.")
    if not in_plugin_mode:
        print(
            "FAIL: the repo is not in plugin mode after a routine goc upgrade — "
            f"skills_source={end['skills_source']}, {end['GoC skill dirs']} GoC skill dirs, "
            f"{end['GoC hook scripts']} hook scripts, {end['GoC settings hook entries']} settings entries."
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
