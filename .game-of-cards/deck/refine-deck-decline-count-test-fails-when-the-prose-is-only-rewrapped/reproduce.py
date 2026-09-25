#!/usr/bin/env python3
"""ResidueAccountingTest fails on a pure rewrap of the refine-deck prose.

Two reads in `tests/test_refine_deck_citation_anchor.py` find a phrase that
runs through hard-wrapped prose with a regex holding literal single spaces:
`declines split (\\w+) ways` over reference.md, and
`Cites the recipe declines — (.+?) — are REPORTED` over SKILL.md.  Move one
line break inside either phrase and the guard fails — the second one saying
that SKILL.md "no longer lists what the citation recipe declines" — while
every word, the list and the count are unchanged.  The same file ships
`_flat`, whose docstring says it exists "so rules survive rewrapping"; these
two reads do not use it.

Runs ResidueAccountingTest three ways: over the shipped files (the control),
then over temp copies in which exactly one space inside each phrase has
become a line break — the edit a different fill column produces.  Only
whitespace changes, so a correct guard passes all three.  Exits 0 when the
rewrapped runs pass too.
"""
import importlib.util
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
TESTS = ROOT / "tests" / "test_refine_deck_citation_anchor.py"


def load():
    spec = importlib.util.spec_from_file_location("anchor_tests", TESTS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def break_inside(text: str, phrase: str, before: str) -> str:
    """Turn the space before the word `before` inside `phrase` into a newline.

    `phrase` is located whitespace-tolerantly, so the edit applies wherever
    the shipped text happens to wrap today; everything else is untouched.
    """
    words = phrase.split()
    pattern = r"\s+".join(re.escape(w) for w in words)
    match = re.search(pattern, text)
    if match is None:
        raise SystemExit(f"phrase not found, reproducer is stale: {phrase!r}")
    flat = " ".join(words)
    cut = flat.index(" " + before)
    rewrapped = flat[:cut] + "\n" + flat[cut + 1:]
    return text[:match.start()] + rewrapped + text[match.end():]


def run(mod, skill: Path, reference: Path) -> list[str]:
    mod.SKILL, mod.REFERENCE = skill, reference
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        mod.ResidueAccountingTest)
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return [f"{test.id().rsplit('.', 1)[1]}: {tb.strip().splitlines()[-1]}"
            for test, tb in result.failures + result.errors]


def main() -> int:
    mod = load()
    skill_text = mod.SKILL.read_text(encoding="utf-8")
    ref_text = mod.REFERENCE.read_text(encoding="utf-8")
    count = re.search(r"declines\s+split\s+(\w+)\s+ways", ref_text).group(1)

    variants = [
        ("shipped files (control)", skill_text, ref_text),
        (f"reference.md: 'declines split {count}\\nways'", skill_text,
         break_inside(ref_text, f"declines split {count} ways", "ways")),
        ("SKILL.md: '—\\nare REPORTED'",
         break_inside(skill_text, "— are REPORTED", "are"), ref_text),
    ]
    rewrap_failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for label, skill, ref in variants:
            s, r = Path(tmp) / "SKILL.md", Path(tmp) / "reference.md"
            s.write_text(skill, encoding="utf-8")
            r.write_text(ref, encoding="utf-8")
            whitespace_only = (skill.split() == skill_text.split()
                               and ref.split() == ref_text.split())
            failures = run(mod, s, r)
            print(f"{label}")
            print(f"    words unchanged: {whitespace_only}")
            print(f"    ResidueAccountingTest: "
                  f"{'FAIL' if failures else 'ok'}")
            for line in failures:
                print(f"      {line}")
            if label != variants[0][0]:
                rewrap_failures += bool(failures)
    print()
    print(f"rewraps the guard rejects: {rewrap_failures} of {len(variants) - 1}")
    return 1 if rewrap_failures else 0


if __name__ == "__main__":
    sys.exit(main())
