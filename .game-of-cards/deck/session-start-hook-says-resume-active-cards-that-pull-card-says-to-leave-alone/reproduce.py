#!/usr/bin/env python3
"""The SessionStart reminder and the pull-card / next-card skills give
opposite instructions about the same active card, and nothing on the card
lets an agent tell which one applies.

1. Builds two throwaway decks, each holding one `status: active`,
   `human_gate: none` card with no wait:
   - LIVE: just claimed by another worker on a feature branch. This is the
     parallel session the soft lock exists to protect.
   - ORPHANED: claimed by this worker on main a day ago by a session that
     then died. This repo's own autonomous runs keep hitting that case.
   Each deck is fed to the shipped `deck_session_start.py` the way Claude
   Code invokes it (hook JSON on stdin), and the script prints what the
   hook tells the new session.
2. Prints what the shipped `pull-card` and `next-card` skills tell the same
   session about the same card.
3. Shows that nothing on the card separates the two cases: a real
   `goc status <title> active` writes `worker: {who, where}` and no time,
   and none of the surfaces that speak about the soft lock says when a
   claim counts as orphaned.

Exits 1 while, for either deck, one surface says "resume" and the other
says "leave it alone". Exits 0 once they agree on both decks: either the
hook stops telling a session to resume a claim the skills protect, or the
skills say when a claim may be resumed.
"""

import json
import os
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
HOOK = ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py"
SKILLS = {
    "pull-card": ROOT / "goc" / "templates" / "skills" / "pull-card" / "SKILL.md",
    "next-card": ROOT / "goc" / "templates" / "skills" / "next-card" / "SKILL.md",
}
# Every shipped surface that speaks about the soft lock or active claims.
SOFT_LOCK_SURFACES = [
    *SKILLS.values(),
    ROOT / "goc" / "templates" / "skills" / "deck" / "SKILL.md",
    ROOT / "goc" / "templates" / "skills" / "deck" / "reference.md",
    ROOT / "goc" / "templates" / "skills" / "advance-card" / "SKILL.md",
    HOOK,
]
ORPHAN_RULE = re.compile(
    r"orphan\w*|abandon\w*|dead (?:session|claim|run)|interrupted (?:session|run|claim)"
    r"|stale (?:claim|soft[- ]lock|active card)|claim\w* (?:is|was|counts as) (?:stale|orphan)",
    re.IGNORECASE,
)
HOOK_RESUME = "resume or close before starting new work"
HOOK_LEAVE = "agent cannot resume"
SKILL_LEAVE = "unless the user explicitly asks to continue that active card"

CARD = """---
title: {title}
summary: "A gate-free card somebody claimed."
status: active
stage: null
contribution: medium
created: "2026-10-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] TDD: a real criterion
worker: {worker}
---

# {title}

A real body.
"""

DECKS = {
    "LIVE": ("claimed-seconds-ago", '{who: other-agent, where: feature/parallel-work}'),
    "ORPHANED": ("claimed-by-a-dead-session", '{who: "claude[bot]", where: main}'),
}


def hook_instruction(title: str, worker: str) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        card = root / ".game-of-cards" / "deck" / title
        card.mkdir(parents=True)
        (card / "README.md").write_text(CARD.format(title=title, worker=worker))
        out = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"cwd": str(root), "hook_event_name": "SessionStart"}),
            text=True, capture_output=True, check=False,
        ).stdout.strip()
    line = next((ln for ln in out.splitlines() if title in ln), "")
    if HOOK_RESUME in line:
        return "resume", line
    if HOOK_LEAVE in line:
        return "leave", line
    return "other", line or "(silent)"


def skill_instruction() -> tuple[str, dict[str, str]]:
    """The soft-lock sentence(s) each skill gives, and whether they amount to
    an unconditional "leave it alone": the user-asks exception is the only
    one, and the skill defines no orphaned claim it could resume instead."""
    sentences = {}
    unconditional = True
    for name, path in SKILLS.items():
        text = path.read_text()
        flat = re.sub(r"\s+", " ", text)
        hit = re.search(
            r"(?:[A-Z][^.`]*soft lock[^.`]*\. )?[A-Z][^.`]*" + re.escape(SKILL_LEAVE) + r"\.", flat
        )
        sentences[name] = hit.group(0) if hit else "(no unconditional soft-lock rule)"
        if not hit or ORPHAN_RULE.search(text):
            unconditional = False
    return ("leave" if unconditional else "other"), sentences


def what_a_claim_records() -> list[str]:
    """Frontmatter lines a real `goc status <title> active` adds to an open card."""
    env = os.environ.copy()
    env.pop("GOC_WORKER", None)
    env["NO_COLOR"] = "1"
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        card = root / ".game-of-cards" / "deck" / "probe"
        card.mkdir(parents=True)
        readme = card / "README.md"
        unclaimed = CARD.format(title="probe", worker="null")
        unclaimed = unclaimed.replace("status: active", "status: open").replace("worker: null\n", "")
        readme.write_text(unclaimed)
        # The claim takes `who` from git's user.name and `where` from the branch.
        for cmd in (
            ["git", "init", "-q", "-b", "main"],
            ["git", "config", "user.name", "claude[bot]"],
            ["git", "config", "user.email", "bot@example.invalid"],
            ["git", "add", "-A"],
            ["git", "commit", "-q", "-m", "seed"],
        ):
            subprocess.run(cmd, cwd=root, check=True)
        before = set(readme.read_text().split("---")[1].strip().splitlines())
        subprocess.run(
            [sys.executable, "-m", "goc.cli", "status", "probe", "active", "--no-commit"],
            cwd=root, env=env, text=True, capture_output=True, check=True,
        )
        after = readme.read_text().split("---")[1].strip().splitlines()
    return [line for line in after if line not in before]


def main() -> int:
    skill_says, sentences = skill_instruction()
    print("=== what the shipped skills say about any active card ===")
    for name, sentence in sentences.items():
        print(f"  {name}: {sentence}")

    contradictions = []
    print("\n=== what the SessionStart hook says about the same card ===")
    for label, (title, worker) in DECKS.items():
        hook_says, line = hook_instruction(title, worker)
        print(f"  {label:8} worker={worker}")
        print(f"           hook: {line}")
        print(f"           hook says {hook_says!r}; skills say {skill_says!r}")
        if {hook_says, skill_says} == {"resume", "leave"}:
            contradictions.append(label)

    print("\n=== what could tell the two cases apart ===")
    added = what_a_claim_records()
    print("  frontmatter lines a real claim writes: " + "; ".join(added))
    has_time = any(re.search(r"\d{4}-\d{2}-\d{2}", line) for line in added)
    print(f"  claim records a time: {has_time}")
    rules = [
        f"{p.relative_to(ROOT)}: {m.group(0)!r}"
        for p in SOFT_LOCK_SURFACES
        for m in ORPHAN_RULE.finditer(p.read_text())
    ]
    print("  soft-lock surfaces that say when a claim is orphaned: " + (", ".join(rules) or "none"))

    print("\n=== verdict ===")
    if contradictions:
        print(
            f"DEFECT: for {len(contradictions)} of {len(DECKS)} decks ({', '.join(contradictions)}) "
            "the hook says resume and the skills say leave it alone, and nothing on the card "
            "separates a live claim from an orphaned one"
        )
        return 1
    print("OK: the hook and the skills agree on both decks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
