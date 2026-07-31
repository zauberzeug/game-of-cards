"""Proof: the English-only guard aborts the whole deck scan on one unparseable
card, instead of falling back to the slug the way its own comment promises.

`scripts/check_card_language.scan_card` calls `engine.parse_frontmatter` with
no `FrontmatterError` net. The comment directly above the fallback line claims
the unreadable-frontmatter case is handled:

    # The directory name is the title of record; fall back to it so a card whose
    # frontmatter the parser cannot read is still checked on its slug.
    frontmatter.setdefault("title", readme.parent.name)

but `setdefault` only rescues the `({}, text)` "no `---` delimiters at all"
return path. When the opener IS present and the document is unparseable,
`parse_frontmatter` RAISES — and because `scan_deck` is a plain comprehension
the raise takes down the scan of every other card with it.

Each case plants ONE malformed card next to a clean, flaggable German control
card. A correct guard reports the control card's findings AND checks the
malformed card on its slug. Exits 0 once fixed.
"""

import importlib.util
import sys
import tempfile
import traceback
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

spec = importlib.util.spec_from_file_location(
    "_goc_card_language_guard", ROOT / "scripts" / "check_card_language.py"
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

# A German slug both marker layers catch, so the slug fallback is provably
# capable of flagging these cards once the crash is netted.
OFFENDER = "kartei-pruefung-fehlt"
CONTROL = "cache-wird-nicht-geleert"

# Three hand-edit slips that all reach `FrontmatterError`, each via a different
# yaml_lite / FRONTMATTER_RE refusal.
CASES = {
    # Opening `---` with no closing delimiter (truncated or interrupted write).
    "unterminated": f'---\ntitle: {OFFENDER}\nsummary: "Die Pruefung fehlt."\n',
    # `status:open` — no space after the colon. yaml_lite refuses rather than
    # silently truncating the rest of the mapping.
    "missing-space": f"---\ntitle: {OFFENDER}\nstatus:open\n---\nbody\n",
    # A key repeated in one mapping — rejected by yaml_lite since ff0fb227.
    "duplicate-key": f"---\ntitle: {OFFENDER}\nstatus: open\nstatus: active\n---\nbody\n",
}

failures = 0
with tempfile.TemporaryDirectory() as tmp:
    deck = Path(tmp) / "deck"
    control = deck / CONTROL
    control.mkdir(parents=True)
    (control / "README.md").write_text(
        f"---\ntitle: {CONTROL}\n"
        'summary: "Der Cache wird nicht geleert."\n'
        "---\nbody\n",
        encoding="utf-8",
    )
    print(f"control card alone -> {len(guard.scan_deck(deck))} finding(s)")

    for name, text in CASES.items():
        card = deck / f"{OFFENDER}-{name}"
        card.mkdir(parents=True)
        (card / "README.md").write_text(text, encoding="utf-8")
        slug_reasons = guard.flag_text(card.name)
        print(f"\n[{name}] flag_text({card.name!r}) -> {slug_reasons}")
        assert slug_reasons, "precondition: the slug itself must be flaggable"
        try:
            findings = guard.scan_deck(deck)
        except Exception as exc:  # noqa: BLE001
            print(f"[{name}] FAIL scan_deck raised {type(exc).__name__}: {exc}")
            traceback.print_exc(limit=1)
            failures += 1
        else:
            cards = {c for c, _f, _r in findings}
            print(f"[{name}] scan_deck -> {len(findings)} finding(s) over {sorted(cards)}")
            if CONTROL not in cards:
                print(f"[{name}] FAIL the clean control card's findings were lost")
                failures += 1
            elif card.name not in cards:
                print(f"[{name}] FAIL the malformed card was not checked on its slug")
                failures += 1
        (card / "README.md").unlink()
        card.rmdir()

print(f"\n{failures} failing case(s) of {len(CASES)}")
sys.exit(1 if failures else 0)
