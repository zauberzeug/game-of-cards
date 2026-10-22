"""Regression guard: a shipped `goc advance` example must build the edge its
own prose claims.

`goc advance <title> --by <advancer>` writes `advancer.advances += title`, so a
skill body that states an encoding (``child.advances: [epic]``) and then hands
the reader a verb form is making a claim no derive-from-tree check can see: the
text is internally consistent English either way, and only *running* it reveals
which direction it builds. The aggregation-epic recipe shipped the swapped form
in all six skill trees until
`shipped-epic-recipe-builds-the-backwards-edge-its-own-next-bullet-forbids`
— every consumer following it built the `BACKWARDS_EPIC_EDGE` shape the same
bullet forbids nine lines down.

So this walks every `goc advance A --by B` occurrence in every shipped skill
body, pairs it with the encoding claim stated in the same block, and executes
it against a scratch deck. Examples written with generic placeholders
(`<title> --by <other>`) carry no role-named claim to compare against and are
reported as uncovered rather than silently dropped; the vacuity check below
fails if the covered set ever empties.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402

# Every tree that ships a skill body to a reader: the templates plus the two
# dogfood mirrors and the three plugin payloads. Derived by globbing rather
# than enumerated so a seventh consumer is covered on the day it lands.
_SKILL_ROOTS = (
    ROOT / "goc" / "templates" / "skills",
    ROOT / ".claude" / "skills",
    ROOT / ".codex" / "skills",
    ROOT / "claude-plugin" / "skills",
    ROOT / "codex-plugin" / "skills",
    ROOT / "openclaw-plugin" / "skills",
)

# `goc advance <a> --by <b>`, with the angle brackets optional so prose forms
# (`goc advance X --by Y`) are caught too. Run against whitespace-collapsed
# block text, so a line-wrapped example still matches.
_ADVANCE_EXAMPLE = re.compile(r"goc advance +<?([A-Za-z][\w-]*)>? +--by +<?([A-Za-z][\w-]*)>?")

# An encoding claim: `<role>.advances: [<role>]` / `<role>.advanced_by: [<role>]`.
_ENCODING_CLAIM = re.compile(r"`([A-Za-z][\w-]*)\.(advances|advanced_by): \[([A-Za-z][\w-]*)\]`")

_BULLET = re.compile(r"^ *(?:[-*+]|\d+\.) ")

# Plurals the skill bodies actually use for a role ("children" for the child
# side of an epic). Roles are English words chosen by the author, so the
# mapping is a convention, not a derivation.
_IRREGULAR_SINGULARS = {"children": "child"}


class Example(NamedTuple):
    """One `goc advance` example and the edge direction its block claims."""

    title_arg: str      # the positional the example passes
    advancer_arg: str   # the `--by` argument
    owner: str          # role whose field the claim describes
    field: str          # "advances" | "advanced_by"
    target: str         # role the claim says that field holds
    source: str         # "<path>:<line>" of the block the pair was read from

    @property
    def key(self) -> tuple[str, str, str, str, str]:
        """Identity of the *claim*, ignoring which tree it was read from."""
        return (self.title_arg, self.advancer_arg, self.owner, self.field, self.target)


def _blocks(lines: list[str]) -> list[tuple[int, str]]:
    """Split markdown into (1-indexed start line, whitespace-collapsed text).

    A block is one list item or one paragraph — narrower than a paragraph-only
    split, which would pool the aggregation-epic bullet together with the
    "Backwards aggregation — `epic.advances: [children]`. **Never.**" bullet
    six lines below it and read the forbidden shape as the claim.
    """
    out: list[tuple[int, str]] = []
    start = 0
    cur: list[str] = []

    def flush() -> None:
        nonlocal cur
        if cur:
            out.append((start, re.sub(r"\s+", " ", " ".join(cur)).strip()))
            cur = []

    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            flush()
            continue
        if _BULLET.match(line) and cur:
            flush()
        if not cur:
            start = lineno
        cur.append(line)
    flush()
    return out


def _singular(word: str, known: set[str]) -> str | None:
    """Normalize a claim's role word onto one of the example's arguments."""
    if word in known:
        return word
    irregular = _IRREGULAR_SINGULARS.get(word)
    if irregular in known:
        return irregular
    if word.endswith("s") and word[:-1] in known:
        return word[:-1]
    return None


def _examples_in(text: str, source: str) -> tuple[list[Example], list[str]]:
    """Return (claimed examples, uncovered `<path>:<line>` example sites)."""
    claimed: list[Example] = []
    uncovered: list[str] = []
    for lineno, block in _blocks(text.splitlines()):
        found = _ADVANCE_EXAMPLE.findall(block)
        if not found:
            continue
        for title_arg, advancer_arg in found:
            roles = {title_arg, advancer_arg}
            pairs = [
                (owner, field, target)
                for raw_owner, field, raw_target in _ENCODING_CLAIM.findall(block)
                for owner in [_singular(raw_owner, roles)]
                for target in [_singular(raw_target, roles)]
                if owner and target and owner != target
            ]
            if len(pairs) == 1:
                owner, field, target = pairs[0]
                claimed.append(Example(title_arg, advancer_arg, owner, field, target, f"{source}:{lineno}"))
            else:
                uncovered.append(f"{source}:{lineno}")
    return claimed, uncovered


def _scan() -> tuple[dict[tuple[str, str, str, str, str], list[Example]], list[str]]:
    """Read every shipped skill body once, grouping claims across the mirrors."""
    claims: dict[tuple[str, str, str, str, str], list[Example]] = {}
    uncovered: list[str] = []
    for root in _SKILL_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            found, missing = _examples_in(
                path.read_text(encoding="utf-8"), str(path.relative_to(ROOT))
            )
            for example in found:
                claims.setdefault(example.key, []).append(example)
            uncovered.extend(missing)
    return claims, uncovered


def _run_goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )


def _execute(example: Example) -> str | None:
    """Run the example on a scratch deck; return a failure message, or None."""
    slugs = {role: f"scratch-{role}-card" for role in (example.title_arg, example.advancer_arg)}
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / ".game-of-cards" / "deck").mkdir(parents=True)
        for slug in sorted(slugs.values()):
            created = _run_goc(cwd, "new", slug, "--gate", "none", "--tag", "story")
            if created.returncode != 0:
                return f"could not scaffold {slug}: {created.stdout}{created.stderr}"
        advanced = _run_goc(cwd, "advance", slugs[example.title_arg], "--by", slugs[example.advancer_arg])
        if advanced.returncode != 0:
            return f"the example itself failed: {advanced.stdout}{advanced.stderr}"
        owner_slug = slugs.get(example.owner)
        if owner_slug is None:  # unreachable: _singular already constrained the roles
            return f"claim names {example.owner!r}, which the example never passes"
        card, _ = engine.parse_frontmatter(
            (cwd / ".game-of-cards" / "deck" / owner_slug / "README.md").read_text(encoding="utf-8")
        )
        built = card.get(example.field) or []
        if slugs[example.target] in built:
            return None
        other = "advanced_by" if example.field == "advances" else "advances"
        return (
            f"claims `{example.owner}.{example.field}: [{example.target}]` but "
            f"`goc advance {example.title_arg} --by {example.advancer_arg}` builds "
            f"`{example.owner}.{example.field}: {[s for s in built]}` "
            f"(and `{example.owner}.{other}: {card.get(other) or []}`) — "
            f"swap the example's arguments to `goc advance {example.advancer_arg} "
            f"--by {example.title_arg}`"
        )


class SkillAdvanceExampleDirectionTest(unittest.TestCase):
    def test_every_claimed_advance_example_builds_the_claimed_edge(self) -> None:
        claims, _ = _scan()
        failures = []
        for key, sites in sorted(claims.items()):
            problem = _execute(sites[0])
            if problem:
                where = ", ".join(sorted({s.source for s in sites}))
                failures.append(f"{where}\n    {problem}")
        self.assertEqual(
            [], failures,
            msg="a shipped `goc advance` example builds the opposite edge from the "
                "one its own block states:\n\n" + "\n\n".join(failures),
        )

    def test_the_covered_set_is_not_empty(self) -> None:
        claims, uncovered = _scan()
        self.assertTrue(
            claims,
            msg="no shipped `goc advance` example is paired with an encoding claim, "
                "so the direction check above ran against nothing. Either a block "
                f"lost its `<role>.advances: [<role>]` wording (example sites seen "
                f"but not covered: {sorted(set(uncovered))}) or the block splitter "
                "stopped matching — re-derive it rather than deleting this test.",
        )

    def test_the_guard_fires_on_the_wording_the_card_found(self) -> None:
        """Feed the pre-fix bullet through the guard; it must reject it.

        A static guard that never demonstrates catching its offender is pinning
        nothing — the swapped line read as valid English for as long as it
        shipped.
        """
        historical = (
            "- **Aggregation epic** - its value chain *is* its children; closes\n"
            "  when they close. Encoding: `child.advances: [epic]`. Verb on the\n"
            "  child: `goc advance <child> --by <epic>`.\n"
        )
        found, _ = _examples_in(historical, "fixture")
        self.assertEqual(
            1, len(found),
            msg=f"the guard read no claim out of the pre-fix bullet: {found}",
        )
        self.assertIsNotNone(
            _execute(found[0]),
            msg="fed the pre-fix aggregation-epic bullet verbatim, the guard "
                "accepted it. It is pinning nothing — re-derive it rather than "
                "deleting this fixture.",
        )


if __name__ == "__main__":
    unittest.main()
