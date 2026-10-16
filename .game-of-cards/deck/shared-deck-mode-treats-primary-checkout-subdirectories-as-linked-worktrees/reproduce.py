"""Reproduce: shared-deck mode treats primary-checkout subdirectories as linked worktrees.

`_detect_worktree_common_root` (goc/engine.py, mirrored by both Python hooks)
decides "linked worktree" by comparing the raw text of `git rev-parse
--git-dir` and `--git-common-dir`. From a subdirectory of the PRIMARY checkout
git prints the first absolute and the second relative, so the strings differ
although both name the same `.git` directory. Every probe below runs in a
primary checkout that has no linked worktree at all.

Exit 1 while the defect fires, 0 once it is fixed.
"""

from __future__ import annotations

import importlib.util
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
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402

HOOKS = ROOT / "goc" / "templates" / "hooks"


def load_hook(name: str):
    spec = importlib.util.spec_from_file_location(f"_hook_{name}", HOOKS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def env_with(**extra: str) -> dict:
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    for key in ("GOC_WORKTREE_DECK", "GOC_WORKER", "CLAUDE_PLUGIN_ROOT"):
        env.pop(key, None)
    env.update(extra)
    return env


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def goc(cwd: Path, *args: str, **extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "goc.cli", *args], cwd=cwd,
                          env=env_with(**extra), capture_output=True, text=True)


def rel(path: Path | None, base: Path) -> str:
    return "None" if path is None else str(path.relative_to(base))


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp).resolve()

        # 1. The detector itself, in a primary checkout with no linked worktree.
        repo = tmp_path / "repo"
        sub = repo / "src" / "pkg"
        sub.mkdir(parents=True)
        git(repo, "init", "-q")
        print("1. _detect_worktree_common_root in a primary checkout (expected: None everywhere)")
        for start in (repo, sub):
            print(f"   from {rel(start, tmp_path)}: --git-dir={git(start, 'rev-parse', '--git-dir')!r}"
                  f" --git-common-dir={git(start, 'rev-parse', '--git-common-dir')!r}")
            readers = {"engine": engine}
            for name in ("deck_session_start", "pattern_generalization_check"):
                readers[name] = load_hook(name)
            for name, module in readers.items():
                got = module._detect_worktree_common_root(start)
                verdict = "ok" if got is None else "DEFECT"
                failures += got is not None
                print(f"     {name:30s} -> {rel(got, tmp_path):8s} [{verdict}]")

        # 2. Config opt-in: a nested deck below the git top level is bypassed.
        mono = tmp_path / "mono"
        service = mono / "service"
        (mono / ".game-of-cards" / "deck").mkdir(parents=True)
        (service / ".game-of-cards" / "deck").mkdir(parents=True)
        git(mono, "init", "-q")
        (mono / ".game-of-cards" / "config.yaml").write_text(
            "workflow:\n  auto_commit: false\n  worktree_deck: shared\n")
        (service / ".game-of-cards" / "config.yaml").write_text(
            "workflow:\n  auto_commit: false\n")
        r = goc(service, "new", "service-card", "--summary", "Filed from service/.", "--no-commit")
        landed = [p for p in (service, mono)
                  if (p / ".game-of-cards" / "deck" / "service-card").is_dir()]
        where = rel(landed[0], tmp_path) if landed else f"nowhere (exit {r.returncode})"
        ok = landed == [service]
        failures += not ok
        print("2. worktree_deck: shared in the top-level config; `goc new` run in mono/service,")
        print(f"   which holds its own deck: card filed into {where}/.game-of-cards/deck"
              f" (expected mono/service) [{'ok' if ok else 'DEFECT'}]")

        # 3. Env opt-in: `goc install` in a sub-project scaffolds the git top level.
        mono2 = tmp_path / "mono2"
        pkg = mono2 / "packages" / "foo"
        pkg.mkdir(parents=True)
        git(mono2, "init", "-q")
        r = goc(pkg, "install", "--agents", "codex", GOC_WORKTREE_DECK="shared")
        created = sorted(rel(p.parent, tmp_path) for p in mono2.rglob(".game-of-cards") if p.is_dir())
        ok = created == [rel(pkg, tmp_path)]
        failures += not ok
        print("3. GOC_WORKTREE_DECK=shared; `goc install` run in mono2/packages/foo:")
        print(f"   .game-of-cards/ scaffolded in {created} (expected ['mono2/packages/foo'])"
              f" [{'ok' if ok else 'DEFECT'}]")

        # 4. Env opt-in: one checkout, two answers — top level vs subdirectory.
        ws = tmp_path / "ws"
        (ws / ".game-of-cards" / "deck").mkdir(parents=True)
        (ws / ".game-of-cards" / "config.yaml").write_text("workflow:\n  auto_commit: false\n")
        r = goc(ws, "new", "workspace-card", "--summary", "Workspace deck card.", "--no-commit")
        app = ws / "app"
        (app / "src").mkdir(parents=True)
        git(app, "init", "-q")
        print("4. GOC_WORKTREE_DECK=shared; workspace deck in ws/, git repo ws/app has no deck:")
        seen = {}
        for start in (app, app / "src"):
            r = goc(start, "--status", "all", "--json", GOC_WORKTREE_DECK="shared")
            seen[start] = "workspace-card" in r.stdout
            print(f"   `goc --status all` from {rel(start, tmp_path):10s} lists workspace-card: {seen[start]}")
        ok = len(set(seen.values())) == 1
        failures += not ok
        print(f"   top level and subdirectory agree: {ok} [{'ok' if ok else 'DEFECT'}]")

    print()
    print(f"defect fires in {failures} check(s)" if failures else "all checks pass")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
