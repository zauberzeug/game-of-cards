"""Reproduce the pattern-generalization opt-out regex bug.

The opt-out check at `goc/templates/hooks/pattern_generalization_check.py:38-42`
uses a regex whose capture group `(false|true)` does not accept surrounding
quotes. So YAML scalars `"false"` and `'false'` — both valid YAML forms of
the bare boolean — fail to match, and the hook silently treats the user as
NOT opted out.

Exits zero when the bug is fixed: all three scalar forms must be detected
as opt-out.
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
sys.path.insert(0, str(_repo_root() / "goc" / "templates" / "hooks"))

from pattern_generalization_check import _opted_out  # noqa: E402


def _write_config(tmpdir: Path, value_form: str) -> Path:
    cfg_dir = tmpdir / ".game-of-cards"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.yaml").write_text(
        f"hooks:\n  pattern_generalization_check: {value_form}\n"
    )
    return tmpdir


def main() -> int:
    forms = {
        "bare false": "false",
        "double-quoted false": '"false"',
        "single-quoted false": "'false'",
    }

    results: dict[str, bool] = {}
    with tempfile.TemporaryDirectory() as td:
        for label, value in forms.items():
            project_dir = _write_config(Path(td) / label.replace(" ", "_"), value)
            results[label] = _opted_out(str(project_dir))

    for label, opted in results.items():
        marker = "OK" if opted else "FAIL"
        print(f"  [{marker}] {label}: opted_out={opted}")

    all_ok = all(results.values())
    if all_ok:
        print("\nPASS: all YAML scalar forms parsed as opt-out.")
        return 0

    failing = [label for label, opted in results.items() if not opted]
    print(
        "\nFAIL: opt-out missed for: "
        + ", ".join(failing)
        + ". Regex at pattern_generalization_check.py:38-42 does not "
        "accept surrounding quotes."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
