#!/usr/bin/env python3
"""Reproduce: `goc upgrade` at the current version skips the pre-commit
goc-validate glob migration because `upgrade()` short-circuits before
`_append_precommit_hook` runs.

Setup: a repo already at `__version__` with a `.git` dir and a
`.pre-commit-config.yaml` carrying the legacy `files: ^deck/.*$` glob.
`_refresh_goc_validate_block` *would* migrate that glob — but the
same-version "nothing to do" short-circuit returns first, so the dead
glob survives and the frontmatter-drift gate stays silently disabled.

Before the fix: the legacy glob is still present after `upgrade()` (BUG).
After the fix: it is migrated to the `.game-of-cards/deck` path.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from goc import install as goc_install  # noqa: E402

LEGACY_GLOB = "files: ^deck/.*$"
NEW_GLOB = "files: ^\\.game-of-cards/deck/.*$"

# A standalone, single-hook GoC-signature stanza carrying the legacy glob —
# exactly what `_refresh_goc_validate_block` is designed to migrate.
LEGACY_PRECOMMIT = (
    "repos:\n"
    "  - repo: local\n"
    "    hooks:\n"
    "      - id: goc-validate\n"
    "        name: goc validate\n"
    "        entry: goc validate\n"
    "        language: system\n"
    "        pass_filenames: false\n"
    "        files: ^deck/.*$\n"
)


@contextlib.contextmanager
def _chdir(path: Path):
    prev = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        fn(*args, **kwargs)
    return buf.getvalue()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        with _chdir(repo):
            _quiet(goc_install.install)

            # `_append_precommit_hook` only touches a real git repo; the
            # legacy config predates the deck move.
            (repo / ".git").mkdir(exist_ok=True)
            precommit = repo / ".pre-commit-config.yaml"
            precommit.write_text(LEGACY_PRECOMMIT)

            # Pin the version sentinel to the CURRENT version so the
            # same-version short-circuit is what gates the behavior.
            (repo / ".game-of-cards" / "deck" / ".goc-version").write_text(
                goc_install.__version__ + "\n"
            )

            _quiet(goc_install.upgrade)

            after = precommit.read_text()

    print(f"goc __version__ : {goc_install.__version__}")
    print(f"legacy glob present after upgrade : {LEGACY_GLOB in after}")
    print(f"migrated glob present after upgrade: {NEW_GLOB in after}")

    if LEGACY_GLOB in after:
        print(
            "\nFAIL (bug reproduced): same-version upgrade did NOT migrate the "
            "stale pre-commit glob — the goc-validate hook stays silently dead."
        )
        return 1

    if NEW_GLOB not in after:
        print("\nFAIL: glob neither stale nor migrated — unexpected state.")
        return 1

    print(
        "\nPASS (fixed): same-version upgrade migrated the stale glob to the "
        ".game-of-cards/deck path."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
