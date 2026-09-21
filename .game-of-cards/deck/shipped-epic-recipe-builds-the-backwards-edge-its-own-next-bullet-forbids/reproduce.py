#!/usr/bin/env python3
"""Run the shipped aggregation-epic recipe verbatim and check what it builds.

`goc/templates/skills/advance-card/reference.md` states the canonical epic
encoding and then gives the verb form to produce it. This scaffolds a throwaway
deck, extracts the verb form from the shipped text (so the check cannot drift
from the doc), runs it, and compares the resulting edges against the canonical
encoding the same file states one line earlier.

Exit 0 when the documented verb produces the documented encoding.
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
text = REF.read_text(encoding="utf-8")
lines = text.splitlines()


def _line_of(needle: str) -> int:
    for i, ln in enumerate(lines, 1):
        if needle in ln:
            return i
    return -1


# --- what the shipped text says -------------------------------------------
canonical = re.search(r"Encoding: `(child|epic)\.advances: \[(epic|children)\]`", text)
flat = re.sub(r"\s+", " ", text)
verb = re.search(r"Verb on the child: `goc advance (<\w+>) --by (<\w+>)`", flat)
forbidden = re.search(r"\*\*Backwards aggregation\*\* — `(epic)\.advances: \[(children)\]`\. \*\*Never\.\*\*", text)

print(f"{REF.relative_to(ROOT)}:{_line_of('Encoding: `child.advances')} "
      f"states the canonical encoding: {canonical.group(0) if canonical else '??'}")
print(f"{REF.relative_to(ROOT)}:{_line_of('--by <epic>')} "
      f"gives the verb:               goc advance {verb.group(1)} --by {verb.group(2)}"
      if verb else "  verb form not found")
print(f"{REF.relative_to(ROOT)}:{_line_of('Backwards aggregation')} "
      f"forbids:                      {forbidden.group(0) if forbidden else '??'}")

# --- what the engine's verb actually does ---------------------------------
from goc import engine  # noqa: E402

doc = engine._cmd_advance.__doc__ or ""
src_line = next(
    (i for i, ln in enumerate(Path(engine.__file__).read_text().splitlines(), 1)
     if "advanced_by += {advancer}; {advancer}.advances += {title}" in ln),
    -1,
)
print(f"\ngoc/engine.py:{src_line} — `goc advance <title> --by <advancer>` writes "
      "advancer.advances += title")

# --- run the recipe verbatim in a throwaway deck --------------------------
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
    for t in ("ship-the-epic", "child-one", "child-two"):
        goc("new", t)
        goc("publish", t)
    deck = repo / ".game-of-cards" / "deck"
    for t, c in (("ship-the-epic", "high"), ("child-one", "low"), ("child-two", "low")):
        p = deck / t / "README.md"
        p.write_text(re.sub(r"^contribution: .*$", f"contribution: {c}",
                            p.read_text(), flags=re.M))

    print("\n--- running the shipped verb form verbatim ---")
    for child in ("child-one", "child-two"):
        # the recipe: `goc advance <child> --by <epic>`
        print("   ", goc("advance", child, "--by", "ship-the-epic").strip().splitlines()[0])

    def edges(t: str) -> tuple[list[str], list[str]]:
        card = engine.parse_frontmatter((deck / t / "README.md").read_text())[0]
        return card.get("advances") or [], card.get("advanced_by") or []

    epic_adv, epic_by = edges("ship-the-epic")
    kid_adv, kid_by = edges("child-one")
    print(f"\n    ship-the-epic.advances    = {epic_adv}")
    print(f"    ship-the-epic.advanced_by = {epic_by}")
    print(f"    child-one.advances        = {kid_adv}")
    print(f"    child-one.advanced_by     = {kid_by}")

    validate = goc("validate")
    backwards = [ln for ln in validate.splitlines() if "BACKWARDS_EPIC_EDGE" in ln]
    print(f"\n    goc validate: {backwards[0].strip() if backwards else 'no BACKWARDS_EPIC_EDGE warning'}")

    print("\n--- the un-swapped form, for contrast: goc advance <epic> --by <child> ---")
    goc("unadvance", "child-one", "--by", "ship-the-epic")
    goc("unadvance", "child-two", "--by", "ship-the-epic")
    for child in ("child-one", "child-two"):
        goc("advance", "ship-the-epic", "--by", child)
    epic_adv2, _ = edges("ship-the-epic")
    kid_adv2, _ = edges("child-one")
    print(f"    ship-the-epic.advances = {epic_adv2}")
    print(f"    child-one.advances     = {kid_adv2}")
    v2 = [ln for ln in goc("validate").splitlines() if "BACKWARDS_EPIC_EDGE" in ln]
    print(f"    goc validate: {v2[0].strip() if v2 else 'no BACKWARDS_EPIC_EDGE warning'}")

print()
if epic_adv:
    print("FAIL: the verb form at "
          f"{REF.relative_to(ROOT)}:{_line_of('--by <epic>')} produced "
          f"epic.advances = {epic_adv} — the shape the same file calls "
          '"Backwards aggregation … Never." and goc validate flags as '
          "BACKWARDS_EPIC_EDGE. The canonical child.advances: [epic] encoding "
          "needs `goc advance <epic> --by <child>`.")
    sys.exit(1)
print("PASS: the documented verb form produces the documented encoding.")
sys.exit(0)
