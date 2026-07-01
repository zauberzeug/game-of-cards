"""Reproduce: `_append_precommit_hook` corrupts a `.pre-commit-config.yaml`
whenever the file does not END with a block-style `repos:` list.

The installer's helper at `goc/install.py:1320` does `text + PRE_COMMIT_HOOK`,
which only produces valid YAML when the file's last block is a block-style
`repos:` list. Three realistic shapes violate that assumption and each yields
YAML that `pre-commit run` (and PyYAML) refuses to parse:

  1. a top-level key after `repos:` (e.g. `default_language_version`, `exclude`)
  2. an empty inline list `repos: []`
  3. no `repos:` key at all (e.g. only `ci:`)

This script exercises all three broken shapes plus the block-form happy path
(control), and exits non-zero while any broken shape is present.
"""
from __future__ import annotations

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

# name -> (input config, should_parse_and_be_correct_after_fix)
CASES = {
    "key-after-repos": """\
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace

default_language_version:
  python: python3.11

exclude: '^vendor/'
""",
    "empty-inline-repos": "repos: []\n",
    "no-repos-key": "ci:\n  autofix_prs: true\n",
    # Control: block-form repos as the last key — must remain correct.
    "block-repos-last": """\
repos:
  - repo: https://github.com/x/y
    rev: v1
    hooks:
      - id: foo
""",
}


def _goc_validate_under_repos_pyyaml(text: str):
    """PyYAML verdict, or None when PyYAML is unavailable."""
    try:
        import yaml  # type: ignore
    except Exception:
        return None
    try:
        loaded = yaml.safe_load(text)
    except Exception:
        return False
    if not isinstance(loaded, dict):
        return False
    repos = loaded.get("repos")
    if not isinstance(repos, list):
        return False
    return any(
        isinstance(h, dict) and h.get("id") == "goc-validate"
        for r in repos
        if isinstance(r, dict)
        for h in r.get("hooks", []) or []
    )


def _goc_validate_under_repos_structural(text: str) -> bool:
    """Parser-free check: the appended `- repo: local` block must be a child
    of a BLOCK-style `repos:` list, with no intervening top-level (column-0)
    key between the `repos:` header and the hook. This is precise for all
    three broken shapes:
      - `repos: []` (inline) has no block header  -> False
      - no `repos:` key                            -> False
      - a top-level key after `repos:`             -> intervening col-0 key -> False
    """
    lines = text.splitlines()
    repos_hdr = None  # index of a block-style `repos:` header (empty value)
    for i, ln in enumerate(lines):
        if ln.rstrip() == "repos:":  # block header only; `repos: []` excluded
            repos_hdr = i
            break
    if repos_hdr is None:
        return False
    hook = None
    for i in range(repos_hdr + 1, len(lines)):
        if lines[i].lstrip().startswith("- repo: local"):
            hook = i
            break
    if hook is None:
        return False
    # No column-0, non-blank, non-comment line may sit between the header
    # and the hook — that would be a sibling top-level key, ejecting the
    # hook from `repos:`.
    for i in range(repos_hdr + 1, hook):
        ln = lines[i]
        if ln and not ln[0].isspace() and not ln.lstrip().startswith("#"):
            return False
    return True


def _goc_validate_under_repos(text: str) -> bool:
    """True iff the emitted config parses AND goc-validate is a valid member
    of the top-level `repos:` list. Prefers PyYAML (true parse verdict) and
    falls back to a precise parser-free structural check."""
    verdict = _goc_validate_under_repos_pyyaml(text)
    if verdict is not None:
        return verdict
    return _goc_validate_under_repos_structural(text)


def main() -> int:
    broken = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".git").mkdir()
        target = root / ".pre-commit-config.yaml"
        for name, config in CASES.items():
            target.write_text(config)
            _append_precommit_hook(target)
            after = target.read_text()
            ok = _goc_validate_under_repos(after)
            print(f"=== {name}: goc-validate correctly under repos: {ok} ===")
            print(after)
            if not ok:
                broken.append(name)

    print("--- verdict ---")
    if broken:
        print("DEFECT REPRODUCED: the following shapes produced a config where")
        print("the goc-validate hook is NOT a valid member of `repos:`:")
        for name in broken:
            print(f"  - {name}")
        print("`pre-commit run` will fail with a parser error on these.")
        return 1
    print("OK: all shapes leave goc-validate as a valid member of repos:.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
