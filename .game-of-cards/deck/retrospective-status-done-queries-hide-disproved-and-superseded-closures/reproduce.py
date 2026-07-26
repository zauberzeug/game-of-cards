"""Prove the `retrospective` skill's closure queries reach every terminal status.

Builds a throwaway deck holding one closure of each terminal status
(`done`, `disproved`, `superseded`), then extracts the `goc ... --json`
invocations the skill body actually prescribes, runs each one against
that deck, and checks the returned population against the engine's own
`TERMINAL_STATUSES`.

The probe reads the queries out of `SKILL.md` rather than hard-coding
them, so it stays honest whichever way the skill is fixed — and turns
red again if a future edit narrows a closure query back to one status.

Exits non-zero while the defect fires.
"""

from __future__ import annotations

import json
import os
import re
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
sys.path.insert(0, str(ROOT))

from goc.engine import TERMINAL_STATUSES  # noqa: E402

SKILL = ROOT / "goc" / "templates" / "skills" / "retrospective" / "SKILL.md"

# Every `goc <flags> --json` invocation on one line, stopping at the first
# shell separator so a `; else goc ...` / `| python3` tail is not swallowed.
# `\b` keeps `_goc-bootstrap.sh` from matching.
QUERY_RE = re.compile(r"\bgoc ([^|;\n]*?--json)")


def _goc(cwd: Path, *args: str) -> str:
    env = dict(os.environ, PYTHONPATH=str(ROOT), GOC_WORKER="")
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, capture_output=True, text=True,
    )
    return proc.stdout


def _author(card_dir: Path) -> None:
    """Clear the draft flag and satisfy the DoD so the card can close."""
    readme = card_dir / "README.md"
    text = readme.read_text()
    text = text.replace("draft: true\n", "")
    text = text.replace("human_gate: decision", "human_gate: none")
    text = text.replace(
        "- [ ] (replace with real criteria)", "- [x] scaffolded for the probe [manual]"
    )
    text = text.replace(
        "title: ", "summary: probe card for the retrospective scope check\ntitle: ", 1
    )
    readme.write_text(text)


def _build_deck(repo: Path) -> dict[str, str]:
    subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "probe@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "probe"], cwd=repo, check=True)
    (repo / ".game-of-cards" / "deck").mkdir(parents=True)
    (repo / ".game-of-cards" / "config.yaml").write_text(
        "auto_commit: false\nclaim_push: false\n"
    )

    plan = {
        "probe-done-card": "done",
        "probe-disproved-card": "disproved",
        "probe-superseded-card": "superseded",
    }
    # `superseded` needs a live successor to point at.
    for title in (*plan, "probe-successor-card"):
        _goc(repo, "new", title, "--contribution", "medium", "--tag", "bug")
        _author(repo / ".game-of-cards" / "deck" / title)

    _goc(repo, "done", "probe-done-card")
    _goc(repo, "status", "probe-disproved-card", "disproved")
    _goc(
        repo, "status", "probe-superseded-card", "superseded",
        "--by", "probe-successor-card",
    )
    return plan


def main() -> int:
    body = SKILL.read_text()
    queries = [m.group(1).split() for m in QUERY_RE.finditer(body)]
    # The Context block emits the bootstrap and bare-`goc` branches of the
    # same query; dedupe so each distinct query is reported once.
    unique: list[list[str]] = []
    for q in queries:
        if q not in unique:
            unique.append(q)

    print("engine TERMINAL_STATUSES :", ", ".join(sorted(TERMINAL_STATUSES)))
    print(f"closure queries found in {SKILL.relative_to(ROOT)}: {len(unique)}")
    if not unique:
        print()
        print("[FAIL] no `goc ... --json` closure query found — the probe cannot "
              "verify a skill body that no longer queries the deck.")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        plan = _build_deck(repo)

        expected = {t for t, s in plan.items() if s in TERMINAL_STATUSES}
        failures: list[str] = []
        for argv in unique:
            raw = _goc(repo, *argv)
            try:
                got = {c["title"] for c in json.loads(raw)}
            except json.JSONDecodeError:
                print(f"  goc {' '.join(argv)}  → non-JSON output")
                failures.append(f"goc {' '.join(argv)}: non-JSON output")
                continue
            missing = sorted(expected - got)
            verdict = "reaches every terminal status" if not missing else (
                "HIDES " + ", ".join(missing)
            )
            print(f"  goc {' '.join(argv):<28} → {len(got & expected)}/"
                  f"{len(expected)} closures · {verdict}")
            if missing:
                failures.append(f"goc {' '.join(argv)}: hides {', '.join(missing)}")

    print()
    print("closures written to the probe deck:", len(expected))
    for title, status in sorted(plan.items()):
        print(f"    {status:<11} {title}")
    print()
    print("Step 3 of the skill asks: \"Cards closed with `disproved` or "
          "`superseded` — what was wrong?\"")

    if failures:
        print()
        for f in failures:
            print("  ", f)
        print(
            f"[FAIL] {len(failures)} of {len(unique)} closure queries scope "
            "below the engine's terminal set, so the population Step 3 asks "
            "about never reaches the analysis."
        )
        return 1
    print()
    print("[OK] every closure query in the skill body reaches all "
          f"{len(TERMINAL_STATUSES)} terminal statuses.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
