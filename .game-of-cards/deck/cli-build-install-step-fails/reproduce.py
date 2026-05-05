import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


def main() -> int:
    workflow = _repo_root() / ".github" / "workflows" / "ci.yml"
    body = workflow.read_text()

    if "uv pip install --system -e ." in body:
        print("FAIL: CI install step forces --system and ignores setup-uv's activated .venv")
        return 1

    if "uv pip install -e ." not in body:
        print("FAIL: CI install step no longer performs the editable package install smoke test")
        return 1

    print("PASS: CI package install targets the setup-uv virtual environment")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
