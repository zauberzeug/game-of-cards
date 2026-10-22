"""Reproduce: Codex install guidance predates the Codex plugin and its bundled engine.

The Codex plugin shipped on 2026-05-18 (f1bd886c; `publish-codex-plugin` closed
2026-05-18T05:33:03Z). On 2026-06-09 (eaed2d24) it gained a bundled-engine
helper, `skills/_goc-bootstrap.sh`, and every Codex skill gained a
`## Codex GoC Command` block that resolves `goc` through it. The first commit
updated README.md and added Codex sections to goc.md and site/llms.txt; the
second updated codex-plugin/README.md, Skill(codex-kickoff) and the Codex
skills. This script checks the surfaces neither commit revisited.

The delivery-channel set is derived from the plugin manifests in the tree, not
restated here. Exit 1 while any stale claim survives, 0 once every surface
agrees. Read-only: it parses files and runs `goc install --help`, nothing else.
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
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

from goc import install as goc_install  # noqa: E402

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def ok(msg: str) -> None:
    print(f"ok:   {msg}")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def line_of(text: str, needle: str) -> int:
    idx = text.find(needle)
    return text.count("\n", 0, idx) + 1 if idx >= 0 else -1


def md_section(text: str, heading: str) -> str:
    """Body of the markdown section opened by `heading`, up to the next peer."""
    level = heading.split(" ", 1)[0]
    start = text.find(heading + "\n")
    if start < 0:
        return ""
    nxt = re.search(rf"^{re.escape(level)} ", text[start + len(heading):], re.M)
    return text[start: start + len(heading) + (nxt.start() if nxt else len(text))]


NUMBER_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}

# --- 1. What the tree ships ---------------------------------------------------
MANIFESTS = {
    "Claude Code plugin": "claude-plugin/.claude-plugin/plugin.json",
    "Codex plugin": "codex-plugin/.codex-plugin/plugin.json",
    "OpenClaw plugin": "openclaw-plugin/openclaw.plugin.json",
}
channels = [name for name, rel in MANIFESTS.items() if (ROOT / rel).is_file()]
channels.append("Generic CLI (PyPI)")
codex_ships = "Codex plugin" in channels
helper = ROOT / "codex-plugin" / "skills" / "_goc-bootstrap.sh"
codex_skills = sorted((ROOT / "codex-plugin" / "skills").glob("*/SKILL.md"))
resolver_skills = [p for p in codex_skills if "## Codex GoC Command" in p.read_text(encoding="utf-8")]
print(f"tree: {len(channels)} delivery channels -> {', '.join(channels)}")
print(f"tree: codex-plugin ships {helper.relative_to(ROOT)}: {helper.is_file()}; "
      f"{len(resolver_skills)}/{len(codex_skills)} Codex plugin skills carry the "
      f"'## Codex GoC Command' resolver")
print()

# --- 2. Control group: surfaces the plugin commits did update -----------------
readme = read("README.md")
if "four first-class delivery channels" in readme and "**Codex plugin**" in readme:
    ok(f"README.md:{line_of(readme, 'four first-class')} four channels, Codex plugin listed")
llms = read("site/llms.txt")
if "## Install (Codex)" in llms:
    ok(f"site/llms.txt:{line_of(llms, '## Install (Codex)')} has an Install (Codex) section")
codex_readme = read("codex-plugin/README.md")
if "_goc-bootstrap.sh" in codex_readme:
    ok(f"codex-plugin/README.md:{line_of(codex_readme, '_goc-bootstrap.sh')} sends plugin users "
       f"to the bundled helper; pipx 'only when using vendored Codex skills without the plugin payload'")
print()

# --- 3. Surfaces that predate the plugin (2026-05-18) -------------------------
site = read("site/index.html")
m = re.search(r'<h2 id="install">Install paths</h2>(.*?)<h2 ', site, re.S)
install_html = m.group(1) if m else ""
install_text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", install_html)).split())
count = re.search(r"ships through (\w+) first-class delivery channels", install_text)
want = NUMBER_WORDS.get(len(channels))
if "Codex" not in install_text or (count and count.group(1) != want):
    said = count.group(1) if count else "(no count)"
    fail(f"site/index.html:{line_of(site, 'first-class delivery channels')} (game-of-cards.com "
         f"home page): says {said!r} channels, lists {install_html.count('<li>')} bullets, "
         f"names Codex: {'Codex' in install_text}  (tree ships {want})")
else:
    ok("site/index.html names the Codex plugin")

personas = read("PERSONAS.md")
rc = re.search(r"^- \*\*Runtime channel\.\*\*(.*)$", personas, re.M)
if rc and "Codex" not in rc.group(1):
    fail(f"PERSONAS.md:{line_of(personas, '**Runtime channel.**')} 'Runtime channel' lists "
         f"Claude Code, OpenClaw and the generic CLI; no Codex")

helptext = " ".join(subprocess.run(
    [sys.executable, "-m", "goc.cli", "install", "--help"],
    cwd=ROOT, capture_output=True, text=True, check=False,
).stdout.split())
hm = re.search(r"Default for Codex \(no plugin yet\)[^.]*\.", helptext)
if codex_ships and hm:
    fail(f"`goc install --help`, --local-skills: {hm.group(0)!r}")

doc = " ".join((goc_install._should_use_local_skills.__doc__ or "").split())
if codex_ships and "no plugin yet" in doc:
    src = read("goc/install.py")
    fail(f"goc/install.py:{line_of(src, 'Codex always uses vendored layout')} "
         f"_should_use_local_skills docstring: 'Codex always uses vendored layout (no plugin yet).'")
always = goc_install._should_use_local_skills("codex", local_skills=False)
print(f"info: _should_use_local_skills('codex', local_skills=False) -> {always}: Codex is vendored "
      f"on every install, so 'Default for Codex' names a default with no opt-out")

kickoff = read("goc/templates/skills/kickoff/SKILL.md")
km = re.search(r"If the host has its own kickoff complement.*?\)", kickoff, re.S)
if (ROOT / "goc/templates/skills/codex-kickoff").is_dir() and km and "codex-kickoff" not in km.group(0):
    fail(f"goc/templates/skills/kickoff/SKILL.md:{line_of(kickoff, 'If the host has its own kickoff')} "
         f"complement example names claude-kickoff and OpenClaw's, not codex-kickoff: "
         f"{' '.join(km.group(0).split())!r}")
print()

# --- 4. Surfaces that predate the bundled-engine helper (2026-06-09) ----------
gocmd = read("goc.md")
codex_md = md_section(gocmd, "## Codex plugin")
if helper.is_file() and "_goc-bootstrap.sh" not in codex_md:
    stale = "skill instructions still assume `goc` is callable"
    fail(f"goc.md:{line_of(gocmd, stale)} § Codex plugin never names _goc-bootstrap.sh; it says "
         f"{stale!r} ({len(resolver_skills)}/{len(codex_skills)} skills carry a resolver) and sends "
         f"plugin users to `pipx install game-of-cards`")
llms_codex = md_section(llms, "## Install (Codex)")
if helper.is_file() and "_goc-bootstrap.sh" not in llms_codex:
    fail(f"site/llms.txt:{line_of(llms, 'If bare')} § Install (Codex) never names _goc-bootstrap.sh; "
         f"tells plugin users: 'If bare `goc` is not available in a consumer repo, install the CLI "
         f"with `pipx install game-of-cards`'")
print()

# --- 5. The follow-up that was due when the plugin shipped (process, info) ----
deck = ROOT / ".game-of-cards" / "deck"
pub = (deck / "publish-codex-plugin" / "README.md").read_text(encoding="utf-8")
pub_status = re.search(r"^status: (\S+)", pub, re.M).group(1)
pub_closed = re.search(r"^closed_at: (\S+)", pub, re.M).group(1).strip('"')
print(f"info: publish-codex-plugin status={pub_status} closed_at={pub_closed}")
print("info: claude-install-defaults-to-plugin-path promised a `codex-install-defaults-to-plugin-path` "
      f"follow-up for that moment; card dir exists: "
      f"{(deck / 'codex-install-defaults-to-plugin-path').is_dir()}")

print()
if failures:
    print(f"RESULT: {len(failures)} stale Codex claim(s)")
    sys.exit(1)
print("RESULT: every surface agrees with the shipped Codex plugin")
