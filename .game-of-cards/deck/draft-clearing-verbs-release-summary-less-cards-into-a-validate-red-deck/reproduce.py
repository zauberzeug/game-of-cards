"""Do the draft-clearing verbs refuse a card without a summary (decision: option 1)?

For each verb that releases a card from draft — `publish`, `status <t> active`,
`done` — build a fresh scratch deck, author a card WITHOUT `summary`, and run
the verb. The contract holds when every verb exits 2 and leaves the README
byte-identical, and the same verb on a card WITH a summary succeeds and leaves
`goc validate` green.

Exit 0: contract holds (defect fixed). Exit 1: at least one verb released a
summary-less draft or refused a valid one (defect present).
"""
from __future__ import annotations

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


def goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    if args and args[0] == "new":
        (cwd / ".game-of-cards" / "deck").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run([sys.executable, "-m", "goc.cli", *args], cwd=cwd, env=env,
                          text=True, capture_output=True, timeout=120)


def authored_draft(cwd: Path, summary: str | None) -> Path:
    args = ["new", "card-a", "--gate", "none", "--tag", "story"]
    if summary is not None:
        args += ["--summary", summary]
    r = goc(cwd, *args)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    path = cwd / ".game-of-cards" / "deck" / "card-a" / "README.md"
    text = path.read_text()
    text = text.replace("- [ ] (replace with real criteria)", "- [x] MECHANICAL: done")
    text = text.replace("(write the design doc here)", "Authored body.")
    path.write_text(text)
    return path


VERBS = {
    "publish": ("publish", "card-a", "--no-commit"),
    "status active": ("status", "card-a", "active", "--no-commit"),
    "done": ("done", "card-a"),
}


def main() -> int:
    holds = True
    for name, argv in VERBS.items():
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            path = authored_draft(cwd, summary=None)
            before = path.read_text()
            r = goc(cwd, *argv)
            refused = r.returncode == 2 and path.read_text() == before
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            authored_draft(cwd, summary="One-line summary.")
            released = goc(cwd, *argv).returncode == 0 and goc(cwd, "validate").returncode == 0
        ok = refused and released
        holds &= ok
        print(f"{'OK  ' if ok else 'FAIL'} {name:14} without summary: {'refused' if refused else 'RELEASED'}"
              f" | with summary: {'released, validate green' if released else 'NOT released'}")
    print("contract holds" if holds else "defect present: a draft-clearing verb ignores the summary")
    return 0 if holds else 1


if __name__ == "__main__":
    sys.exit(main())
