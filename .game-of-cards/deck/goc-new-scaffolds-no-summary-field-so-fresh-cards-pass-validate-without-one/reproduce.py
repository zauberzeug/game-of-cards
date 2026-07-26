"""Reproduce: goc new scaffolds no summary field and validate accepts its absence.

In a scratch deck: file a card via `goc new`, publish it (clearing the
draft flag, as claiming does on the real deck), and run `goc validate`.

Contract: a published card should not be able to reach the queues
summary-less — either `goc new` scaffolds the field or `goc validate`
flags its absence on non-draft cards (validate already rejects a
present-but-blank `summary: ""`).

Observed today: the scaffold contains no `summary:` key and validate
exits 0 on the published summary-less card. Exits non-zero while the
defect is present; exits zero once the gap no longer fires.
"""

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
TITLE = "sample-card-filed-without-a-summary"


def _goc(scratch: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=scratch,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        subprocess.run(["git", "init", "-q", str(scratch)], check=True)
        (scratch / ".game-of-cards" / "deck").mkdir(parents=True)

        new = _goc(scratch, "new", TITLE, "--gate", "none", "--tag", "bug", "--no-commit")
        if new.returncode != 0:
            print(f"[SETUP FAIL] goc new exited {new.returncode}: {new.stderr.strip()}")
            return 2
        readme = scratch / ".game-of-cards" / "deck" / TITLE / "README.md"
        fm_lines = readme.read_text().split("---\n")[1].splitlines()
        has_summary = any(line.startswith("summary:") for line in fm_lines)
        print(f"scaffold has summary key: {has_summary}")

        # Author a real DoD and body — everything Step 5 demands EXCEPT the
        # summary — so `goc publish` releases the card the way an agent that
        # skipped the summary line would.
        text = readme.read_text()
        text = text.replace(
            "- [ ] (replace with real criteria",
            "- [ ] MECHANICAL: the sample edit landed (replace with real criteria",
        )
        fm, body = text.split("---\n", 2)[1], text.split("---\n", 2)[2]
        readme.write_text(
            f"---\n{fm}---\n{body}\nAuthored body prose replacing the scaffold placeholder.\n"
        )

        pub = _goc(scratch, "publish", TITLE)
        print(f"goc publish exit: {pub.returncode}")
        draft_line = [l for l in readme.read_text().splitlines() if l.startswith("draft:")]
        print(f"draft flag after publish: {draft_line or '(removed)'}")

        val = _goc(scratch, "validate")
        print(f"goc validate exit: {val.returncode}")
        for line in val.stdout.splitlines():
            if TITLE in line:
                print(f"validate line: {line}")

    if not has_summary and val.returncode == 0:
        print(
            "[FAIL] goc new scaffolded no summary: key and goc validate "
            "accepted the published summary-less card — the card reaches "
            "triage views with a blank summary and only goc quality-pass "
            "(run during refine passes) ever flags it."
        )
        return 1
    print("[OK] defect no longer fires: the scaffold carries a summary field "
          "or validate flags its absence on a published card.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
