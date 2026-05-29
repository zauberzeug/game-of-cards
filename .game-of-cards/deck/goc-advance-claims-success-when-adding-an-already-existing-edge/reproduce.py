"""Demonstrate that `goc advance` claims success on an already-existing edge.

The verb prints its `advance: ...` success line and exits 0 even when the
bidirectional edge already exists; on-disk READMEs are byte-for-byte
unchanged. This is the symmetric counterpart to
`goc-unadvance-claims-success-when-removing-a-non-existent-edge`.
"""
import hashlib
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


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _new_card(deck: Path, slug: str) -> None:
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
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [ ] (placeholder)\n"
        "---\n\n"
        f"# {slug}\n"
    )


class _Args:
    def __init__(self, title: str, advancer: str) -> None:
        self.title = title
        self.advancer = advancer
        self.commit = False
        self.no_commit = True


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        deck = root / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        engine.REPO_ROOT = root
        engine.DECK_DIR = deck
        _new_card(deck, "a")
        _new_card(deck, "b")
        readme_a = deck / "a" / "README.md"
        readme_b = deck / "b" / "README.md"

        print("=== Call 1: goc advance b --by a (edge does NOT yet exist) ===")
        buf1 = io.StringIO()
        with redirect_stdout(buf1):
            engine._cmd_advance(_Args("b", "a"))
        out1 = buf1.getvalue().rstrip()
        d1_a, d1_b = _digest(readme_a), _digest(readme_b)
        print(f"  stdout: {out1!r}")
        print(f"  sha256(a/README.md)[:12]: {d1_a}")
        print(f"  sha256(b/README.md)[:12]: {d1_b}")

        print()
        print("=== Call 2: goc advance b --by a (edge ALREADY exists) ===")
        buf2 = io.StringIO()
        with redirect_stdout(buf2):
            engine._cmd_advance(_Args("b", "a"))
        out2 = buf2.getvalue().rstrip()
        d2_a, d2_b = _digest(readme_a), _digest(readme_b)
        print(f"  stdout: {out2!r}")
        print(f"  sha256(a/README.md)[:12]: {d2_a}")
        print(f"  sha256(b/README.md)[:12]: {d2_b}")

        print()
        print("=== Verdict ===")
        same_msg = out1 == out2
        no_change = (d1_a == d2_a) and (d1_b == d2_b)
        print(f"  Call 2 prints the same success line as call 1?  {same_msg}")
        print(f"  Call 2 left both READMEs byte-for-byte unchanged? {no_change}")
        defect_fires = same_msg and no_change
        print(f"  DEFECT FIRES (claims-success-on-no-op): {defect_fires}")
        sys.exit(0 if defect_fires else 1)


if __name__ == "__main__":
    main()
