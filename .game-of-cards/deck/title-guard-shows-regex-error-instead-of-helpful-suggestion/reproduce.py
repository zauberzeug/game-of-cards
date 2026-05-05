"""Demonstrate that two TITLE_ANTIPATTERNS branches are unreachable.

The schema title regex is checked before the antipattern guard, so any
string that could match the `_md_|_py_` or `[a-z][A-Z]` patterns is
already rejected with a bare regex-mismatch error. A user typing
`fix_md_thing` or `fixThing` therefore never sees the maintainer's
authored teaching message.

Exits 0 when the bug is fixed (i.e. the helpful antipattern reason is
shown for at least one of the two unreachable patterns). Exits 1 while
the bug is live.
"""

import re
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


REPO = _repo_root()
sys.path.insert(0, str(REPO))


def main() -> int:
    from goc.engine import TITLE_ANTIPATTERNS, load_schema  # noqa: E402

    schema = load_schema()
    title_pat = re.compile(schema.title_pattern)

    print(f"schema title_pattern = {schema.title_pattern}")
    print()

    unreachable = []
    for pat, reason in TITLE_ANTIPATTERNS:
        # Probe a few strings that match this antipattern; if every probe
        # is rejected by the schema regex, the branch is unreachable.
        probes = {
            r"\br\d+\b": ["fix-r3-thing"],
            r"\bpath-\d+\b": ["fix-path-3-thing"],
            r"\bphase-\d+\b": ["fix-phase-3-thing"],
            r"\bbug-\d+\b": ["fix-bug-140-thing"],
            r"_md_|_py_": ["fix_md_thing", "fix_py_thing"],
            r"[a-z][A-Z]": ["fixThing", "myCamelCase"],
        }.get(pat.pattern, [])

        any_passes_schema = any(title_pat.match(p) for p in probes)
        status = "REACHABLE" if any_passes_schema else "UNREACHABLE"
        print(f"  [{status}] {pat.pattern!r}  →  {reason!r}")
        if not any_passes_schema:
            unreachable.append((pat.pattern, reason))

    print()
    print(f"unreachable branches: {len(unreachable)} / {len(TITLE_ANTIPATTERNS)}")

    # Now show the user-facing symptom: invoke `goc new fix_md_thing` and
    # capture the error. The fixed behavior will mention "source-file
    # infix"; the live bug only mentions the regex.
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", "new", "fix_md_thing", "--gate", "none"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    err = (proc.stderr or "") + (proc.stdout or "")
    print()
    print("--- `goc new fix_md_thing` stderr ---")
    print(err.rstrip())
    print("--- end ---")

    helpful_message_shown = "source-file infix" in err
    if helpful_message_shown:
        print()
        print("OK: helpful antipattern reason is shown alongside/instead of the regex error.")
        return 0

    print()
    print("BUG: the user sees only a regex-mismatch error; the authored teaching message is buried.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
