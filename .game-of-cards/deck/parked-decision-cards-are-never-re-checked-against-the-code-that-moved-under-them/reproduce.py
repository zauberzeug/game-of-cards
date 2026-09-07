#!/usr/bin/env python3
"""Find gated cards whose cited code no longer exists, and check nobody re-read them.

A card at `human_gate: decision` is a claim about code, held until a human
reads it. Nothing re-evaluates the claim while it waits. This probe looks for
the cheapest observable symptom of a claim that has gone stale: the card
quotes a line of source, and that line is nowhere in HEAD.

Two things make the measurement non-obvious.

**Anchor AS FILED, not as last written.** `Skill(refine-deck)` anchors a cite
at the commit that last WROTE the line number, which is the right rule for
*repairing* a drifted number. It is the wrong rule for detecting staleness,
because the repair step relocates the number onto a line that does exist —
consuming the signal. Both known stale parks below were repaired by the
2026-08-10 pass and are invisible to last-write anchoring at HEAD. Anchoring
each cite at the card's FILING commit asks the question the card actually
poses: is the code I described still here?

**Two passing states.** An empty offender list reads the same whether nothing
is stale or nothing was scanned (see
`static-source-guards-never-prove-they-can-catch-an-offender`). So the probe
runs controls before it trusts a scan: a synthetic offender that MUST be
caught, a synthetic clean case that MUST NOT be, and the two live cards known
to be stale. If any control misbehaves the probe errors out rather than
reporting a clean deck.

Exit 1 while a stale-park candidate carries no record that anyone re-read it.
Exit 0 once every candidate is either retired or marked re-checked — whichever
mechanism the card's `## Decision required` picks, all four produce one of
those.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# A candidate counts as SURFACED when the deck records that someone re-read it.
RECHECK_MARKER = re.compile(r"^##\s+.*\bStaleness re-check\b", re.M)
TERMINAL = ("done", "superseded", "disproved")

# Cards whose cited defect is known — verified by hand on 2026-08-24 — to be
# fixed already. Positive controls: a scan that misses these is not sensitive.
KNOWN_STALE = (
    "goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits",
    "waiting-flag-filters-on-waiting-on-field-not-the-impediment-overlay",
)

CITE = re.compile(r"([A-Za-z0-9_./\-]+\.(?:py|md|ya?ml|json|ts|sh|toml|txt))[:#](\d+)")
MIRROR = ("claude-plugin/", "codex-plugin/", "openclaw-plugin/", ".claude/", ".codex/")
MIN_ANCHOR = 12  # shorter lines are too generic to prove anything


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
DECK = ROOT / ".game-of-cards" / "deck"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    ).stdout


def build_suffix_index() -> dict[str, list[str]]:
    """Map every path suffix to the tracked files that end with it.

    Cards write `engine.py:N` for `goc/engine.py:N` and `standup/SKILL.md:N`
    for the template under `goc/templates/skills/`, so resolution is by
    suffix, preferring the non-mirror copy.
    """
    index: dict[str, list[str]] = {}
    for path in git("ls-files").split():
        if path.startswith(".game-of-cards/deck/"):
            continue
        parts = path.split("/")
        for i in range(len(parts)):
            index.setdefault("/".join(parts[i:]), []).append(path)
    return index


SUFFIX = build_suffix_index()


def resolve(cite_path: str):
    candidates = SUFFIX.get(cite_path, [])
    if not candidates:
        return None
    pool = [c for c in candidates if not c.startswith(MIRROR)] or candidates
    return sorted(pool, key=lambda c: (c.count("/"), len(c)))[0]


def batch_cat(specs):
    """Read many `<rev>:<path>` blobs in one `git cat-file --batch` call."""
    specs = list(dict.fromkeys(specs))
    if not specs:
        return {}
    out = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=ROOT,
        input=("\n".join(specs) + "\n").encode(),
        capture_output=True,
    ).stdout
    blobs, i = {}, 0
    for spec in specs:
        nl = out.find(b"\n", i)
        if nl < 0:
            break
        header = out[i:nl].decode("utf-8", "replace")
        if header.endswith(("missing", "ambiguous")):
            blobs[spec] = None
            i = nl + 1
            continue
        size = int(header.split()[-1])
        blobs[spec] = out[nl + 1 : nl + 1 + size].decode("utf-8", "replace")
        i = nl + 1 + size + 1
    return blobs


def trivial(line: str) -> bool:
    s = line.strip()
    return len(s) < MIN_ANCHOR or s in ("{", "}", "(", ")", "[", "]", '"""', "'''")


_HEAD: dict[str, str | None] = {}


def head_text(path: str):
    if path not in _HEAD:
        f = ROOT / path
        _HEAD[path] = (
            f.read_text(encoding="utf-8", errors="replace") if f.exists() else None
        )
    return _HEAD[path]


def absent_from_head(path: str, anchor: str) -> bool:
    body = head_text(path)
    return body is None or anchor.strip() not in body


