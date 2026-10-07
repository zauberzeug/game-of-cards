"""Every surface that enumerates GoC's delivery channels names each one the tree ships.

`codex-install-guidance-predates-the-codex-plugin-and-its-bundled-engine`:
the Codex plugin shipped on 2026-05-18 and gained a bundled `goc` helper
(`skills/_goc-bootstrap.sh`) on 2026-06-09. Each commit updated the surfaces
its author had open, so for twenty weeks the game-of-cards.com home page and
`PERSONAS.md` listed three channels without Codex, `goc install --help` said
Codex had "no plugin yet", and `goc.md` / `site/llms.txt` sent plugin users
to `pipx install game-of-cards` for a CLI the plugin already bundles.

Nothing here restates the channel set. It is derived from the tree: one
channel per plugin payload manifest that exists, plus the PyPI package
(`pyproject.toml`) as the Generic CLI. The count word each surface must state
is computed from that set, so shipping a fifth payload turns this red until
every enumerating surface names it.

Detection is precision-first, in the posture of
`tests/test_llms_txt_install_channels.py`: the "no plugin" and
"assume `goc` is callable" markers are claims about what ships, not style. A
stale claim spelled some other way still slips through. This guards the
project's own docs, not goc semantics, so it lives in `tests/`.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Host name -> the manifest whose presence means that host's plugin ships.
PLUGIN_MANIFESTS = {
    "Claude Code": Path("claude-plugin/.claude-plugin/plugin.json"),
    "Codex": Path("codex-plugin/.codex-plugin/plugin.json"),
    "OpenClaw": Path("openclaw-plugin/openclaw.plugin.json"),
}
GENERIC_CLI = "Generic CLI"
CODEX_BOOTSTRAP = Path("codex-plugin/skills/_goc-bootstrap.sh")
NUMBER_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}

# Docs and help strings scanned for a shipped host paired with "no plugin".
NO_PLUGIN_SCAN_GLOBS = (
    "*.md",
    "site/*.html",
    "site/*.txt",
    "goc/*.py",
    "goc/templates/skills/**/*.md",
    "claude-plugin/README.md",
    "codex-plugin/README.md",
    "openclaw-plugin/README.md",
)
NO_PLUGIN = re.compile(r"\bno plugin\b(?!-)", re.IGNORECASE)
COUNT_CLAIM = re.compile(r"\b(\w+) first-class delivery channels|\bAll (\w+) drive\b")


def shipped_plugin_hosts(root: Path = ROOT) -> list[str]:
    return [host for host, manifest in PLUGIN_MANIFESTS.items() if (root / manifest).is_file()]


def channel_set(root: Path = ROOT) -> list[str]:
    channels = [f"{host} plugin" for host in shipped_plugin_hosts(root)]
    # tomllib is 3.11+; CI covers 3.10, and the one key needed sits on its own line.
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    if re.search(r'^name = "game-of-cards"$', pyproject, flags=re.MULTILINE):
        channels.append(GENERIC_CLI)
    return channels


def section(text: str, start: str, stop: str) -> str:
    """Text from the line holding `start` up to the next line starting with `stop`."""
    begin = text.index(start)
    end = text.find(stop, begin + len(start))
    return text[begin:] if end == -1 else text[begin:end]


def channel_list_problems(name: str, text: str, channels: list[str]) -> list[str]:
    """A surface that enumerates channels must state the count and name each one."""
    problems = []
    expected = NUMBER_WORDS[len(channels)]
    claims = [word for match in COUNT_CLAIM.finditer(text) for word in match.groups() if word]
    if not claims:
        problems.append(f"{name}: states no channel count (tree ships {expected})")
    problems += [
        f"{name}: says '{word}' channels, tree ships {expected}" for word in claims if word.lower() != expected
    ]
    problems += [f"{name}: never names the {channel}" for channel in channels if channel.lower() not in text.lower()]
    return problems


def runtime_channel_problems(text: str, hosts: list[str]) -> list[str]:
    bullet = next((line for line in text.splitlines() if "**Runtime channel.**" in line), "")
    if not bullet:
        return ["PERSONAS.md: no 'Runtime channel' bullet"]
    problems = [f"PERSONAS.md Runtime channel: never names {host}" for host in hosts if host not in bullet]
    if "PyPI" not in bullet:
        problems.append("PERSONAS.md Runtime channel: never names the generic CLI from PyPI")
    return problems


def llms_install_heading_problems(text: str, hosts: list[str], channels: list[str]) -> list[str]:
    headings = re.findall(r"^## Install \((.+)\)$", text, flags=re.MULTILINE)
    problems = [f"site/llms.txt: no '## Install ({host})' section" for host in hosts if host not in headings]
    if len(headings) != len(channels):
        problems.append(f"site/llms.txt: {len(headings)} '## Install (…)' sections, tree ships {len(channels)} channels")
    return problems


def no_plugin_problems(name: str, text: str, hosts: list[str]) -> list[str]:
    """A line that names a shipped host must not also say it has no plugin."""
    return [
        f"{name}:{lineno}: pairs {host} with 'no plugin': {line.strip()}"
        for lineno, line in enumerate(text.splitlines(), 1)
        if NO_PLUGIN.search(line)
        for host in hosts
        if re.search(rf"\b{re.escape(host)}\b", line)
    ]


def codex_cli_problems(name: str, text: str) -> list[str]:
    """A section telling a Codex plugin user how to run goc names the bundled helper."""
    problems = []
    if CODEX_BOOTSTRAP.name not in text:
        problems.append(f"{name}: never names {CODEX_BOOTSTRAP.name}, the helper the Codex plugin ships")
    if "assume `goc` is callable" in text:
        problems.append(f"{name}: says skill instructions assume `goc` is callable; every Codex skill carries a resolver")
    if "pipx install" in text and "without the plugin" not in text:
        problems.append(f"{name}: offers pipx without scoping it to vendored skills without the plugin payload")
    return problems


def read(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8")


class DeliveryChannelSurfacesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.hosts = shipped_plugin_hosts()
        self.channels = channel_set()

    def test_tree_ships_the_channels_this_guard_derives(self) -> None:
        # Sanity: the derivation sees the payloads, so an empty set cannot pass vacuously.
        self.assertIn("Codex plugin", self.channels)
        self.assertIn(GENERIC_CLI, self.channels)

    def test_channel_lists_state_the_count_and_name_every_channel(self) -> None:
        readme = section(read("README.md"), "## Install paths", "\n## ")
        index = section(read("site/index.html"), '<h2 id="install">', "<h2")
        problems = channel_list_problems("README.md § Install paths", readme, self.channels)
        problems += channel_list_problems("site/index.html #install", index, self.channels)
        problems += runtime_channel_problems(read("PERSONAS.md"), self.hosts)
        problems += llms_install_heading_problems(read("site/llms.txt"), self.hosts, self.channels)
        self.assertEqual(problems, [])

    def test_no_doc_or_help_string_says_a_shipped_host_has_no_plugin(self) -> None:
        problems = []
        for pattern in NO_PLUGIN_SCAN_GLOBS:
            for path in sorted(ROOT.glob(pattern)):
                rel = path.relative_to(ROOT).as_posix()
                problems += no_plugin_problems(rel, path.read_text(encoding="utf-8"), self.hosts)
        self.assertEqual(problems, [])

    def test_codex_run_goc_sections_name_the_bundled_helper(self) -> None:
        if not (ROOT / CODEX_BOOTSTRAP).is_file():
            self.skipTest("codex-plugin ships no bootstrap helper")
        problems = codex_cli_problems("goc.md § Codex plugin", section(read("goc.md"), "## Codex plugin", "\n## "))
        problems += codex_cli_problems(
            "site/llms.txt § Install (Codex)", section(read("site/llms.txt"), "## Install (Codex)", "\n## ")
        )
        problems += codex_cli_problems("codex-plugin/README.md", read("codex-plugin/README.md"))
        self.assertEqual(problems, [])


class PreFixTextFiresTest(unittest.TestCase):
    """Fed the text each surface carried before the fix, every check fires."""

    HOSTS = ["Claude Code", "Codex", "OpenClaw"]
    CHANNELS = ["Claude Code plugin", "Codex plugin", "OpenClaw plugin", GENERIC_CLI]

    def test_three_channel_home_page_fires(self) -> None:
        pre_fix = (
            "GoC ships through three first-class delivery channels. All three drive the same engine\n"
            "<strong>Claude Code plugin.</strong> <strong>OpenClaw plugin.</strong> <strong>Generic CLI</strong>"
        )
        problems = channel_list_problems("site/index.html", pre_fix, self.CHANNELS)
        self.assertIn("site/index.html: says 'three' channels, tree ships four", problems)
        self.assertIn("site/index.html: never names the Codex plugin", problems)

    def test_runtime_channel_without_codex_fires(self) -> None:
        pre_fix = (
            "- **Runtime channel.** Claude Code (via plugin or pipx), [OpenClaw](https://openclaw.ai) "
            "(via ClawHub plugin), or the generic `goc` CLI from PyPI for any other agent runtime."
        )
        self.assertEqual(
            runtime_channel_problems(pre_fix, self.HOSTS), ["PERSONAS.md Runtime channel: never names Codex"]
        )

    def test_missing_llms_install_section_fires(self) -> None:
        pre_fix = "## Install (Claude Code)\n## Install (OpenClaw)\n## Install (other agent runtimes / CI)\n"
        problems = llms_install_heading_problems(pre_fix, self.HOSTS, self.CHANNELS)
        self.assertIn("site/llms.txt: no '## Install (Codex)' section", problems)

    def test_no_plugin_yet_help_and_docstring_fire(self) -> None:
        for pre_fix in (
            '    "Default for Codex (no plugin yet); opt-in for Claude. "',
            "    Codex always uses vendored layout (no plugin yet).",
        ):
            with self.subTest(pre_fix=pre_fix):
                self.assertEqual(len(no_plugin_problems("goc/install.py", pre_fix, self.HOSTS)), 1)
        # "plugin-side" is not a claim about what ships.
        self.assertEqual(no_plugin_problems("x", "Codex path with no plugin-side change.", self.HOSTS), [])

    def test_pipx_only_codex_cli_paragraph_fires(self) -> None:
        pre_fix = (
            "Codex does not currently document plugin `bin/` auto-PATH behavior. The plugin ships `bin/goc` "
            "and the bundled engine for plugin-aware launchers, but skill instructions still assume `goc` is "
            "callable in the project environment. In this source repo, use `uv run goc ...`; in consumer "
            "repos, install the CLI with `pipx install game-of-cards` or `uv tool install game-of-cards` if "
            "bare `goc` is missing."
        )
        self.assertEqual(len(codex_cli_problems("goc.md", pre_fix)), 3)


if __name__ == "__main__":
    unittest.main()
