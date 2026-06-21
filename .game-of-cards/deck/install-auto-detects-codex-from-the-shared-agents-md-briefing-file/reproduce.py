"""Reproduce: `goc install` auto-detection treats the shared AGENTS.md briefing
as a Codex-exclusive marker (and `.mcp.json` as a Claude-exclusive marker), so a
Claude-only repo whose CLAUDE.md imports an AGENTS.md briefing is detected as
having Codex too — and a bare `goc install` would scaffold the Codex harness the
user never asked for.

Run: uv run python .game-of-cards/deck/install-auto-detects-codex-from-the-shared-agents-md-briefing-file/reproduce.py
Exits 0 when the defect fires (over-detection observed); exits 1 once fixed.
"""

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


sys.path.insert(0, str(_repo_root()))

from goc import install  # noqa: E402


def main() -> int:
    failures = []

    # Case A: a Claude repo whose CLAUDE.md imports the AGENTS.md briefing.
    # AGENTS.md is the *generic cross-agent* briefing file (it is GoC's default
    # briefing target), NOT a Codex-exclusive marker.
    with tempfile.TemporaryDirectory() as d:
        t = Path(d)
        (t / "CLAUDE.md").write_text("@AGENTS.md\n")
        (t / "AGENTS.md").write_text("# Agent Guidelines\n")
        (t / ".claude").mkdir()
        detected = install._detect_agent_surfaces(t)
        print(f"Case A (CLAUDE.md + AGENTS.md + .claude): detected = {detected}")
        if "codex" in detected:
            failures.append(
                "Case A: 'codex' auto-detected from the shared AGENTS.md briefing "
                "in a Claude-only repo — a bare `goc install` would scaffold the "
                "Codex harness unbidden."
            )

    # Case B: a Codex repo that uses MCP servers. `.mcp.json` is the Model Context
    # Protocol config — cross-agent, NOT a Claude-exclusive marker.
    with tempfile.TemporaryDirectory() as d:
        t = Path(d)
        (t / "AGENTS.md").write_text("# Agent Guidelines\n")
        (t / ".codex").mkdir()
        (t / ".mcp.json").write_text("{}\n")
        detected = install._detect_agent_surfaces(t)
        print(f"Case B (AGENTS.md + .codex + .mcp.json): detected = {detected}")
        if "claude" in detected:
            failures.append(
                "Case B: 'claude' auto-detected from the cross-agent .mcp.json in a "
                "Codex repo — a bare `goc install` would scaffold the Claude harness "
                "unbidden."
            )

    print()
    print("AGENT_SIGNAL_PATHS =", {k: [str(p) for p in v] for k, v in install.AGENT_SIGNAL_PATHS.items()})
    print()

    if failures:
        print("DEFECT REPRODUCED:")
        for f in failures:
            print("  -", f)
        return 0
    print("No over-detection observed — defect appears fixed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
