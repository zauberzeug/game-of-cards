from __future__ import annotations

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


def _write_card(deck: Path, title: str, status: str, closed_at: str) -> Path:
    card = deck / title
    card.mkdir(parents=True)
    checkbox = "x" if status == "done" else " "
    (card / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"summary: terminal {status}\n"
        f"status: {status}\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-01-01\n"
        f"closed_at: {closed_at}\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        f"  - [{checkbox}] terminal fixture\n"
        "---\n\n"
        f"# {title}\n"
    )
    (card / "log.md").write_text("")
    return card


def _frontmatter_line(readme: Path, key: str) -> str:
    prefix = f"{key}:"
    for line in readme.read_text().splitlines():
        if line.startswith(prefix):
            return line
    raise RuntimeError(f"{key} not found")


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck = cwd / "deck"
        deck.mkdir()
        fixtures = [
            ("done-card", "done", "2026-01-02"),
            ("disproved-card", "disproved", "null"),
            ("superseded-card", "superseded", "null"),
        ]
        for title, status, closed_at in fixtures:
            _write_card(deck, title, status, closed_at)

        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"

        results: list[tuple[str, int, str, str, str]] = []
        for title, _status, _closed_at in fixtures:
            result = subprocess.run(
                [sys.executable, "-m", "goc.cli", "status", title, "open", "--no-commit"],
                cwd=cwd,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            readme = deck / title / "README.md"
            results.append(
                (
                    title,
                    result.returncode,
                    result.stdout.strip(),
                    _frontmatter_line(readme, "status"),
                    _frontmatter_line(readme, "closed_at"),
                )
            )

        validate = subprocess.run(
            [sys.executable, "-m", "goc.cli", "validate", "--quiet"],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    for title, returncode, stdout, status_line, closed_at_line in results:
        print(f"{title}: exit={returncode}; stdout={stdout}; {status_line}; {closed_at_line}")
    print(f"validate_exit={validate.returncode}")
    print(f"validate_stderr={validate.stderr.strip()}")

    reopened = [title for title, returncode, _stdout, status_line, _closed_at in results if returncode == 0 and status_line == "status: open"]
    if reopened:
        print(f"defect present: terminal cards reopened: {', '.join(reopened)}")
        return 1
    if validate.returncode == 0:
        print("defect present: stale closed_at on non-done card validates")
        return 1
    print("ok: terminal cards cannot be reopened through goc status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
