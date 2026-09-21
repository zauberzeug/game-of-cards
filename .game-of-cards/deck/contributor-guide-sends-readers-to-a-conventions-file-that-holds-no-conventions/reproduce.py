#!/usr/bin/env python3
"""Every factual claim CONTRIBUTING.md makes about this tree, checked against the tree.

Run from the repo root:

    uv run python .game-of-cards/deck/\
contributor-guide-sends-readers-to-a-conventions-file-that-holds-no-conventions/reproduce.py

Exit 0 once every claim below agrees with the repository it describes.

An optional argument points the checks at a different copy of the guide
(`... reproduce.py /tmp/CONTRIBUTING.pre-fix.md`), which is how the failing
direction stays runnable once the tree copy is repaired. Every check reads the
claim it grades out of that text -- none of them hardcodes the wording the file
happened to carry on the day the card was filed, or the check could not flip.
"""

from __future__ import annotations

import io
import re
import sys
import tokenize
from pathlib import Path

def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
TARGET = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "CONTRIBUTING.md"
CONTRIB = TARGET.read_text(encoding="utf-8")
LINES = CONTRIB.splitlines()

failures: list[str] = []
checks = 0


def line_of(needle: str) -> int:
    for i, ln in enumerate(LINES, 1):
        if needle in ln:
            return i
    return -1


checks += 1
# --- 1. the conventions pointer -------------------------------------------
claude_md = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
pointers = [i for i, ln in enumerate(LINES, 1) if "CLAUDE.md`](CLAUDE.md)" in ln]
prose_lines = [ln for ln in claude_md.splitlines() if ln.strip() and not ln.startswith("@")]
print(f"CONTRIBUTING.md routes the reader to CLAUDE.md at lines: {pointers}")
print(f"CLAUDE.md is {len(claude_md)} bytes: {claude_md!r}")
print(f"  lines of prose in CLAUDE.md (excluding the @import): {len(prose_lines)}")
if pointers and not prose_lines:
    failures.append(
        f"CONTRIBUTING.md sends readers to CLAUDE.md for project conventions at "
        f"{len(pointers)} sites, but CLAUDE.md carries {len(prose_lines)} lines of prose "
        f"— it is a bare `@AGENTS.md` import a non-Claude reader cannot follow"
    )

checks += 1
# --- 2. source-file count --------------------------------------------------
src_files = sorted(
    p.relative_to(ROOT).as_posix()
    for p in (ROOT / "goc").rglob("*.py")
    if "templates" not in p.relative_to(ROOT / "goc").parts
)
m = re.search(r"\((\d+) source files under `goc/`\)", CONTRIB)
claimed = int(m.group(1)) if m else None
print(f"\nCONTRIBUTING.md:{line_of('source files under')} claims {claimed} source files under goc/")
print(f"  actual ({len(src_files)}): {', '.join(src_files)}")
if claimed != len(src_files):
    failures.append(f"claims {claimed} source files under goc/; the tree has {len(src_files)}")

checks += 1
# --- 3. plugin-payload roster ---------------------------------------------
payloads = sorted(
    p.name
    for p in ROOT.iterdir()
    if p.is_dir() and p.name.endswith("-plugin") and not p.name.startswith(".")
)
named = sorted({f"{n}-plugin" for n in ("claude", "codex", "openclaw") if f"{n}-plugin/" in CONTRIB})
m = re.search(r"the (\w+) plugin payloads", CONTRIB)
stated = f"the {m.group(1)} plugin payloads" if m else "(no roster phrase found)"
print(f"\nplugin payloads in the tree ({len(payloads)}): {', '.join(payloads)}")
print(f"  named anywhere in CONTRIBUTING.md ({len(named)}): {', '.join(named)}")
print(f"  CONTRIBUTING.md:{line_of('plugin payloads')} says {stated!r}")
if set(payloads) - set(named):
    failures.append(
        f"CONTRIBUTING.md calls the mirror set {stated!r} and never names "
        + ", ".join(sorted(set(payloads) - set(named)))
    )

checks += 1
# --- 4. mirror trees the pre-commit hook owns vs what `goc upgrade` owns ---
sys.path.insert(0, str(ROOT / "scripts"))
import sync_plugin_assets as sync  # noqa: E402

mirror_dsts = sorted({p[1].relative_to(ROOT).as_posix() for p in sync.SYNC_PAIRS})
print(f"\nmirror destinations the sync hook regenerates ({len(mirror_dsts)}):")
for d in mirror_dsts:
    print(f"    {d}")
upgrade_as_mechanism = re.search(
    r"(?:re-)?run `goc upgrade` (?:rather than|instead of)", CONTRIB
)
print(f"  CONTRIBUTING.md:{line_of('goc upgrade`') if upgrade_as_mechanism else -1} "
      f"names `goc upgrade` as the refresh mechanism: {bool(upgrade_as_mechanism)}")
