#!/usr/bin/env python3
"""`_append_precommit_hook` ignores the indentation the target file already uses.

`PRE_COMMIT_HOOK` (goc/install.py:64-73) is a `- repo: local` list item hard-coded
at TWO-space indentation, and `_append_precommit_hook` (goc/install.py:1340-1342)
concatenates it onto the end of the file. That is only correct when the existing
`repos:` list also indents its items two spaces. Configs whose list items start at
column 0 — the style `pre-commit sample-config` emits — get a stanza at the wrong
indentation, which either breaks the parse outright or silently reparents the
stanza into the PREVIOUS repo's `hooks:` list.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py

Exits 0 only when the `goc-validate` hook is a member of the top-level `repos:`
list in every shape. Exits 1 while the defect fires.
"""

from __future__ import annotations

import re
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


sys.path.insert(0, str(_repo_root()))

from goc.install import _append_precommit_hook  # noqa: E402

# Best available YAML parser. PyYAML is what pre-commit itself uses, so prefer
# it; goc's vendored yaml-lite is the dependency-free fallback. yaml-lite cannot
# parse the `-   repo:` column-zero style even BEFORE goc touches it, so for that
# shape it can only report "unparseable" and the structural check below carries
# the proof.
try:
    import yaml  # type: ignore

    PARSER = "PyYAML"

    def _load(text: str):
        return yaml.safe_load(text)

except ImportError:
    from goc._vendor import yaml_lite

    PARSER = "goc._vendor.yaml_lite (PyYAML absent)"

    def _load(text: str):
        return yaml_lite.safe_load(text)


# (label, pristine config, is-this-the-documented-happy-path)
SHAPES: list[tuple[str, str, bool]] = [
    (
        "column-zero, four-space content — `pre-commit sample-config` output",
        "# See https://pre-commit.com for more information\n"
        "repos:\n"
        "-   repo: https://github.com/pre-commit/pre-commit-hooks\n"
        "    rev: v3.2.0\n"
        "    hooks:\n"
        "    -   id: trailing-whitespace\n",
        False,
    ),
    (
        "column-zero, two-space content — common hand-written style",
        "repos:\n"
        "- repo: https://github.com/psf/black\n"
        "  rev: 24.1.0\n"
        "  hooks:\n"
        "  - id: black\n",
        False,
    ),
    (
        "two-space list items, `repos:` last — documented happy path (control)",
        "repos:\n"
        "  - repo: https://github.com/psf/black\n"
        "    rev: 24.1.0\n"
        "    hooks:\n"
        "      - id: black\n",
        True,
    ),
]

_ITEM_RE = re.compile(r"^(\s*)-\s+repo:", re.MULTILINE)


def _goc_is_a_repos_member(text: str) -> tuple[bool, str]:
    """True iff `goc-validate` is reachable as a hook of a top-level `repos:` entry."""
    try:
        data = _load(text)
    except Exception as exc:  # noqa: BLE001 — any parse failure is the verdict
        return False, f"unparseable: {type(exc).__name__}: {str(exc).splitlines()[0][:70]}"
    if not isinstance(data, dict) or not isinstance(data.get("repos"), list):
        return False, "no top-level `repos:` list survived"
    for repo in data["repos"]:
        if not isinstance(repo, dict):
            continue
        for hook in repo.get("hooks") or []:
            if isinstance(hook, dict) and hook.get("id") == "goc-validate":
                return True, f"member of repos[{data['repos'].index(repo)}]"
    return False, (
        f"absent from repos (list has {len(data['repos'])} entry/entries) — "
        "the stanza landed somewhere else in the tree"
    )


def main() -> int:
    print(f"parser: {PARSER}\n")
    failures = []
    for label, pristine, is_control in SHAPES:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()  # _append_precommit_hook no-ops outside a repo
            cfg = root / ".pre-commit-config.yaml"
            cfg.write_text(pristine)
            _append_precommit_hook(cfg)
            result = cfg.read_text()

        existing_indent = _ITEM_RE.search(pristine).group(1)
        goc_match = re.search(r"^(\s*)-\s+repo: local$", result, re.MULTILINE)
        goc_indent = goc_match.group(1) if goc_match else None

        ok, detail = _goc_is_a_repos_member(result)
        # Baseline: could this parser read the file BEFORE goc touched it? Without
        # it, a fallback-parser limitation reads as a goc defect. yaml-lite cannot
        # parse the column-zero four-space style at all, so on that row the
        # indentation mismatch above — not the parse verdict — is the proof.
        baseline_ok = True
        try:
            _load(pristine)
        except Exception:  # noqa: BLE001
            baseline_ok = False

        tag = "control" if is_control else "affected"
        print(f"[{tag}] {label}")
        print(f"    parser read it pristine   : {baseline_ok}")
        print(f"    existing `- repo:` indent : {len(existing_indent)} space(s)")
        print(
            "    appended `- repo: local`  : "
            + (f"{len(goc_indent)} space(s)" if goc_indent is not None else "not emitted")
        )
        print(f"    indentation matches       : {goc_indent == existing_indent}")
        print(f"    goc-validate in repos     : {ok} ({detail})")
        if not baseline_ok:
            print(
                "    NOTE: this parser cannot read the shape pristine either — read\n"
                "          the indentation mismatch above as the verdict, and see the\n"
                "          card body for pre-commit's own `validate-config` result."
            )
        print()
        if not ok:
            failures.append(label)

    if failures:
        print(f"DEFECT PRESENT — {len(failures)} of {len(SHAPES)} shape(s) corrupted:")
        for f in failures:
            print(f"  - {f}")
        print(
            "\n`_append_precommit_hook` appends `PRE_COMMIT_HOOK` verbatim at its\n"
            "hard-coded two-space indentation instead of matching the indentation\n"
            "the file's own `repos:` list uses."
        )
        return 1

    print("FIXED — goc-validate is a member of `repos:` in every shape.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
