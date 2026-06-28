"""Empirical proof that `goc status <t> superseded --by <new>` silently
drops the `--by` argument when `<t>` is already superseded.

Sets up an isolated GOC_PROJECT_DIR with three cards: `foo` (will be
superseded), `bar` (the original successor), and `baz` (the redirect
target the operator wants to point at instead). Then:

1. Open state — `foo` is open, no supersession.
2. First flip — `goc status foo superseded --by bar` (sets `foo.superseded_by: [bar]`).
3. Redirect attempt — `goc status foo superseded --by baz`.

Expected (one of):
  (a) `foo.superseded_by` becomes `[baz]` and `bar.supersedes` loses
      `foo` while `baz.supersedes` gains it; or
  (b) The redirect attempt exits non-zero with a clear "already
      superseded; release first" diagnostic.

Actual: exit code 0; the engine prints "foo: already superseded;
nothing to do" and `foo.superseded_by` stays at `[bar]`. The operator's
`--by baz` was validated (file existence + live-status check at
engine.py:4279-4290) and then ignored when the early-return at
engine.py:4294-4303 fired for `prior == new_status == "superseded"`.
"""

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


REPO = _repo_root()


def run(*args, cwd, env, check=True):
    r = subprocess.run(
        ["uv", "run", "goc", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    if check and r.returncode != 0:
        print(f"ERROR: goc {' '.join(args)} exited {r.returncode}", file=sys.stderr)
        print(r.stdout, file=sys.stderr)
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)
    return r


def read_field(card_dir: Path, field: str) -> str:
    text = (card_dir / "README.md").read_text().split("---\n", 2)[1]
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"{field}:"):
            tail = [line]
            for j in range(i + 1, len(lines)):
                nxt = lines[j]
                if nxt.startswith(("  - ", "    ")) or nxt.strip() == "":
                    if nxt.strip() == "":
                        break
                    tail.append(nxt)
                else:
                    break
            return "\n".join(tail)
    return f"{field}: <missing>"


def main():
    workspace = Path(tempfile.mkdtemp(prefix="goc-supersede-redirect-"))
    try:
        # Bootstrap a minimal goc workspace.
        subprocess.run(["git", "init", "-q", str(workspace)], check=True)
        subprocess.run(["git", "-C", str(workspace), "commit", "-q", "--allow-empty",
                        "-m", "init"], check=True,
                       env={**os.environ,
                            "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@e",
                            "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@e"})
        env = {**os.environ, "GOC_AUTOCOMMIT": "0"}

        run("install", "--local-skills", cwd=workspace, env=env)
        run("new", "foo", "--contribution", "low", "--gate", "none", cwd=workspace, env=env)
        run("new", "bar", "--contribution", "low", "--gate", "none", cwd=workspace, env=env)
        run("new", "baz", "--contribution", "low", "--gate", "none", cwd=workspace, env=env)

        foo_dir = workspace / ".game-of-cards" / "deck" / "foo"

        print("=== Initial state ===")
        print(read_field(foo_dir, "status"))
        print(read_field(foo_dir, "superseded_by"))

        print("\n=== First flip: goc status foo superseded --by bar ===")
        r = run("status", "foo", "superseded", "--by", "bar", cwd=workspace, env=env)
        print(r.stdout.rstrip())
        print(read_field(foo_dir, "status"))
        print(read_field(foo_dir, "superseded_by"))

        print("\n=== Redirect attempt: goc status foo superseded --by baz ===")
        r = run("status", "foo", "superseded", "--by", "baz", cwd=workspace, env=env, check=False)
        print(f"exit code: {r.returncode}")
        print(f"stdout: {r.stdout.rstrip()}")
        print(f"stderr: {r.stderr.rstrip()}")

        print("\n=== Post-redirect state ===")
        print(read_field(foo_dir, "status"))
        print(read_field(foo_dir, "superseded_by"))
        bar_dir = workspace / ".game-of-cards" / "deck" / "bar"
        baz_dir = workspace / ".game-of-cards" / "deck" / "baz"
        print("bar." + read_field(bar_dir, "supersedes"))
        print("baz." + read_field(baz_dir, "supersedes"))

        foo_super = read_field(foo_dir, "superseded_by")
        if "baz" in foo_super:
            print("\nDEFECT NOT REPRODUCED: foo.superseded_by was updated to baz")
            sys.exit(1)
        if r.returncode == 0 and "bar" in foo_super:
            print("\nDEFECT REPRODUCED: --by baz was silently dropped;"
                  " exit code 0, foo.superseded_by still points at bar.")
            sys.exit(0)
        if r.returncode != 0:
            print("\nDEFECT NOT REPRODUCED: redirect attempt errored with non-zero exit"
                  " (acceptable alternative behavior).")
            sys.exit(1)
        print("\nDEFECT NOT REPRODUCED: unexpected state.")
        sys.exit(1)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    main()
