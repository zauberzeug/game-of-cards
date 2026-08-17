#!/usr/bin/env python3
"""Census: which mutating verbs are pinned against a second run?

Seven shipped defects share one shape — an operation correct on its first
run and wrong on its second. Each was fixed with a test for that one verb.
This script measures the consequence: how much of the mutating surface has
a re-run test at all, and whether anything asserts the property as a class.

It does two independent things:

  1. STATIC census — for each verb the engine registers, look for a test
     that exercises it twice. Coverage is the count of verbs that have one.
  2. DYNAMIC probe — actually run each verb twice against a scratch deck in
     a temp directory and compare the deck's bytes after run 1 and run 2.
     This is the class-level check the card argues should exist; running it
     here shows it is cheap and that it generalizes over the verb list
     instead of being written out one verb at a time.

The dynamic probe passing is not the same as the property being guaranteed:
nothing in `tests/` runs it, so a new verb added tomorrow is covered by
nothing. Exit 1 while no class-level re-run test exists in the suite, 0
once one does.
"""

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
TESTS = ROOT / "tests"

# Verbs that write to the deck or the repo. Read-only verbs (validate, show,
# triage) are out of scope: re-running them cannot corrupt anything.
MUTATING = [
    "new", "status", "done", "attest", "decide", "publish", "advance",
    "unadvance", "wait", "repair-edges", "move", "quality-pass",
    "migrate", "migrate-list-style",
]

# The instances this card generalizes, with the test each one shipped.
INSTANCES = [
    ("second-install-exits-nonzero", "2026-05-05", "goc install"),
    ("done-rerun-rewrites-closure-date", "2026-05-05", "goc done"),
    ("make-kickoff-idempotent-on-restart", "2026-05-08", "kickoff skill"),
    ("goc-upgrade-duplicates-the-goc-guidance-block-on-suffixed-versions",
     "2026-05-26", "goc upgrade"),
    ("merge-claude-settings-rewrites-settings-json-on-idempotent-merge",
     "2026-06-23", "_merge_claude_settings"),
    ("merge-claude-settings-spams-bak-files-on-idempotent-merge",
     "2026-06-24", "_merge_claude_settings"),
    ("second-citation-repair-pass-moves-correct-cites-onto-unrelated-code",
     "2026-08-17", "refine-deck citation repair"),
]


def static_census():
    """Verbs with a test that plausibly exercises them twice."""
    blobs = {}
    for path in sorted(TESTS.glob("test_*.py")):
        blobs[path.name] = path.read_text(encoding="utf-8", errors="replace")

    # The signal must be in the test's NAME. Matching the body instead
    # picks up any test that merely mentions a verb near the word "again",
    # which inflates coverage — the same fail-open shape that
    # static-source-guards-never-prove-they-can-catch-an-offender warns
    # about, and it reported 4/14 here against a true 1/14.
    covered = {}
    for verb in MUTATING:
        hits = []
        for name, text in blobs.items():
            for m in re.finditer(r"def (test_\w+)\(", text):
                fn = m.group(1)
                if not re.search(r"idempot|twice|second_run|rerun|re_run", fn):
                    continue
                start = m.end()
                nxt = text.find("\n    def ", start)
                body = text[start: nxt if nxt != -1 else len(text)]
                # and the test must actually drive the CLI — otherwise a
                # parser test that happens to quote "status" as a frontmatter
                # key scores as coverage for `goc status`.
                drives_cli = re.search(r"goc\.cli|_cmd_|cli\.main|run_goc", body)
                if drives_cli and re.search(
                    rf'["\']{re.escape(verb)}["\']', body
                ):
                    hits.append(f"{name}::{fn}")
        if hits:
            covered[verb] = hits
    return covered


