"""Reproduce: `goc new`'s success message crashes with ValueError when the
deck lives in a shared worktree root (DECK_ROOT != REPO_ROOT).

In shared-worktree-deck mode (GOC_WORKTREE_DECK=shared or
workflow.worktree_deck: shared), `_resolve_deck_root` returns the *primary*
working tree, so DECK_ROOT — and therefore DECK_DIR and every card_dir under
it — lives OUTSIDE REPO_ROOT (the current linked worktree, == Path.cwd()).

`_cmd_new`'s final two prints display the new card_dir relative to a root.
The bug: they used `card_dir.relative_to(REPO_ROOT)`, which raises ValueError
when card_dir is not under REPO_ROOT. The card has already been written to
disk by that point, so the command both half-succeeds and crashes with an
uncaught traceback instead of printing the next-step hint.

This script drives the real engine `_cmd_new`, monkeypatching the module
globals to the exact shared-worktree layout (DECK_ROOT = a primary tree that
is NOT under REPO_ROOT). It exits 1 if `_cmd_new` raises (defect present),
0 if it completes and prints a path relative to DECK_ROOT (fix in place).
"""
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    repo_root = tmp / "worktrees" / "feature-branch"   # cwd / linked worktree
    deck_root = tmp / "primary"                         # shared primary tree
    deck_dir = deck_root / ".game-of-cards" / "deck"
    repo_root.mkdir(parents=True)
    deck_dir.mkdir(parents=True)

    # Simulate shared-worktree mode: deck lives in the primary tree, the
    # command runs from the linked worktree.
    engine.REPO_ROOT = repo_root
    engine.DECK_ROOT = deck_root
    engine.DECK_DIR = deck_dir

    print("REPO_ROOT (cwd / linked worktree):", repo_root)
    print("DECK_ROOT (shared primary tree):  ", deck_root)
    print()

    args = SimpleNamespace(
        title="my-new-card",
        contribution="medium",
        gate="none",
        tags=[],
        worker=None,
        allow_jargon=False,
        commit=False,
        no_commit=True,        # no git commit — keep the reproduce hermetic
        advances_wire=[],
        advanced_by_wire=[],
    )

    out = io.StringIO()
    try:
        with redirect_stdout(out):
            engine._cmd_new(args)
        crashed = False
        err = None
    except ValueError as exc:
        crashed = True
        err = exc

    captured = out.getvalue().strip()
    if captured:
        print("_cmd_new printed:")
        for line in captured.splitlines():
            print("   ", line)
    print()

    if crashed:
        print("_cmd_new raised ValueError:")
        print("   ", err)
        print()
        print("DEFECT CONFIRMED: `goc new` crashes after writing the card to disk.")
        sys.exit(1)
    else:
        assert "my-new-card" in captured, "expected the created-path line"
        print("No crash; card-path displayed relative to DECK_ROOT. Fix is in place.")
        sys.exit(0)
