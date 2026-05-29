"""Reproduce: `goc status <t> <non-active> --worker-who alice` silently drops the flag.

Builds a temp deck, files a card, flips it through three non-active transitions
each with worker-override flags set, and shows the `worker:` field is never
written. Exits non-zero (defect present) until a fix lands; flips to zero once
the chosen behavior (Option A / B / C from README) is in place.
"""
from __future__ import annotations

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


REPO_ROOT = _repo_root()


def _read_worker(card_path: Path) -> str:
    for line in card_path.read_text().splitlines():
        if line.startswith("worker"):
            return line
    return "<absent>"


def _read_status(card_path: Path) -> str:
    for line in card_path.read_text().splitlines():
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
    return "<absent>"


def _run(env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", "--project", str(REPO_ROOT), "goc", *args],
        capture_output=True, text=True, env=env,
    )


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="goc-worker-drop-"))
    try:
        # Minimal repo: git init, .game-of-cards/deck, vendored config.
        subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workdir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=workdir, check=True)
        (workdir / ".game-of-cards" / "deck").mkdir(parents=True)
        (workdir / ".game-of-cards" / "config.yaml").write_text("skills_source: vendored\n")

        env = os.environ.copy()
        env["GOC_AUTO_COMMIT"] = "0"
        env.pop("GOC_WORKER", None)
        # The CLI resolves DECK_DIR relative to cwd; chdir via env doesn't help, so
        # we shell each subprocess with cwd=workdir.

        def goc(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                ["uv", "run", "--project", str(REPO_ROOT), "goc", *args],
                capture_output=True, text=True, env=env, cwd=workdir,
            )

        drops = 0

        for target_status in ("disproved", "superseded", "open"):
            slug = f"probe-{target_status}-worker"

            # Reset: file a fresh card in `open`.
            r = goc("new", slug, "--contribution", "low", "--gate", "none", "--tag", "bug")
            if r.returncode != 0:
                print(f"setup failed for {slug}: {r.stderr}", file=sys.stderr)
                return 2
            card = workdir / ".game-of-cards" / "deck" / slug / "README.md"

            # For `superseded` we need a successor. For `open` we need a prior != open;
            # claim active first so the transition is meaningful.
            extra_args = []
            if target_status == "superseded":
                successor = f"probe-{target_status}-successor"
                goc("new", successor, "--contribution", "low", "--gate", "none", "--tag", "bug")
                extra_args = ["--by", successor]
            elif target_status == "open":
                # Move active first (with no worker override) so the open transition has somewhere to come from.
                goc("status", slug, "active")

            before_worker = _read_worker(card)
            before_status = _read_status(card)

            r = goc(
                "status", slug, target_status,
                "--worker-who", "alice",
                "--worker-where", "feature/foo",
                *extra_args,
            )
            after_worker = _read_worker(card)
            after_status = _read_status(card)

            print(f"=== new_status={target_status} ===")
            print(f"  before: status={before_status}, worker={before_worker}")
            print(f"  command exit: {r.returncode}")
            print(f"  command stderr: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else '(empty)'}")
            print(f"  after:  status={after_status}, worker={after_worker}")

            # Defect signature: command exit 0, status flipped, but worker NOT written to alice/feature/foo.
            wrote_alice = "alice" in after_worker
            wrote_branch = "feature/foo" in after_worker
            rejected = r.returncode != 0 and ("worker-who" in r.stderr or "worker-where" in r.stderr)
            if not rejected and not (wrote_alice and wrote_branch):
                print(f"  DROPPED: --worker-who/--worker-where silently discarded\n")
                drops += 1
            elif rejected:
                print(f"  REJECTED with diagnostic (Option B applied)\n")
            else:
                print(f"  APPLIED (Option A applied)\n")

        print("=" * 60)
        if drops > 0:
            print(f"DEFECT REPRODUCED ({drops}/3 non-active transitions silently dropped worker overrides)")
            return 1
        print("DEFECT NOT REPRODUCED (the chosen fix is honoring or rejecting on all three transitions)")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