def dynamic_probe():
    """Run each verb twice on a scratch deck; report whether run 2 is a no-op."""
    results = []
    tmp = Path(tempfile.mkdtemp(prefix="goc-rerun-"))
    try:
        subprocess.run(["git", "init", "-q", "."], cwd=tmp, check=True)
        for k, v in (("user.email", "a@b.c"), ("user.name", "probe")):
            subprocess.run(["git", "config", k, v], cwd=tmp, check=True)
        (tmp / "pyproject.toml").write_text("x\n", encoding="utf-8")
        (tmp / ".game-of-cards" / "deck").mkdir(parents=True)
        subprocess.run(["git", "add", "-A"], cwd=tmp, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp, check=True,
                       capture_output=True)

        env = {**os.environ, "PYTHONPATH": str(ROOT)}

        # quality-pass and repair-edges register no --commit/--no-commit pair;
        # passing it makes argparse exit 2 and hides the verb's real behaviour.
        NO_COMMIT_FLAG = {
            "new", "status", "done", "attest", "decide", "publish",
            "advance", "unadvance", "wait",
        }

        def goc(*args):
            argv = list(args)
            if argv[0] in NO_COMMIT_FLAG:
                argv.append("--no-commit")
            return subprocess.run(
                [sys.executable, "-m", "goc.cli", *argv],
                cwd=tmp, capture_output=True, text=True, env=env,
            )

        def author(title):
            """goc publish refuses an unauthored scaffold, so fill it in."""
            p = tmp / ".game-of-cards" / "deck" / title / "README.md"
            text = p.read_text(encoding="utf-8")
            text = text.replace(
                "- [ ] (replace with real criteria)",
                "- [ ] MECHANICAL: the probe exercises this card",
            ).replace("(write the design doc here)", "Probe fixture.")
            p.write_text(text, encoding="utf-8")

        def snapshot():
            out = []
            deck = tmp / ".game-of-cards" / "deck"
            for f in sorted(deck.rglob("*")):
                if f.is_file():
                    out.append(
                        f.relative_to(deck).as_posix() + "\0"
                        + f.read_text(encoding="utf-8", errors="replace")
                    )
            return "\n".join(out)

        for t in ("alpha-probe-card", "beta-probe-card"):
            goc("new", t, "--summary", "probe", "--gate", "none")
            author(t)
        # decide needs a card that is actually parked on a gate
        goc("new", "gated-probe-card", "--summary", "probe", "--gate",
            "decision")
        author("gated-probe-card")

        cases = [
            ("publish", ["publish", "alpha-probe-card"]),
            ("wait", ["wait", "alpha-probe-card", "--reason", "external"]),
            ("advance", ["advance", "alpha-probe-card", "--by",
                         "beta-probe-card"]),
            ("status", ["status", "beta-probe-card", "active"]),
            ("decide", ["decide", "gated-probe-card", "--decision", "d",
                        "--because", "b"]),
            ("move", ["move", "beta-probe-card", "gamma-probe-card"]),
            ("quality-pass", ["quality-pass", "--status", "all"]),
            ("repair-edges", ["repair-edges", "--apply"]),
        ]
        for verb, argv in cases:
            first = goc(*argv)
            after_one = snapshot()
            second = goc(*argv)
            after_two = snapshot()
            if first.returncode != 0 and second.returncode != 0:
                verdict = "both runs refused"
            elif after_one == after_two:
                verdict = "stable"
            else:
                verdict = "CHANGED ON RE-RUN"
            results.append((verb, first.returncode, second.returncode, verdict))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return results


def suite_has_class_level_check() -> bool:
    """Is there a test that walks the verb list and re-runs each one?"""
    for path in TESTS.glob("test_*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"MUTATING|for verb in|every mutating verb", text) and \
           re.search(r"idempot|second[_ ]run|re-?run", text, re.I):
            return True
    return False


def main() -> int:
    print("Instances of 'correct once, wrong on re-run' already fixed here:\n")
    for title, when, surface in INSTANCES:
        print(f"  {when}  {surface:32s} {title}")
    print(f"\n  {len(INSTANCES)} instances across "
          f"{len({i[2] for i in INSTANCES})} distinct surfaces\n")

    covered = static_census()
    print(f"static census — mutating verbs with a re-run test: "
          f"{len(covered)}/{len(MUTATING)}")
    for verb in MUTATING:
        mark = "yes" if verb in covered else " - "
        extra = f"  ({covered[verb][0]})" if verb in covered else ""
        print(f"    {mark}  goc {verb}{extra}")

    print("\ndynamic probe — run each verb twice on a scratch deck:")
    for verb, rc1, rc2, verdict in dynamic_probe():
        print(f"    goc {verb:14s} exit {rc1}/{rc2}   {verdict}")

    if suite_has_class_level_check():
        print("\nPASS: the suite carries a class-level re-run check.")
        return 0
    print(
        "\nDEFECT PRESENT: no test in tests/ asserts re-run safety over the "
        "verb list. The probe above shows the class-level check is cheap and "
        "generalizes, but nothing runs it, so coverage stays a thing a verb "
        "earns only after a defect ships."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
