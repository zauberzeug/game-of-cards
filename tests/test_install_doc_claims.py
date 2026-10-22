"""Regression guard: the install flags and per-flag effects the docs state must match a real install.

`ABOUT.md` § "Agent harnesses", `README.md`'s Generic CLI bullet and `goc.md`
kept describing the install model from before the Claude Code plugin became
the default. They named a `--no-harness` flag that `goc install` rejects with
exit 2. They said `--agents claude` writes `.claude/skills/` and
`.claude/hooks/`, which it does only with `--local-skills`. And they routed
OpenCode users to invocations that vendor no skill files. The one guard on
those pages required the false goc.md parenthetical, so fixing the page would
have turned the build red
(`install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag`).

These tests read each claim out of the pages and run it:

- every flag a doc or shipped template names for `goc install` / `goc upgrade`
  must appear in that verb's `--help` usage;
- every harness bullet (``- `--flags` …``) in an install section must describe
  what installing with those flags writes into a scratch repo;
- every paragraph or list item on an install page that routes OpenCode to a
  `goc install` invocation must name one that leaves skills under
  `.claude/skills/`, which is where those pages say OpenCode reads them;
- goc.md's Claude skill count must equal what the invocation beside it vendors.

Each check is also fed the pre-fix wording verbatim, to prove it fires.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Pages a reader installs GoC from. Only these are read for OpenCode routes:
# elsewhere OpenCode is named beside `goc install` without being routed to it.
INSTALL_PAGES = ("ABOUT.md", "README.md", "goc.md", "site/llms.txt")
# The section of a page that lists harness flags as ``- `--flags` …`` bullets.
HARNESS_SECTIONS = {"ABOUT.md": "## Agent harnesses", "goc.md": "## Install into a repo"}
HOOK_TEMPLATES = ROOT / "goc" / "templates" / "hooks"

_REPO_PATH = re.compile(r"^(?:\.claude/|\.codex/|[A-Z]+\.md$)")
_HARNESS_BULLET = re.compile(r"^- `(--[^`]+)` (.+)$", re.MULTILINE)
_NO_SKILLS = re.compile(r"\bno (?:\w+ (?:or|and) )?skills\b")
_NO_HOOKS = re.compile(r"\bno (?:\w+ (?:or|and) )?hooks\b")
_SKILL_COUNT = re.compile(r"\*\*(\d+) GoC skills\*\* \(([^)]*)\)")

_CHECKS = ("rejected-flag", "harness-bullet", "opencode-route", "skill-count")


def _flag_surfaces() -> list[Path]:
    """Every doc and shipped template that could name an install or upgrade flag."""
    return sorted(
        {
            *ROOT.glob("*.md"),
            ROOT / "site" / "llms.txt",
            *ROOT.glob("*-plugin/README.md"),
            *(ROOT / "goc" / "templates").rglob("*.md"),
        }
    )


def _goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        text=True,
        capture_output=True,
        check=False,
    )


class _Installer:
    """Answers flag lookups and runs `goc install` once per distinct flag set."""

    def __init__(self, work: Path) -> None:
        self.work = work
        self._usage: dict[str, set[str]] = {}
        self._runs: dict[tuple[str, ...], tuple[subprocess.CompletedProcess[str], Path]] = {}

    def accepted(self, verb: str) -> set[str]:
        if verb not in self._usage:
            usage = _goc(self.work, verb, "--help").stdout.split("\n\n", 1)[0]
            self._usage[verb] = set(re.findall(r"\[(--?[\w-]+)", usage))
        return self._usage[verb]

    def install(self, args: tuple[str, ...]) -> tuple[subprocess.CompletedProcess[str], Path]:
        if args not in self._runs:
            repo = Path(tempfile.mkdtemp(dir=self.work))
            self._runs[args] = (_goc(repo, "install", *args), repo)
        return self._runs[args]


def _section(text: str, heading: str) -> str:
    """The body of one `## ` section, or "" if the heading is gone."""
    start = text.find(heading)
    if start == -1:
        return ""
    end = text.find("\n## ", start + 1)
    return text[start:] if end == -1 else text[start:end]


def _code_snippets(text: str) -> list[str]:
    """Inline code spans, plus every line of a fenced block."""
    fence = re.compile(r"^```[^\n]*\n(.*?)^```", re.MULTILINE | re.DOTALL)
    fenced = [line for block in fence.findall(text) for line in block.splitlines()]
    return fenced + re.findall(r"`([^`\n]+)`", fence.sub("", text))


def _invocations(text: str) -> list[tuple[str, tuple[str, ...]]]:
    """`(verb, args)` for every `goc install` / `goc upgrade` in a code snippet."""
    found = []
    for snippet in _code_snippets(text):
        m = re.search(r"(?:^|[\s|])goc (install|upgrade)\b(.*)$", snippet)
        if m:
            found.append((m.group(1), tuple(m.group(2).split())))
    return found


def _blocks(text: str) -> list[str]:
    """Paragraphs and top-level list items."""
    return [b for b in re.split(r"\n\s*\n|\n(?=- )", text) if b.strip()]


def _skill_dirs(repo: Path, rel: str) -> list[str]:
    return sorted(p.parent.name for p in (repo / rel).glob("*/SKILL.md"))


def _written(repo: Path, rel: str) -> bool:
    path = repo / rel
    return any(path.iterdir()) if path.is_dir() else path.is_file()


def _findings(pages: dict[str, str], installer: _Installer) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Grade the install claims in `pages` ({relative path: text}).

    Returns ({check-id: what's wrong}, {check-id: claims checked}).
    """
    out: dict[str, list[str]] = {}
    checked = dict.fromkeys(_CHECKS, 0)

    def report(check: str, message: str) -> None:
        out.setdefault(check, []).append(message)

    # --- 1. every flag named for goc install / goc upgrade exists ----------
    named: list[tuple[str, str, str]] = []
    for name, heading in HARNESS_SECTIONS.items():
        section = _section(pages.get(name, ""), heading)
        for span in re.findall(r"`(--[^`]+)`", section):
            named += [(name, "install", tok) for tok in span.split() if tok.startswith("--")]
    for name, text in pages.items():
        for verb, args in _invocations(text):
            named += [(name, verb, tok.split("=", 1)[0]) for tok in args if tok.startswith("--")]
    for name, verb, flag in dict.fromkeys(named):
        checked["rejected-flag"] += 1
        if flag not in installer.accepted(verb):
            report("rejected-flag", f"{name} names `{flag}`, which `goc {verb}` rejects")

    # --- 2. each harness bullet describes what its flags write -------------
    for name, heading in HARNESS_SECTIONS.items():
        for flags, claim in _HARNESS_BULLET.findall(_section(pages.get(name, ""), heading)):
            checked["harness-bullet"] += 1
            result, repo = installer.install(tuple(flags.split()))
            if result.returncode:
                last = (result.stderr.strip().splitlines() or ["no stderr"])[-1]
                report("harness-bullet", f"{name}: `goc install {flags}` exits {result.returncode} ({last})")
                continue
            paths = [p for p in re.findall(r"`([^`]+)`", claim) if _REPO_PATH.match(p)]
            missing = [p for p in dict.fromkeys(paths) if not _written(repo, p)]
            if missing:
                report("harness-bullet", f"{name}: says `{flags}` writes {', '.join(missing)}; a real install does not")
            skills = sorted(str(p.relative_to(repo).parent) for p in repo.glob(".*/skills/*/SKILL.md"))
            if _NO_SKILLS.search(claim) and skills:
                report("harness-bullet", f"{name}: says `{flags}` writes no skills; it vendors {len(skills)}")
            if _NO_HOOKS.search(claim) and _written(repo, ".claude/hooks"):
                report("harness-bullet", f"{name}: says `{flags}` writes no hooks; it writes .claude/hooks/")
            if "`goc/templates/hooks/`" in claim:
                hooks_dir = repo / ".claude" / "hooks"
                got = sorted(p.name for p in hooks_dir.iterdir()) if hooks_dir.is_dir() else []
                want = sorted(p.name for p in HOOK_TEMPLATES.glob("*.py"))
                if got != want:
                    report("harness-bullet", f"{name}: says `{flags}` writes one hook script per template {want}; it writes {got}")

    # --- 3. every OpenCode route on an install page vendors .claude/skills/ -
    for name in INSTALL_PAGES:
        for block in _blocks(pages.get(name, "")):
            runs = [
                args
                for verb, args in _invocations(block)
                if verb == "install" and not any("<" in a or "…" in a for a in args)
            ]
            if "OpenCode" not in block or not runs:
                continue
            checked["opencode-route"] += 1
            vendored = {args: _skill_dirs(installer.install(args)[1], ".claude/skills") for args in runs}
            if not any(vendored.values()):
                shown = "; ".join(f"`{' '.join(('goc install', *a))}`" for a in vendored)
                report(
                    "opencode-route",
                    f"{name} routes OpenCode, which reads .claude/skills/, to {shown}, "
                    "which vendors no skill there",
                )

    # --- 4. goc.md's skill count is what the invocation beside it vendors --
    for count, aside in _SKILL_COUNT.findall(pages.get("goc.md", "")):
        for verb, args in _invocations(aside):
            if verb != "install":
                continue
            checked["skill-count"] += 1
            got = _skill_dirs(installer.install(args)[1], ".claude/skills")
            if len(got) != int(count):
                report(
                    "skill-count",
                    f"goc.md: '**{count} GoC skills** ({aside})', but "
                    f"`goc install {' '.join(args)}` vendors {len(got)}",
                )

    return out, checked


