"""Reproduce: the `--ready` leverage line's gated half ignores `GOC_WORKER`.

Drives the real `goc` CLI against a temp deck holding one ready and one
gated card per worker. bob's gated card outranks alice's, so an unscoped
gated pool names bob's card. `GOC_WORKER=alice goc --ready` scopes the
"Pulling" half to alice's queue; the "Highest gated card" half must be
scoped the same way and name alice's parked card, never bob's.

Exits 0 when the gated half is worker-scoped (fixed engine);
exits 1 when it names another worker's card (the bug).
"""
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


def _write_card(cwd: Path, title: str, worker: str, contribution: str, gate: str) -> None:
    card_dir = cwd / "deck" / title
    card_dir.mkdir(parents=True)
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"summary: {title}\n"
        "status: open\n"
        "stage: null\n"
        f"contribution: {contribution}\n"
        "created: 2026-05-04\n"
        "closed_at: null\n"
        f"human_gate: {gate}\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        f"worker: {worker}\n"
        "definition_of_done: |\n"
        "  - [ ] test card\n"
        "---\n\n"
        f"# {title}\n"
    )


def _leverage_line(cwd: Path, goc_worker: str | None) -> str:
    env = os.environ.copy()
    env.pop("GOC_WORKER", None)
    if goc_worker is not None:
        env["GOC_WORKER"] = goc_worker
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    r = subprocess.run(
        [sys.executable, "-m", "goc.cli", "--ready", "--no-color"],
        cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )
    if r.returncode != 0:
        raise SystemExit(f"goc --ready exited {r.returncode}:\n{r.stdout}{r.stderr}")
    return next((ln for ln in r.stdout.splitlines() if ln.startswith("Pulling ")), "")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        _write_card(cwd, "alice-ready", "alice", "low", "none")
        _write_card(cwd, "alice-parked", "alice", "medium", "decision")
        _write_card(cwd, "bob-ready", "bob", "low", "none")
        _write_card(cwd, "bob-parked", "bob", "high", "decision")

        unscoped = _leverage_line(cwd, None)
        scoped = _leverage_line(cwd, "alice")

        print("=== `goc --ready` (no GOC_WORKER) ===")
        print(unscoped or "(no leverage line)")
        print("=== `GOC_WORKER=alice goc --ready` ===")
        print(scoped or "(no leverage line)")
        print()

        gated_half = scoped.partition("Highest gated card:")[2]
        pulls_alice = scoped.startswith("Pulling alice-ready ")
        names_bob = "bob-" in gated_half
        names_alice = "alice-parked" in gated_half
        print(f"pulling half names alice-ready:  {pulls_alice}")
        print(f"gated half names bob's card:     {names_bob}   (BUG if True)")
        print(f"gated half names alice-parked:   {names_alice}")
        print()

        if pulls_alice and names_alice and not names_bob:
            print("PASS: the leverage line's gated half is scoped to GOC_WORKER=alice.")
            sys.exit(0)
        print("FAIL: the leverage line compares alice's pick against another worker's gated card.")
        sys.exit(1)


if __name__ == "__main__":
    main()
