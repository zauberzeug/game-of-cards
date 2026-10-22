#!/usr/bin/env python3
"""Run the shipped aggregation-epic recipe verbatim and check what it builds.

`goc/templates/skills/advance-card/reference.md` states the canonical epic
encoding and then gives the verb form to produce it. This scaffolds a throwaway
deck, extracts both halves from the shipped text (so the check cannot drift
from the doc — neither the encoding nor the verb's argument order is written
down here), runs the verb, and compares the edges it built against the
encoding the same file states one line earlier.

Exit 0 when the documented verb produces the documented encoding and
`goc validate` stays silent. Before the fix it exited 1: the recipe read
`goc advance <child> --by <epic>`, which builds `epic.advances: [children]` —
the shape the same bullet list calls "Backwards aggregation … Never."
"""

from __future__ import annotations

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

REF = ROOT / "goc" / "templates" / "skills" / "advance-card" / "reference.md"
REL = REF.relative_to(ROOT)
text = REF.read_text(encoding="utf-8")
lines = text.splitlines()


def _line_of(needle: str) -> int:
    for i, ln in enumerate(lines, 1):
        if needle in ln:
            return i
    return -1


def _require(match, what: str):
    if match is None:
        sys.exit(f"ERROR: could not read {what} out of {REL} — the recipe's "
                 "wording moved; re-derive this script against it.")
    return match


# --- what the shipped text says -------------------------------------------
# Both the encoding and the verb are read from the file, and nothing below
# assumes which role sits in which argument slot — so a future swap in either
# direction is caught rather than baked in.
flat = re.sub(r"\s+", " ", text)
canonical = _require(
    re.search(r"Encoding: `(\w+)\.(advances|advanced_by): \[(\w+)\]`", flat),
    "the canonical encoding",
)
verb = _require(
    re.search(r"Verb on the \w+: `goc advance <(\w+)> --by <(\w+)>`", flat),
    "the verb form",
)
forbidden = _require(
    re.search(r"\*\*Backwards aggregation\*\* — `(\w+)\.advances: \[(\w+)\]`\. \*\*Never\.\*\*", text),
    "the forbidden shape",
)

owner, field, held = canonical.groups()
verb_title, verb_advancer = verb.groups()

print(f"{REL}:{_line_of('Encoding: `child.advances')} states the canonical encoding: {canonical.group(0)}")
print(f"{REL}:{_line_of('Verb on the')} gives the verb:               "
      f"goc advance <{verb_title}> --by <{verb_advancer}>")
print(f"{REL}:{_line_of('Backwards aggregation')} forbids:                      {forbidden.group(0)}")

# --- what the engine's verb actually does ---------------------------------
from goc import engine  # noqa: E402

src_line = next(
    (i for i, ln in enumerate(Path(engine.__file__).read_text().splitlines(), 1)
     if "advanced_by += {advancer}; {advancer}.advances += {title}" in ln),
    -1,
)
print(f"\ngoc/engine.py:{src_line} — `goc advance <title> --by <advancer>` writes "
      "advancer.advances += title")

# --- run the recipe verbatim in a throwaway deck --------------------------
EPIC = "ship-the-epic"
CHILDREN = ("child-one", "child-two")
CONTRIBUTIONS = {EPIC: "high", CHILDREN[0]: "low", CHILDREN[1]: "low"}


def slots(child: str) -> dict[str, str]:
    """Map the recipe's role placeholders onto scratch-deck slugs."""
    return {"epic": EPIC, "epics": EPIC, "child": child, "children": child}


with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp) / "repo"
    repo.mkdir()
    env = {"PATH": "/usr/bin:/bin", "HOME": tmp, "PYTHONPATH": str(ROOT)}
    py = sys.executable

    def goc(*args: str) -> str:
        r = subprocess.run([py, "-m", "goc.cli", *args], cwd=repo, env=env,
                           capture_output=True, text=True)
        return r.stdout + r.stderr

    subprocess.run(["git", "init", "-q", "."], cwd=repo, env=env, check=True)
    goc("install")
    for t in CONTRIBUTIONS:
        goc("new", t)
        goc("publish", t)
    deck = repo / ".game-of-cards" / "deck"
    for t, c in CONTRIBUTIONS.items():
        p = deck / t / "README.md"
        p.write_text(re.sub(r"^contribution: .*$", f"contribution: {c}",
                            p.read_text(), flags=re.M))

    def edges(t: str) -> tuple[list[str], list[str]]:
        card = engine.parse_frontmatter((deck / t / "README.md").read_text())[0]
        return card.get("advances") or [], card.get("advanced_by") or []

    def backwards_warning() -> str | None:
        hits = [ln.strip() for ln in goc("validate").splitlines() if "BACKWARDS_EPIC_EDGE" in ln]
        return hits[0] if hits else None

    print(f"\n--- running the shipped verb form verbatim: "
          f"goc advance <{verb_title}> --by <{verb_advancer}> ---")
    for child in CHILDREN:
        slot = slots(child)
        print("   ", goc("advance", slot[verb_title], "--by", slot[verb_advancer]).strip().splitlines()[0])

    epic_adv, epic_by = edges(EPIC)
    kid_adv, kid_by = edges(CHILDREN[0])
    print(f"\n    {EPIC}.advances    = {epic_adv}")
    print(f"    {EPIC}.advanced_by = {epic_by}")
    print(f"    {CHILDREN[0]}.advances        = {kid_adv}")
    print(f"    {CHILDREN[0]}.advanced_by     = {kid_by}")

    warning = backwards_warning()
    print(f"\n    goc validate: {warning or 'no BACKWARDS_EPIC_EDGE warning'}")

    # The encoding claim resolved onto the scratch deck: the shipped text says
    # `<owner>.<field>` holds `<held>`, so read exactly that card and field.
    owner_slug, held_slug = slots(CHILDREN[0])[owner], slots(CHILDREN[0])[held]
    built = dict(zip(("advances", "advanced_by"), edges(owner_slug)))[field]

    print(f"\n--- the other argument order, for contrast: "
          f"goc advance <{verb_advancer}> --by <{verb_title}> ---")
    for child in CHILDREN:
        slot = slots(child)
        goc("unadvance", slot[verb_title], "--by", slot[verb_advancer])
        goc("advance", slot[verb_advancer], "--by", slot[verb_title])
    print(f"    {EPIC}.advances = {edges(EPIC)[0]}")
    print(f"    {CHILDREN[0]}.advances     = {edges(CHILDREN[0])[0]}")
    print(f"    goc validate: {backwards_warning() or 'no BACKWARDS_EPIC_EDGE warning'}")

print()
problems = []
if held_slug not in built:
    problems.append(
        f"the verb form at {REL}:{_line_of('Verb on the')} left "
        f"{owner}.{field} = {built}, but the same file states the canonical "
        f"encoding is `{owner}.{field}: [{held}]`. `goc advance <title> --by "
        "<advancer>` writes advancer.advances += title, so the arguments are swapped."
    )
if warning:
    problems.append(
        'the recipe tripped the shape the same file calls "Backwards '
        f'aggregation … Never.": {warning}'
    )
if problems:
    for p in problems:
        print(f"FAIL: {p}")
    sys.exit(1)
print(f"PASS: the documented verb `goc advance <{verb_title}> --by <{verb_advancer}>` "
      f"produces the documented encoding `{owner}.{field}: [{held}]`, "
      "and goc validate emits no BACKWARDS_EPIC_EDGE.")
sys.exit(0)
