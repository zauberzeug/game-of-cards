"""Reproduce: `goc decide` lowers a gate without naming unclosed prerequisites.

Drives the real `goc` CLI against a temp deck holding two cards:

  prereq-card  status: open   (non-terminal)  advances:    [gated-card]
  gated-card   human_gate: decision           advanced_by: [prereq-card]

`goc decide gated-card ...` lowers the gate to `none` and announces that
"any agent can now claim this card" — the act that makes the card
autonomously implementable. The queue renderers carry a dependency
advisory for exactly this situation; `_cmd_decide` carries none, so the
open prerequisite is never mentioned.

Exits 0 when the decide output names the unclosed prerequisite (fixed
engine); exits 1 when it stays silent (the bug).
"""
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


ROOT = _repo_root()


def _write_card(
    cwd: Path,
    title: str,
    *,
    human_gate: str = "none",
    advances: list[str] | None = None,
    advanced_by: list[str] | None = None,
    body_extra: str = "",
) -> None:
    card_dir = cwd / "deck" / title
    card_dir.mkdir(parents=True)

    def _emit(field: str, items: list[str] | None) -> str:
        if not items:
            return f"{field}: []\n"
        return f"{field}:\n" + "".join(f"  - {i}\n" for i in items)

    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"summary: {title}\n"
        "status: open\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-07-26\n"
        "closed_at: null\n"
        f"human_gate: {human_gate}\n"
        + _emit("advances", advances)
        + _emit("advanced_by", advanced_by)
        + "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [ ] MECHANICAL: test card\n"
        "---\n\n"
        f"# {title}\n"
        f"{body_extra}"
    )
    (card_dir / "log.md").write_text("")


def _run(cwd: Path, *args: str) -> str:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    r = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )
    return r.stdout + r.stderr


def main():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        _write_card(cwd, "prereq-card", advances=["gated-card"])
        _write_card(
            cwd,
            "gated-card",
            human_gate="decision",
            advanced_by=["prereq-card"],
            body_extra=(
                "\n## Decision required\n\n"
                "- **A** — one way.\n"
                "- **B** — another way.\n"
            ),
        )

        out = _run(
            cwd, "decide", "gated-card",
            "--decision", "go with A",
            "--because", "it is cheaper",
            "--no-commit",
        )

        print("=== `goc decide gated-card ...` output ===")
        print(out.rstrip() or "(no output)")
        print()

        prereq_status = _run(cwd, "show", "prereq-card")
        prereq_open = "status: open" in prereq_status
        gate_lowered = "gate decision → none" in out or "→ none" in out
        names_prereq = "prereq-card" in out

        print(f"prerequisite still open:        {prereq_open}")
        print(f"gate was lowered to none:       {gate_lowered}")
        print(f"output names the prerequisite:  {names_prereq}   (BUG if False)")
        print()

        if prereq_open and gate_lowered and names_prereq:
            print("PASS: decide surfaces the unclosed prerequisite.")
            sys.exit(0)
        print(
            "FAIL: decide lowered the gate and announced the card is claimable "
            "without ever naming the open prerequisite."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
