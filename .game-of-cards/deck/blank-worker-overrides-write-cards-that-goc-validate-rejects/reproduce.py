#!/usr/bin/env python3
"""Proof that the `worker` write path skips the guards its own validator demands.

Three doors, one root cause — neither `_cmd_new`'s `--worker` nor
`_cmd_status`'s `--worker-who` / `--worker-where` validates the value before it
reaches the frontmatter:

  A. `goc new --worker "   "`                        -> exit 0, writes validate-red card
  B. `goc status <t> active --worker-who "   "`      -> exit 0, writes validate-red card
  C. `goc status <t> active --worker-where "   "`    -> exit 0, writes validate-red card
  D. `goc status <t> active --worker-who $'a\\rb'`    -> FrontmatterError traceback, not ERROR/exit 2

Doors A-C are the corrupting writes: the verb reports success, and `goc validate`
then refuses the very card the verb just wrote. Door D is the unguarded-emitter
door that `goc new` closed for `--summary`/`--worker` (see
../goc-new-leaves-an-empty-card-directory-when-summary-or-worker-carries-a-line-break/)
but that `goc status` never got.

Exits 0 while the defect is present (all four doors behave as described), 1 once
the guards land. Written to be run from a clean checkout:

    uv run python .game-of-cards/deck/blank-worker-overrides-write-cards-that-goc-validate-rejects/reproduce.py
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


def goc(cwd: Path, *argv: str) -> subprocess.CompletedProcess:
    """Run the engine in-process-equivalent via `python -m goc.cli` from `cwd`."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    # Neutralize any ambient runner identity so the probe measures the flags only.
    env.pop("GOC_WORKER", None)
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *argv],
        cwd=cwd, env=env, capture_output=True, text=True,
    )


def make_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    (repo / ".game-of-cards" / "deck").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Probe User"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "probe@example.com"], cwd=repo, check=True)
    return repo


def worker_line(repo: Path, title: str) -> str:
    readme = repo / ".game-of-cards" / "deck" / title / "README.md"
    if not readme.exists():
        return "<no README written>"
    for line in readme.read_text().splitlines():
        if line.startswith("worker:"):
            return line
    return "<no worker field>"


def validate_errors(repo: Path, title: str) -> list[str]:
    r = goc(repo, "validate")
    return [
        ln for ln in (r.stdout + r.stderr).splitlines()
        if ln.startswith("ERROR:") and title in ln
    ]


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as td:
        repo = make_repo(Path(td))

        # ---- Door A: `goc new --worker "   "` -------------------------------
        a = goc(repo, "new", "door-a-new-worker", "--summary", "probe", "--worker", "   ")
        a_errs = validate_errors(repo, "door-a-new-worker")
        print("=== Door A: goc new --worker '   ' ===")
        print(f"  exit               : {a.returncode}")
        print(f"  frontmatter written: {worker_line(repo, 'door-a-new-worker')!r}")
        print(f"  goc validate says  : {a_errs}")
        if not (a.returncode == 0 and a_errs):
            failures.append("A: `goc new --worker '   '` no longer writes a validate-red card")

        # ---- Door B: `--worker-who "   "` ----------------------------------
        goc(repo, "new", "door-b-who", "--summary", "probe")
        b = goc(repo, "status", "door-b-who", "active", "--worker-who", "   ", "--no-commit")
        b_errs = validate_errors(repo, "door-b-who")
        print("\n=== Door B: goc status <t> active --worker-who '   ' ===")
        print(f"  exit               : {b.returncode}")
        print(f"  stdout             : {b.stdout.strip().splitlines()[:1]}")
        print(f"  frontmatter written: {worker_line(repo, 'door-b-who')!r}")
        print(f"  goc validate says  : {b_errs}")
        if not (b.returncode == 0 and b_errs):
            failures.append("B: `--worker-who '   '` no longer writes a validate-red card")

        # ---- Door C: `--worker-where "   "` --------------------------------
        goc(repo, "new", "door-c-where", "--summary", "probe")
        c = goc(repo, "status", "door-c-where", "active",
                "--worker-who", "bob", "--worker-where", "   ", "--no-commit")
        c_errs = validate_errors(repo, "door-c-where")
        print("\n=== Door C: goc status <t> active --worker-where '   ' ===")
        print(f"  exit               : {c.returncode}")
        print(f"  frontmatter written: {worker_line(repo, 'door-c-where')!r}")
        print(f"  goc validate says  : {c_errs}")
        if not (c.returncode == 0 and c_errs):
            failures.append("C: `--worker-where '   '` no longer writes a validate-red card")

        # ---- Door D: line break reaches _yaml_inline unguarded --------------
        goc(repo, "new", "door-d-linebreak", "--summary", "probe")
        d = goc(repo, "status", "door-d-linebreak", "active",
                "--worker-who", "a\rb", "--no-commit")
        traceback_leaked = "FrontmatterError" in d.stderr and "Traceback" in d.stderr
        print("\n=== Door D: goc status <t> active --worker-who $'a\\rb' ===")
        print(f"  exit               : {d.returncode}")
        print(f"  traceback leaked   : {traceback_leaked}")
        print(f"  last stderr line   : {d.stderr.strip().splitlines()[-1][:90]!r}")
        if not traceback_leaked:
            failures.append("D: line-break `--worker-who` no longer leaks a traceback")

    print("\n" + "=" * 62)
    if failures:
        print("DEFECT NOT REPRODUCED — guards appear to be in place:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("DEFECT REPRODUCED: all four doors bypass the worker write-path guards.")
    print("Three verbs exited 0 with a success line and wrote frontmatter that")
    print("`goc validate` refuses; the fourth leaked a raw FrontmatterError.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
