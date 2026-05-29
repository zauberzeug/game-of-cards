"""Demonstrate that `goc decide` accepts empty --decision / --because.

The verb's argparse declarations mark both `--decision` and `--because` as
`required=True`, which only forces *presence* on the command line; empty
strings satisfy presence. `_cmd_decide` then writes a malformed `## Decision`
block (no decision text, no reasoning text) into the README, appends a
log entry whose visible content is ` — . Gate decision → none.`, and
lowers the human gate to `none` so the next puller treats the parked
card as resolved.
"""
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402


def _new_parked_card(deck: Path, slug: str) -> None:
    (deck / slug).mkdir(parents=True)
    (deck / slug / "log.md").write_text("")
    (deck / slug / "README.md").write_text(
        "---\n"
        f"title: {slug}\n"
        'summary: ""\n'
        "status: open\n"
        "stage: null\n"
        "contribution: medium\n"
        'created: "2026-05-29T00:00:00Z"\n'
        "closed_at: null\n"
        "human_gate: decision\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [ ] (placeholder)\n"
        "---\n\n"
        f"# {slug}\n\n"
        "## Decision required\n\n"
        "Pick option A or option B.\n"
    )


class _Args:
    def __init__(self, title: str, decision: str, reasoning: str) -> None:
        self.title = title
        self.decision = decision
        self.reasoning = reasoning
        self.commit = False
        self.no_commit = True


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        deck = root / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        engine.REPO_ROOT = root
        engine.DECK_DIR = deck
        slug = "parked-card"
        _new_parked_card(deck, slug)
        readme = deck / slug / "README.md"
        logfile = deck / slug / "log.md"

        print(f"=== Call: goc decide {slug} --decision '' --because '' ===")
        buf = io.StringIO()
        exit_code = 0
        try:
            with redirect_stdout(buf):
                engine._cmd_decide(_Args(slug, "", ""))
        except SystemExit as e:
            exit_code = int(e.code) if e.code is not None else 0
        out = buf.getvalue().rstrip()
        print(f"  exit code: {exit_code}")
        print(f"  stdout (first line): {out.splitlines()[0]!r}")

        body = readme.read_text()
        log_text = logfile.read_text()
        fm_block = body.split("---\n", 2)[1]
        gate_line = next(
            line for line in fm_block.splitlines() if line.startswith("human_gate:")
        )
        decision_section = body.split("## Decision\n\n", 1)[1] if "## Decision\n\n" in body else ""

        print()
        print("=== Resulting README `## Decision` block ===")
        for line in decision_section.splitlines():
            print(f"  | {line}")

        print()
        print("=== Resulting log.md entry ===")
        for line in log_text.rstrip().splitlines():
            print(f"  | {line}")

        print()
        print("=== Verdict ===")
        claimed_success = exit_code == 0 and "decision recorded" in out
        gate_lowered = gate_line.strip() == "human_gate: none"
        import re as _re
        m = _re.search(
            r"\*Resolved [^\n]*?:\*(?P<dec>[^\n]*)\n\n\*Reasoning:\*(?P<rsn>[^\n]*)",
            decision_section,
        )
        body_has_empty_decision = bool(m) and m.group("dec").strip() == "" and m.group("rsn").strip() == ""
        log_has_empty_decision = " — . Gate decision → none." in log_text

        print(f"  exit 0 + 'decision recorded' on stdout?    {claimed_success}")
        print(f"  frontmatter human_gate lowered to 'none'?  {gate_lowered}")
        print(f"  README `## Decision` block has empty body? {body_has_empty_decision}")
        print(f"  log.md entry has empty decision/reasoning? {log_has_empty_decision}")
        defect_fires = (
            claimed_success and gate_lowered and body_has_empty_decision and log_has_empty_decision
        )
        print(f"  DEFECT FIRES (empty-decision-silently-accepted): {defect_fires}")
        sys.exit(0 if defect_fires else 1)


if __name__ == "__main__":
    main()
