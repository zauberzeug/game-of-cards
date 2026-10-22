#!/usr/bin/env python3
"""Proof that `_yaml_inline`'s quote trigger has no strict-reader coercion term.

The emitter documents its trigger as the union of two oracles (engine.py, the
comment above the `if` in `_yaml_inline`): strict-YAML legality, plus the
vendored parser's reinterpretations. The strict half is implemented as three
*legality* predicates (`_YAML_NEEDS_QUOTE`, `_opens_with_yaml_indicator`,
`s != s.strip()`) and the parser half as `_parser_coerces_scalar`, derived from
`yaml_lite`'s own recognizers. Nothing asks the third question the union needs:
"would a standard YAML reader resolve this legal plain scalar to a non-string?"

Three checks, each exiting non-zero while the term is missing:

  A. emitter sweep    — scalars emitted bare that PyYAML resolves to non-str.
  B. worker path      — the reachability path: `goc status <card> active` on a
                        branch named `1.5` / `off`, end to end, no hand-editing.
  C. shipped deck     — `created` / `closed_at` values in this repo's own deck
                        that a strict reader types as `date` while the emitter's
                        own current output for the same field is a quoted string.

PyYAML is the reference strict reader. It is a dev-time import only: `goc`
itself has no third-party runtime dependency (see
`drop-third-party-runtime-dependencies-from-goc`), which is exactly why the
engine cannot answer this question by asking a real YAML parser at emit time.
"""

from __future__ import annotations

import datetime
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

from goc import engine  # noqa: E402
from goc._vendor import yaml_lite  # noqa: E402


def _reexec_under_a_strict_reader() -> None:
    """Re-run this script under an interpreter that has PyYAML.

    PyYAML is the oracle here, and it is deliberately absent from goc's runtime
    and from the project venv (`drop-third-party-runtime-dependencies-from-goc`)
    — which is the whole reason the emitter cannot just ask a real YAML parser
    at emit time. So `uv run python reproduce.py` lands in an interpreter that
    cannot answer the question. Hand off to one that can (the system `python3`
    usually carries PyYAML) rather than degrading to a hand-rolled resolver: a
    regex of our own would be one more copy of the enumeration this card is
    about.
    """
    import os
    import shutil

    if os.environ.get("_GOC_REPRO_REEXEC"):
        print("SKIP: no interpreter with PyYAML found; it is the strict reader here.")
        raise SystemExit(0)
    # Candidates are compared by *environment*, not by binary: a venv's
    # `python3` is usually a symlink to the same system binary, so an
    # `is this sys.executable?` check on the resolved path would discard the
    # very interpreter that carries PyYAML. The env is stripped of the venv
    # variables for the same reason, and `_GOC_REPRO_REEXEC` bounds recursion.
    base = {k: v for k, v in os.environ.items()
            if k not in ("VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH")}
    candidates = ["/usr/bin/python3", "/usr/local/bin/python3",
                  shutil.which("python3"), shutil.which("python")]
    for path in candidates:
        if not path or not Path(path).exists():
            continue
        if subprocess.run([path, "-c", "import yaml"], capture_output=True,
                          env=base).returncode != 0:
            continue
        env = {**base, "_GOC_REPRO_REEXEC": "1", "PYTHONPATH": str(ROOT)}
        raise SystemExit(subprocess.run([path, __file__], env=env).returncode)
    print("SKIP: no interpreter with PyYAML found; it is the strict reader here.")
    raise SystemExit(0)


try:
    import yaml as pyyaml  # noqa: E402
except ImportError:  # pragma: no cover - resolved by re-exec
    _reexec_under_a_strict_reader()


# Shapes chosen to span the three resolver families PyYAML has and yaml_lite
# does not: float, extended int (sign / leading zero / underscore / base
# prefix), and the YAML 1.1 on/off boolean pair.
CANDIDATES = [
    "1.5", "-2.0", "+3.5", "1.0e-5", ".5", ".inf", "-.inf", ".nan", ".INF",
    "+5", "007", "0x1F", "0b101", "1_000",
    "on", "off", "On", "Off", "ON", "OFF",
]


def check_emitter() -> list[tuple[str, str, str]]:
    """Return (value, emitted, strict-repr) for every bare-but-retyped scalar."""
    bad = []
    for v in CANDIDATES:
        emitted = engine._yaml_inline(v)
        if emitted.startswith('"'):
            continue  # quoted: the trigger caught it
        strict = pyyaml.safe_load(f"k: {emitted}")["k"]
        if not isinstance(strict, str):
            bad.append((v, emitted, f"{strict!r} ({type(strict).__name__})"))
    return bad


