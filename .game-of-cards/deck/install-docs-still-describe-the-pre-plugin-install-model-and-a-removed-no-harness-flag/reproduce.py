#!/usr/bin/env python3
"""Run the install claims in ABOUT.md, README.md and goc.md against real installs.

What it extracts and how it checks each claim:

- every `goc install` flag the three pages name: the bare flag spans in
  ABOUT.md § "Agent harnesses" and the flags of every `goc install …` /
  `goc upgrade …` code snippet. Each is looked up in the verb's `--help` usage.
- each ABOUT.md harness bullet (`--flags` followed by what they write). The
  script installs with those flags into a scratch repo and checks every repo
  path the bullet names. A bullet that says "no skills" must vendor no SKILL.md.
- each paragraph or list item that routes OpenCode to a `goc install`
  invocation. At least one of those invocations must leave SKILL.md files under
  `.claude/skills/`, the directory the same pages say OpenCode reads.
- goc.md's "**N GoC skills** (… `goc install …` …)". The invocation must
  vendor exactly N skill dirs.

Exits 1 and lists every claim the installer contradicts, 0 when there are none.
"""

from __future__ import annotations

import os
import re
import shutil
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
SURFACES = ("ABOUT.md", "README.md", "goc.md")
HARNESS_SECTION = "## Agent harnesses"
REPO_PATH = re.compile(r"^(?:\.claude/|\.codex/|[A-Z]+\.md$)")
WORK = Path(tempfile.mkdtemp(prefix="goc-install-claims-"))


def _goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"CLAUDECODE", "CLAUDE_CODE", "CLAUDE_PROJECT_DIR"}}
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run([sys.executable, "-m", "goc.cli", *args], cwd=cwd, env=env, text=True, capture_output=True)


def _accepted(verb: str) -> set[str]:
    usage = _goc(WORK, verb, "--help").stdout.split("\n\n", 1)[0]
    return set(re.findall(r"\[(--?[\w-]+)", usage))


def _install(args: list[str]) -> tuple[subprocess.CompletedProcess[str], Path]:
    repo = Path(tempfile.mkdtemp(dir=WORK))
    return _goc(repo, "install", *args), repo


def _skill_dirs(repo: Path, rel: str) -> list[str]:
    return sorted(p.parent.name for p in (repo / rel).glob("*/SKILL.md"))


def _written(repo: Path, rel: str) -> bool:
    path = repo / rel
    return any(path.iterdir()) if path.is_dir() else path.is_file()


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def _code_snippets(text: str) -> list[str]:
    """Inline code spans plus every line of a fenced block."""
    fenced = re.findall(r"^```[^\n]*\n(.*?)^```", text, re.MULTILINE | re.DOTALL)
    prose = re.sub(r"^```[^\n]*\n.*?^```", "", text, flags=re.MULTILINE | re.DOTALL)
    return [ln for block in fenced for ln in block.splitlines()] + re.findall(r"`([^`\n]+)`", prose)


def _invocations(text: str) -> list[tuple[str, list[str]]]:
    found = []
    for snippet in _code_snippets(text):
        m = re.search(r"(?:^|[\s|])goc (install|upgrade)\b(.*)$", snippet)
        if m:
            found.append((m.group(1), m.group(2).split()))
    return found


def _blocks(text: str) -> list[str]:
    """Paragraphs and top-level list items."""
    return [b for b in re.split(r"\n\s*\n|\n(?=- )", text) if b.strip()]


def main() -> int:
    pages = {name: (ROOT / name).read_text(encoding="utf-8") for name in SURFACES}
    accepted = {verb: _accepted(verb) for verb in ("install", "upgrade")}
    contradicted: list[str] = []
    checked = 0

    # 1. Every flag the pages name must be one the parser accepts.
    harness = _section(pages["ABOUT.md"], HARNESS_SECTION)
    named: list[tuple[str, str, str]] = [
        ("ABOUT.md", "install", tok)
        for span in re.findall(r"`(--[^`]+)`", harness)
        for tok in span.split()
        if tok.startswith("--")
    ]
    for name, text in pages.items():
        named += [(name, verb, tok.split("=")[0]) for verb, args in _invocations(text) for tok in args if tok.startswith("--")]
    for name, verb, flag in dict.fromkeys(named):
        checked += 1
        if flag not in accepted[verb]:
            contradicted.append(f"{name}: names `{flag}`, which `goc {verb}` rejects (not in its --help usage)")

    # 2. Each ABOUT.md harness bullet: install with its flags, check what it says lands.
    for flags, claim in re.findall(r"^- `(--[^`]+)` (.+)$", harness, re.MULTILINE):
        checked += 1
        result, repo = _install(flags.split())
        if result.returncode:
            contradicted.append(f"ABOUT.md: `goc install {flags}` exits {result.returncode}: {result.stderr.strip().splitlines()[-1]}")
            continue
        paths = [p for p in re.findall(r"`([^`]+)`", claim) if REPO_PATH.match(p)]
        missing = [p for p in paths if not _written(repo, p)]
        if missing:
            contradicted.append(f"ABOUT.md: says `goc install {flags}` writes {', '.join(missing)}; a real install does not")
        vendored = [str(p.relative_to(repo).parent) for p in repo.rglob("SKILL.md")]
        if "no skills" in claim and vendored:
            contradicted.append(f"ABOUT.md: says `goc install {flags}` writes no skills; it vendors {len(vendored)}")

    # 3. Every block routing OpenCode to an install must name one that vendors .claude/skills/.
    for name, text in pages.items():
        for block in _blocks(text):
            runs = [args for verb, args in _invocations(block) if verb == "install"]
            if "OpenCode" not in block or not runs:
                continue
            checked += 1
            counts = {" ".join(["goc install", *args]): len(_skill_dirs(_install(args)[1], ".claude/skills")) for args in runs}
            if not any(counts.values()):
                shown = "; ".join(f"`{inv}` vendors {n}" for inv, n in counts.items())
                contradicted.append(f"{name}: routes OpenCode (which reads .claude/skills/) to an install that vendors no skill there: {shown}")

    # 4. goc.md's Claude skill count must be what its named invocation vendors.
    for count, aside in re.findall(r"\*\*(\d+) GoC skills\*\* \(([^)]*)\)", pages["goc.md"]):
        for verb, args in _invocations(aside):
            checked += 1
            got = _skill_dirs(_install(args)[1], ".claude/skills")
            if len(got) != int(count):
                contradicted.append(f"goc.md: '**{count} GoC skills** ({aside})' — `goc install {' '.join(args)}` vendors {len(got)}")

    print(f"checked {checked} install claims across {', '.join(SURFACES)}")
    for line in contradicted:
        print(f"  CONTRADICTED  {line}")
    if contradicted:
        print(f"\nFAIL: the installer contradicts {len(contradicted)} documented claim(s).")
        return 1
    print("\nOK: every documented install flag and per-flag effect matches a real install.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(WORK, ignore_errors=True)
