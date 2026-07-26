"""Closure verbs write `closed_at` in the same canonical form the emitter would.

`mutate_frontmatter_field` is a raw line-substitution and does not apply YAML
quoting; the closure verbs (`goc done`, `goc done --bundle`,
`goc status X disproved|superseded`) therefore have to wrap their datetime
value in `_yaml_inline` so that the on-disk line is byte-identical to what
`emit_frontmatter` would produce on the next whole-frontmatter rewrite.
Without that wrap, every `goc decide` / `goc migrate-list-style` /
emitter-routed migration silently rewrites the `closed_at` line on every
closed card it touches, inflating diffs and hiding real changes.

`ClosedAtWriterContractTest` guards the same contract *statically* over every
`closed_at` writer in the tree, not just the four verbs exercised above. The
behavioural tests only cover the writers someone thought to enumerate, which is
how `scripts/backfill_terminal_closed_at.py` kept writing the bare form for two
months after the drift was declared fixed — see card
`backfill-script-reintroduces-bare-closed-at-the-migration-removed`.
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
sys.path.insert(0, str(ROOT))

from goc.engine import emit_frontmatter, parse_frontmatter  # noqa: E402


def _closed_at_line(readme: Path) -> str:
    for line in readme.read_text().splitlines():
        if line.startswith("closed_at:"):
            return line
    raise AssertionError(f"no closed_at line in {readme}")


def _emitter_closed_at_line(readme: Path) -> str:
    """What `emit_frontmatter` would emit for this card's closed_at value."""
    fm, body = parse_frontmatter(readme.read_text())
    reemitted = emit_frontmatter(fm, body=body)
    for line in reemitted.splitlines():
        if line.startswith("closed_at:"):
            return line
    raise AssertionError(f"emit_frontmatter produced no closed_at line for {readme}")


class ClosedAtCanonicalFormTest(unittest.TestCase):
    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_card(self, cwd: Path, title: str, *, status: str = "active") -> Path:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            f"status: {status}\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-05-01\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [x] item\n"
            "---\n\n"
            f"# {title}\n"
        )
        (card_dir / "log.md").write_text("")
        return card_dir

    def test_done_writes_closed_at_matching_emitter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            card = self.write_card(cwd, "card-a")
            result = self.run_goc(cwd, "done", "card-a")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            readme = card / "README.md"
            self.assertEqual(_closed_at_line(readme), _emitter_closed_at_line(readme))

    def test_done_bundle_writes_closed_at_matching_emitter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            card_a = self.write_card(cwd, "card-a")
            card_b = self.write_card(cwd, "card-b")
            result = self.run_goc(cwd, "done", "--bundle", "card-a", "card-b")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            for card in (card_a, card_b):
                readme = card / "README.md"
                self.assertEqual(_closed_at_line(readme), _emitter_closed_at_line(readme))

    def test_status_disproved_writes_closed_at_matching_emitter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            card = self.write_card(cwd, "card-a", status="open")
            result = self.run_goc(cwd, "status", "card-a", "disproved")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            readme = card / "README.md"
            self.assertEqual(_closed_at_line(readme), _emitter_closed_at_line(readme))

    def test_status_superseded_writes_closed_at_matching_emitter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            old = self.write_card(cwd, "old-card", status="open")
            self.write_card(cwd, "new-card", status="open")
            result = self.run_goc(
                cwd, "status", "old-card", "superseded", "--by", "new-card"
            )
            self.assertEqual(0, result.returncode, msg=result.stderr)
            readme = old / "README.md"
            self.assertEqual(_closed_at_line(readme), _emitter_closed_at_line(readme))


# Matches `mutate_frontmatter_field(<target>, "closed_at", <value>)`, capturing
# the value expression. The value alternation tolerates one level of nested call
# parens so `_yaml_inline(_utc_now_iso())` is captured whole.
_CLOSED_AT_WRITE_RE = re.compile(
    r'mutate_frontmatter_field\(\s*[^,]+,\s*"closed_at"\s*,\s*'
    r"(?P<value>(?:[^()]|\((?:[^()]|\([^()]*\))*\))+?)\s*\)"
)

# Trees scanned for `closed_at` writers. The plugin payloads
# (`claude-plugin/goc/`, `codex-plugin/goc/`, `openclaw-plugin/goc/`) are
# deliberately excluded: they are byte-for-byte mirrors of `goc/`, enforced by
# `tests/test_plugin_mirror_parity.py`, so scanning them would only re-report
# the same call sites under four names.
_WRITER_TREES = ("goc", "scripts")

# Files that must each contribute at least one writer. Without this floor the
# test would pass vacuously if `_CLOSED_AT_WRITE_RE` ever stopped matching —
# the exact failure mode that lets a "we swept every call site" claim rot.
_EXPECTED_WRITER_FILES = (
    Path("goc") / "engine.py",
    Path("scripts") / "backfill_terminal_closed_at.py",
)


class ClosedAtWriterContractTest(unittest.TestCase):
    """Every `closed_at` writer in the tree must route its value through `_yaml_inline`.

    Scoped to `closed_at` rather than "any colon-bearing value" because the
    general form is not statically decidable: `mutate_frontmatter_field(text,
    "status", new_status)` passes a variable whose colon-freeness follows from
    an argparse `choices` enum, and `"worker", worker_yaml` passes a value that
    was already run through `_yaml_inline` one frame up. Widening the rule would
    need a per-callsite allowlist, which drifts the same way the manual sweep
    did. `closed_at` is the field whose value is *always* a colon-bearing
    timestamp, so for it the rule is exact.
    """

    def _writers(self) -> list[tuple[Path, int, str]]:
        found: list[tuple[Path, int, str]] = []
        for tree in _WRITER_TREES:
            for path in sorted((ROOT / tree).rglob("*.py")):
                for lineno, line in enumerate(path.read_text().splitlines(), 1):
                    m = _CLOSED_AT_WRITE_RE.search(line)
                    if m:
                        rel = path.relative_to(ROOT)
                        found.append((rel, lineno, m.group("value").strip()))
        return found

    def test_scan_finds_the_known_writer_files(self) -> None:
        writers = self._writers()
        seen = {rel for rel, _, _ in writers}
        for expected in _EXPECTED_WRITER_FILES:
            self.assertIn(
                expected,
                seen,
                msg=(
                    f"no `mutate_frontmatter_field(..., \"closed_at\", ...)` call found "
                    f"in {expected}. Either the writer moved (update "
                    f"_EXPECTED_WRITER_FILES) or _CLOSED_AT_WRITE_RE stopped matching "
                    f"— in the latter case this whole test is passing vacuously."
                ),
            )

    def test_every_closed_at_writer_routes_through_yaml_inline(self) -> None:
        offenders = [
            f"{rel}:{lineno} passes `{value}`"
            for rel, lineno, value in self._writers()
            if "_yaml_inline" not in value
        ]
        self.assertEqual(
            [],
            offenders,
            msg=(
                "closed_at must be wrapped in `_yaml_inline` before reaching "
                "`mutate_frontmatter_field`, which inserts the value verbatim. "
                "The bare form parses fine but differs from what "
                "`emit_frontmatter` writes, so the next whole-frontmatter "
                "rewrite re-quotes a card nobody edited:\n  "
                + "\n  ".join(offenders)
            ),
        )


if __name__ == "__main__":
    unittest.main()