CARD = """---
title: {title}
summary: "Probe card."
status: open
stage: null
contribution: high
created: "2026-09-16T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: probe
---

Body.
"""


def check_worker_path(branch: str) -> tuple[str, object, object] | None:
    """Claim a card on `branch` through the real CLI; report a retyped `worker`.

    No hand-editing anywhere: `goc status <title> active` auto-populates
    `worker.where` from `git rev-parse --abbrev-ref HEAD`, which is the
    documented reachability path the closed sibling
    `frontmatter-emitter-does-not-quote-integer-looking-string-scalars`
    established for this field.
    """
    title = "probe-card"
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        run = lambda *a: subprocess.run(a, cwd=repo, capture_output=True, text=True)
        run("git", "init", "-q", ".")
        run("git", "config", "user.name", "probe-worker")
        run("git", "config", "user.email", "probe@example.invalid")
        run("git", "checkout", "-q", "-b", branch)
        card = repo / ".game-of-cards" / "deck" / title
        card.mkdir(parents=True)
        (card / "README.md").write_text(CARD.format(title=title), encoding="utf-8")
        (card / "log.md").write_text("", encoding="utf-8")
        # The branch must be born before `git rev-parse --abbrev-ref HEAD`
        # reports its name — on an unborn branch the engine's auto-populate
        # finds nothing and leaves `worker.where` unset.
        run("git", "add", "-A")
        run("git", "commit", "-qm", "probe")
        r = subprocess.run(
            [sys.executable, "-m", "goc.cli", "status", title, "active", "--no-commit"],
            cwd=repo, capture_output=True, text=True, env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
        )
        if r.returncode != 0:
            raise RuntimeError(f"goc status failed on branch {branch!r}: {r.stderr}")
        block = (card / "README.md").read_text(encoding="utf-8").split("---\n", 2)[1]
        line = next(l for l in block.splitlines() if l.startswith("worker:"))
        lite = yaml_lite.safe_load(block)["worker"]
        strict = pyyaml.safe_load(block)["worker"]
        if lite == strict:
            return None
        return (line, lite, strict)


def check_shipped_deck() -> tuple[int, int]:
    """Count deck cards whose `created`/`closed_at` a strict reader types as a
    date, against those the current emitter writes as a quoted string."""
    deck = ROOT / ".game-of-cards" / "deck"
    retyped = same = 0
    for readme in sorted(deck.glob("*/README.md")):
        text = readme.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        block = text.split("---\n", 2)[1]
        try:
            strict = pyyaml.safe_load(block)
        except Exception:
            continue
        lite = yaml_lite.safe_load(block)
        hit = False
        for key in ("created", "closed_at"):
            if isinstance(strict.get(key), (datetime.date, datetime.datetime)) and isinstance(lite.get(key), str):
                hit = True
        retyped += hit
        same += not hit
    return retyped, same


def main() -> int:
    failures = 0

    print("A. emitter sweep — scalars emitted bare that a strict reader retypes")
    bad = check_emitter()
    for value, emitted, strict in bad:
        print(f"   {value!r:<10} emitted as {emitted:<10} -> PyYAML reads {strict}")
    print(f"   {len(bad)} of {len(CANDIDATES)} probe shapes retyped\n")
    failures += bool(bad)

    print("B. reachability — `goc status <card> active` on a named git branch")
    for branch in ("1.5", "off"):
        hit = check_worker_path(branch)
        if hit is None:
            print(f"   branch {branch!r}: worker round-trips identically")
            continue
        line, lite, strict = hit
        print(f"   branch {branch!r}: goc wrote  {line}")
        print(f"{'':>16} yaml_lite  {lite!r}")
        print(f"{'':>16} PyYAML     {strict!r}")
        failures += 1
    print()

    print("C. shipped deck — cards whose date fields a strict reader retypes")
    retyped, same = check_shipped_deck()
    print(f"   {retyped} card(s) carry a bare date-only created/closed_at (strict reader: date)")
    print(f"   {same} card(s) carry the emitter's current quoted form (strict reader: str)")
    failures += bool(retyped)
    print()

    if failures:
        print(f"FAIL: {failures} check(s) show the strict-reader coercion term is missing.")
        return 1
    print("PASS: every emitted scalar keeps its type under a standard YAML reader.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