def cites_in(body: str):
    seen, out = set(), []
    for m in CITE.finditer(body):
        key = (m.group(1), int(m.group(2)))
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def scan_card(title: str):
    """Anchor a card's cites at its filing commit; return (checked, absent)."""
    rel = f".game-of-cards/deck/{title}/README.md"
    commits = git("log", "--format=%H", "--follow", "--", rel).split()
    if not commits:
        return 0, []
    filing = commits[-1]
    body = batch_cat([f"{filing}:{rel}"]).get(f"{filing}:{rel}")
    if body is None:
        return 0, []

    wanted, meta = [], []
    for cite_path, lineno in cites_in(body):
        resolved = resolve(cite_path)
        if resolved is None:
            continue  # path itself is gone or was never in-tree; not our signal
        wanted.append(f"{filing}:{resolved}")
        meta.append((cite_path, lineno, resolved))

    sources = batch_cat(wanted)
    checked, absent = 0, []
    for cite_path, lineno, resolved in meta:
        src = sources.get(f"{filing}:{resolved}")
        if src is None:
            continue
        lines = src.split("\n")
        if lineno > len(lines):
            continue
        anchor = lines[lineno - 1]
        if trivial(anchor):
            continue
        checked += 1
        if absent_from_head(resolved, anchor):
            absent.append((f"{cite_path}:{lineno}", resolved, anchor.strip()))
    return checked, absent


# --------------------------------------------------------------------------
# Controls — prove the detector can both catch an offender and clear a clean
# case before any empty result is believed.
# --------------------------------------------------------------------------


def run_controls() -> list[str]:
    failures = []

    # Synthetic offender: an anchor that is certainly not in the tree.
    if not absent_from_head(
        "goc/engine.py", "def this_function_has_never_existed_anywhere(  # sentinel"
    ):
        failures.append("synthetic offender was NOT flagged absent")

    # Synthetic clean case: a line that is certainly in the tree right now.
    live = (ROOT / "goc" / "engine.py").read_text(encoding="utf-8").split("\n")
    control_line = next(
        (ln for ln in live if ln.strip().startswith("def ") and len(ln.strip()) > 30),
        None,
    )
    if control_line is None:
        failures.append("could not build a synthetic clean case from goc/engine.py")
    elif absent_from_head("goc/engine.py", control_line):
        failures.append("synthetic clean case WAS flagged absent (false positive)")

    # The cite regex must actually match the forms cards use.
    if len(cites_in("see `goc/engine.py:2846` and engine.py:130 plus x.md:7")) != 3:
        failures.append("cite regex stopped matching the in-deck citation forms")

    # Live positive controls: both known stale parks must be caught.
    for title in KNOWN_STALE:
        if not (DECK / title / "README.md").exists():
            failures.append(f"known-stale control {title} is no longer in the deck")
            continue
        checked, absent = scan_card(title)
        if checked == 0:
            failures.append(f"known-stale control {title}: nothing scanned")
        elif not absent:
            failures.append(
                f"known-stale control {title}: scanned {checked} anchors, caught none"
            )
    return failures


def surfaced(title: str, card: dict) -> bool:
    """Has anyone recorded a re-read of this card?"""
    if card["status"] in TERMINAL:
        return True
    if card.get("superseded_by"):
        return True
    log = DECK / title / "log.md"
    return log.exists() and bool(RECHECK_MARKER.search(log.read_text(encoding="utf-8")))


def main() -> int:
    print("controls ...")
    failures = run_controls()
    if failures:
        for f in failures:
            print(f"  CONTROL FAILED: {f}")
        print("\nERROR: the detector cannot be trusted; not reporting a scan.")
        return 2
    print(f"  ok — synthetic offender caught, clean case cleared, "
          f"{len(KNOWN_STALE)}/{len(KNOWN_STALE)} known stale parks caught\n")

    raw = subprocess.run(
        [sys.executable, "-m", "goc.cli", "--status", "all", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    ).stdout
    cards = json.loads(raw)
    gated = [
        c
        for c in cards
        if c["status"] in ("open", "active") and c["human_gate"] != "none"
    ]

    scanned, candidates, total_absent = 0, [], 0
    for card in gated:
        checked, absent = scan_card(card["title"])
        if checked:
            scanned += 1
        if absent:
            total_absent += len(absent)
            candidates.append((card, absent))

    print(f"gated open/active cards                   : {len(gated)}")
    print(f"  with >=1 resolvable as-filed anchor     : {scanned}")
    print(f"  with >=1 as-filed anchor absent at HEAD : {len(candidates)}")
    print(f"  absent anchors                          : {total_absent}")

    unsurfaced = [(c, a) for c, a in candidates if not surfaced(c["title"], c)]
    print(f"  ... of those, never re-read by anyone   : {len(unsurfaced)}\n")

    for card, absent in unsurfaced:
        print(f"{card['title']}  [{card['human_gate']}, filed {(card.get('created') or '')[:10]}]")
        for token, resolved, anchor in absent[:3]:
            print(f"    {token} -> {resolved}")
            print(f"      anchor gone: {anchor[:78]!r}")

    if unsurfaced:
        print(
            f"\nDEFECT PRESENT: {len(unsurfaced)} gated cards quote code that is no "
            f"longer in the tree, and nothing has re-read any of them. Each is a "
            f"decision a human may be asked to take on a premise that has expired."
        )
        return 1
    print(f"\nPASS: every stale-park candidate is retired or marked re-checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
