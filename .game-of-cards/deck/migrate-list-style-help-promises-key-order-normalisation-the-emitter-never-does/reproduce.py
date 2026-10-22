"""Reproduce: `goc migrate-list-style` promises key-order normalisation it never performs.

The subparser help and `_cmd_migrate_list_style`'s docstring both named "key
order" among the things a canonical re-emit normalises. `emit_frontmatter`
iterates `fm.items()` — the parsed dict, whose insertion order is the authored
file's own key order — so key order is preserved, never canonicalised.

Prints the three observations that together prove the claim false:
  1. the two user-facing strings, and whether either still promises it;
  2. a card that is canonical except for two swapped keys re-emits byte-identical;
  3. the verb therefore reports that card as already canonical.

A string only *promises* the normalisation when it names key order without
denying it: the fix keeps the phrase in the docstring, explicitly stating that
key order is carried over, so a bare substring test would report the defect
forever. `_promises_key_order` therefore reads each sentence that mentions key
order and clears the ones that deny normalisation.
"""

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

# Canonical order is the one `goc new` writes: title, summary, status, stage, …
# This card swaps `summary` and `status`, and changes nothing else.
REORDERED = """---
title: reordered-keys-card
status: open
summary: canonical everywhere except the key order
stage: null
contribution: medium
created: "2026-09-07T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: nothing
---

# reordered-keys-card

body
"""


def main() -> int:
    print("=== 1. The two user-facing scope strings, at their key-order mention ===")
    parser = engine._build_parser()
    print(f"  subparser help: ...{_excerpt(_subparser_help(parser))}")
    print(f"  docstring     : ...{_excerpt(engine._cmd_migrate_list_style.__doc__)}")

    print()
    print("=== 2. emit_frontmatter on a key-reordered card ===")
    fm, body = engine.parse_frontmatter(REORDERED)
    rewritten = engine.emit_frontmatter(fm, body=body)
    print(f"  parsed key order   : {list(fm)[:4]} ...")
    print(f"  re-emitted == input: {rewritten == REORDERED}")
    print(f"  _reemit_changes    : {engine._reemit_changes(REORDERED, rewritten)}")

    print()
    print("=== 3. What `goc migrate-list-style --dry-run` reports for that card ===")
    with TemporaryDirectory() as tmp:
        deck = Path(tmp) / ".game-of-cards" / "deck" / "reordered-keys-card"
        deck.mkdir(parents=True)
        (deck / "README.md").write_text(REORDERED)
        prev = engine.DECK_DIR
        engine.DECK_DIR = deck.parent
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                engine._cmd_migrate_list_style(_Args(dry_run=True))
            report = buf.getvalue().strip()
        finally:
            engine.DECK_DIR = prev
    print(f"  {report}")

    print()
    claims_key_order = _promises_key_order(_subparser_help(parser)) or _promises_key_order(
        engine._cmd_migrate_list_style.__doc__ or ""
    )
    normalises_key_order = rewritten != REORDERED
    defect = claims_key_order and not normalises_key_order
    print(f"claims key-order normalisation  : {claims_key_order}")
    print(f"performs key-order normalisation: {normalises_key_order}")
    print(f"DEFECT PRESENT: {defect}")
    return 1 if defect else 0


# Wording that puts key order OUTSIDE the normalised set. A sentence naming key
# order clears only when it carries one of these.
_DENIALS = ("not", "carried over", "carried straight through")


def _promises_key_order(text: str) -> bool:
    """True when `text` lists key order among what a canonical re-emit normalises.

    Sentence-scoped rather than substring-scoped: the corrected docstring still
    names key order, to say it is preserved. Only an undenied mention is a promise.
    """
    flat = " ".join((text or "").split())
    for sentence in flat.replace("—", ".").split("."):
        low = sentence.lower()
        if "key order" in low and not any(d in low for d in _DENIALS):
            return True
    return False


class _Args:
    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run


def _subparser_help(parser) -> str:
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if choices and "migrate-list-style" in choices:
            for sub in action._choices_actions:
                if sub.dest == "migrate-list-style":
                    return sub.help or ""
    return ""


def _excerpt(text: str) -> str:
    flat = " ".join((text or "").split())
    idx = flat.find("key order")
    return flat[max(0, idx - 60):idx + 40] if idx >= 0 else "(no 'key order' claim)"


if __name__ == "__main__":
    raise SystemExit(main())