# The install claims exactly as the three pages carried them before
# `install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag`,
# under their real headings. Feeding them to the same checks proves each one fires.
_HISTORICAL_PAGES = {
    "ABOUT.md": """## Agent harnesses

Harness selection controls which runtime affordances are installed:

- `--agents claude` writes `.claude/skills/`, `.claude/hooks/` (one script per file under `goc/templates/hooks/`), and `CLAUDE.md`.
- `--agents codex` writes Codex-readable skills under `.codex/skills/`, without Claude-only hooks.
- `--no-harness` installs project state and guidance only — no skills, no hooks, no agent-specific files.

Detection is intentionally simple: Claude markers such as `CLAUDE.md` or `.claude/` select the Claude harness; Codex markers such as `AGENTS.md` or `.codex/` select the Codex harness; both marker families install both harnesses. Explicit `--agents`, `--claude`, `--codex`, and `--no-harness` flags override detection for scripted installs.

OpenCode is a free path: it already reads `.claude/skills/`, so `goc install --agents claude` gives OpenCode the skill files without a separate OpenCode shim. The Claude `UserPromptSubmit` hook is not part of that compatibility path; hooks remain Claude Code-specific.
""",
    "README.md": """## Install paths

- **Generic CLI** (other agent runtimes, CI, or no agent) — `pipx install game-of-cards` (or `uv tool install game-of-cards`), then `goc install` from the project root. This is the path for OpenCode, custom runners, or running `goc` by hand.
""",
    "goc.md": """## Claude Code plugin

- **16 GoC skills** (same as `goc install --agents claude`) — auto-discoverable by Claude Code when the plugin is loaded.
""",
}


class InstallDocClaimsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="goc-install-doc-claims-")
        cls.addClassCleanup(cls._tmp.cleanup)
        cls.installer = _Installer(Path(cls._tmp.name))

    def test_docs_agree_with_a_real_install(self) -> None:
        pages = {
            p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8")
            for p in {*_flag_surfaces(), *(ROOT / rel for rel in INSTALL_PAGES)}
        }
        findings, checked = _findings(pages, self.installer)
        self.assertEqual(
            {},
            findings,
            msg=(
                "the docs describe an install the installer does not perform:\n\n"
                + "\n".join(f"[{k}] {m}" for k, ms in sorted(findings.items()) for m in ms)
            ),
        )
        # A reformatted page the parsers no longer read would pass vacuously.
        for check in ("rejected-flag", "harness-bullet", "opencode-route"):
            self.assertGreater(
                checked[check],
                0,
                msg=(
                    f"[{check}] found no claim to check in the live docs. If the claims "
                    "were removed on purpose, drop the check; if the page was reformatted, "
                    "teach the parser the new shape."
                ),
            )

    def test_every_check_fires_on_the_wording_the_card_found(self) -> None:
        findings, _ = _findings(_HISTORICAL_PAGES, self.installer)
        self.assertEqual(
            sorted(_CHECKS),
            sorted(findings),
            msg=(
                "fed the pre-fix install docs verbatim, the guard reported "
                f"{sorted(findings)} instead of every check. A check that stays quiet "
                "on the exact wording it was written for pins nothing."
            ),
        )
        self.assertIn("ABOUT.md names `--no-harness`, which `goc install` rejects", findings["rejected-flag"])


if __name__ == "__main__":
    unittest.main()