if upgrade_as_mechanism:
    failures.append(
        "CONTRIBUTING.md's coding-conventions bullet names `goc upgrade` as the mirror-refresh "
        "mechanism; `goc upgrade` plans no write into any *-plugin/ payload (it writes into a "
        "consuming repo), so it refreshes none of the three plugin mirror trees the same guide "
        "calls byte-for-byte"
    )

checks += 1
# --- 5. release-time version literals -------------------------------------
rewrite = (ROOT / "scripts" / "release_rewrite_versions.py").read_text(encoding="utf-8")
manifest_targets = sorted(
    set(re.findall(r'ROOT / "([^"]+)"(?: / "([^"]+)")?(?: / "([^"]+)")?', rewrite))
)
targets = sorted({"/".join(x for x in t if x) for t in manifest_targets})
manifests = [t for t in targets if t.endswith((".json",))]
m = re.search(r"`goc/__init__\.py` and the\s+(\w+)\s+plugin manifests", CONTRIB, re.S)
print(f"\nCONTRIBUTING.md:{line_of('plugin manifests')} says the release rewrites "
      f"'`goc/__init__.py` and the {m.group(1) if m else '?'} plugin manifests'")
print(f"  release_rewrite_versions.py rewrites {len(manifests)} manifests: {', '.join(manifests)}")
print(f"  plus non-manifest targets: {', '.join(t for t in targets if t not in manifests)}")
if (m.group(1) if m else None) != {4: "four", 5: "five", 6: "six"}.get(len(manifests)):
    failures.append(
        f"claims the release rewrites '{m.group(1) if m else '?'} plugin manifests'; "
        f"release_rewrite_versions.py rewrites {len(manifests)}"
    )

checks += 1
# --- 6. what `pre-commit run --all-files` actually runs -------------------
pc = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
hook_ids = re.findall(r"^\s+- id: (\S+)", pc, re.MULTILINE)
print(f"\n.pre-commit-config.yaml hooks ({len(hook_ids)}): {', '.join(hook_ids)}")
comments = [
    (i, ln.split("#", 1)[1].strip())
    for i, ln in enumerate(LINES, 1)
    if "pre-commit run --all-files" in ln and "#" in ln
]
for ln_no, comment in comments:
    print(f"  CONTRIBUTING.md:{ln_no} describes it as: {comment!r}")
if any("format" in c for _, c in comments):
    failures.append(
        "CONTRIBUTING.md says `pre-commit run --all-files` 'formats'; no hook in "
        ".pre-commit-config.yaml runs a formatter"
    )
card_hooks = [h for h in hook_ids if h.split("-")[0] == "card"]
unnamed = [h for h in card_hooks if not any(h in c for _, c in comments)]
if unnamed:
    failures.append(
        f"{len(comments)} CONTRIBUTING.md description(s) of the pre-commit set omit "
        + " and ".join(unnamed)
        + " — the two hooks that reject a card a contributor just filed"
    )

checks += 1
# --- 7. the stated quote convention ---------------------------------------
single = double = 0
for p in (ROOT / "goc").rglob("*.py"):
    if "templates" in p.relative_to(ROOT / "goc").parts:
        continue
    for tok in tokenize.tokenize(io.BytesIO(p.read_bytes()).readline):
        if tok.type != tokenize.STRING:
            continue
        s = tok.string.lstrip("rbfuRBFU")
        if s.startswith(('"""', "'''")):
            continue
        if s.startswith('"'):
            double += 1
        elif s.startswith("'"):
            single += 1
total = single + double
m = re.search(r"\b(Single|Double) quotes for strings", CONTRIB)
stated_quote = m.group(1).lower() if m else None
majority = "double" if double > single else "single"
print(f"\nCONTRIBUTING.md:{line_of('quotes for strings')} states the style rule: "
      f"{(m.group(0) + '; f-strings preferred.') if m else '(no quote rule found)'!r}")
print(f"  single-quoted string literals under goc/: {single} ({single / total:.0%})")
print(f"  double-quoted string literals under goc/: {double} ({double / total:.0%})")
if stated_quote != majority:
    counts = {"single": single, "double": double}
    failures.append(
        f"states '{(m.group(1) if m else '?')} quotes for strings' while "
        f"{counts[majority] / total:.0%} of the package's string literals "
        f"({counts[majority]} of {total}) are {majority}-quoted"
    )

# --- verdict ---------------------------------------------------------------
print()
if failures:
    for f in failures:
        print(f"FAIL: {f}")
    print(f"\n{len(failures)} finding(s) across {checks} checked CONTRIBUTING.md claim groups.")
    sys.exit(1)
print("PASS: every checked CONTRIBUTING.md claim agrees with the tree.")
sys.exit(0)
