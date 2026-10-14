#!/usr/bin/env python3
"""The Python hooks in a linked worktree of a shared-deck repo.

Builds a primary repo with `goc install --agents claude`, uncomments the
config template's own `worktree_deck: shared` line, commits, and adds a linked
worktree. From the linked worktree it creates and claims a card with `goc`,
which lands in the primary tree's deck. Then it runs both hooks with `cwd` =
the linked worktree, the way the host calls them:

- `deck_session_start.py` must name the claimed card, as it does for `cwd` =
  the primary tree.
- `pattern_generalization_check.py` must read the config `goc` reads. The
  primary tree's config enables the hook after the worktree was branched, so
  the linked checkout still carries `pattern_generalization_check: false`; on
  a code-mutating turn the hook must block (exit 2), as it does for `cwd` =
  the primary tree.

Exits 0 when both hooks follow the shared deck, 1 while either reads the
linked worktree's own checkout instead.
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
HOOKS = ROOT / "goc" / "templates" / "hooks"
CARD = "claimed-card-from-worktree"


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="goc-shared-deck-hooks-")).resolve()
    env = {k: v for k, v in os.environ.items()
           if k not in ("GOC_WORKTREE_DECK", "GOC_WORKER", "CLAUDE_PROJECT_DIR",
                        "CODEX_PROJECT_DIR", "CLAUDE_PLUGIN_ROOT")}
    env.update(PYTHONPATH=str(ROOT), HOME=str(work / "home"),
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    (work / "home").mkdir()

    def run(cwd: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(list(args), cwd=cwd, env=env, input=stdin,
                              capture_output=True, text=True)

    def goc(cwd: Path, *args: str) -> subprocess.CompletedProcess:
        r = run(cwd, sys.executable, "-m", "goc.cli", *args)
        if r.returncode != 0:
            raise SystemExit(f"goc {' '.join(args)} failed:\n{r.stdout}{r.stderr}")
        return r

    try:
        primary = work / "primary"
        primary.mkdir()
        for args in (("init", "-q"), ("config", "user.email", "probe@example.invalid"),
                     ("config", "user.name", "probe"), ("config", "commit.gpgsign", "false")):
            run(primary, "git", *args)
        goc(primary, "install", "--agents", "claude")
        config = primary / ".game-of-cards" / "config.yaml"
        text, n = re.subn(r"^  # worktree_deck: shared", "  worktree_deck: shared",
                          config.read_text(), flags=re.M)
        assert n == 1, "the config template no longer carries the commented shared line"
        config.write_text(text)
        run(primary, "git", "add", "-A")
        run(primary, "git", "commit", "-q", "-m", "install goc, share the deck")
        linked = work / "linked"
        run(primary, "git", "worktree", "add", "-q", "-b", "feature", str(linked))

        goc(linked, "new", CARD, "--summary", "Claimed from a linked worktree.", "--gate", "none")
        goc(linked, "status", CARD, "active")
        in_primary = (primary / ".game-of-cards" / "deck" / CARD).is_dir()
        in_linked = (linked / ".game-of-cards" / "deck" / CARD).exists()
        listed = CARD in goc(linked, "--status", "active").stdout
        print(f"card in primary deck={in_primary}; in linked checkout={in_linked}; "
              f"goc --status active from linked lists it={listed}")
        if not in_primary or in_linked or not listed:
            print("\nINCONCLUSIVE: goc itself did not resolve the shared deck from the linked worktree.")
            return 1

        def session_start(cwd: Path) -> str:
            payload = json.dumps({"hook_event_name": "SessionStart", "cwd": str(cwd)})
            return run(cwd, sys.executable, str(HOOKS / "deck_session_start.py"), stdin=payload).stdout

        names_from_primary = CARD in session_start(primary)
        names_from_linked = CARD in session_start(linked)
        print(f"session-start names the card: cwd=primary {names_from_primary}; "
              f"cwd=linked {names_from_linked}")

        # Enable the Stop hook in the primary config only: the linked checkout
        # was branched before, so its copy still says false.
        text = config.read_text()
        config.write_text(text.replace("pattern_generalization_check: false",
                                       "pattern_generalization_check: true"))
        transcript = work / "transcript.jsonl"
        transcript.write_text("\n".join(json.dumps(e) for e in (
            {"message": {"role": "user", "content": "edit the file"}},
            {"message": {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Edit", "input": {}}]}},
        )) + "\n")

        def stop_hook(cwd: Path) -> int:
            payload = json.dumps({"hook_event_name": "Stop", "cwd": str(cwd),
                                  "transcript_path": str(transcript)})
            return run(cwd, sys.executable, str(HOOKS / "pattern_generalization_check.py"),
                       stdin=payload).returncode

        stop_from_primary = stop_hook(primary)
        stop_from_linked = stop_hook(linked)
        print(f"stop hook exit (2 = enabled, blocks): cwd=primary {stop_from_primary}; "
              f"cwd=linked {stop_from_linked}")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if not names_from_primary or stop_from_primary != 2:
        print("\nINCONCLUSIVE: the hooks do not work from the primary tree either.")
        return 1
    if not names_from_linked or stop_from_linked != 2:
        print("\nFAIL: from the linked worktree the hooks read its own checkout, not the shared deck goc uses.")
        return 1
    print("\nOK: from the linked worktree both hooks follow the shared deck goc uses.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
