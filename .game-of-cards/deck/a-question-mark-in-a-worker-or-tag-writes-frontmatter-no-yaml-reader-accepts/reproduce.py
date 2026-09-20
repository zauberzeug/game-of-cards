#!/usr/bin/env python3
"""A `?` in `worker.who` or in a tag makes goc emit frontmatter strict YAML refuses.

`_yaml_inline` decides whether to quote a plain scalar using a block-context
oracle: `_YAML_SPACE_BOUND_INDICATORS` exempts `-`, `?` and `:` unless they open
the value AND are followed by whitespace, because `?query` really is an ordinary
plain scalar -- *in block context*. But `_yaml_inline` also builds YAML **flow
sequences** for list fields (`tags: [a, b]`), and `_emit_worker` builds a
**flow mapping** (`worker: {who: x, where: y}`) out of the same helper. Inside a
flow collection the plain-scalar acceptance set is strictly narrower: `?` is a
key indicator wherever it appears, so it terminates the scalar and the reader
faults. `,[]{}` -- the other flow indicators -- are already quoted anywhere by
`_YAML_NEEDS_QUOTE`, which leaves `?` as the sole survivor.

This script needs PyYAML only as the strict-reader oracle. goc itself has no
third-party runtime dependency, so the project venv does not carry PyYAML; if
it is unavailable the script still reports the emitted lines and marks the
strict checks SKIPPED. Run it under an interpreter that has PyYAML to see the
full verdict:

    python3 .game-of-cards/deck/<this-card>/reproduce.py   # strict oracle present
    uv run python .game-of-cards/deck/<this-card>/reproduce.py  # oracle SKIPPED
"""

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

from goc.engine import _emit_worker, _yaml_inline, parse_frontmatter  # noqa: E402

try:
    import yaml as strict_yaml
except ModuleNotFoundError:  # pragma: no cover - oracle is optional
    strict_yaml = None


def strict_read(line: str):
    """Return (ok, detail) from the strict reader, or (None, 'SKIPPED')."""
    if strict_yaml is None:
        return None, "SKIPPED (PyYAML not importable)"
    try:
        return True, strict_yaml.safe_load(line)
    except Exception as exc:  # noqa: BLE001 - any strict-reader fault counts
        return False, f"{type(exc).__name__}: {str(exc).splitlines()[0]}"


print("=" * 72)
print("1. Direct emission: the two flow-collection sites")
print("=" * 72)
for label, line in (
    ("worker mapping", "worker: " + _emit_worker({"who": "who?knows", "where": "main"})),
    ("tags sequence ", "tags: " + _yaml_inline(["bug", "needs?review"])),
    ("worker (flat) ", "worker: " + _emit_worker({"who": "who?knows"})),
    ("summary (block)", "summary: " + _yaml_inline("who?knows")),
):
    ok, detail = strict_read(line + "\n")
    verdict = "OK" if ok else ("SKIPPED" if ok is None else "STRICT REJECT")
    print(f"  {label}  {line!r}")
    print(f"      -> {verdict}: {detail}")
print()
print("  The last two lines are block context and are legal: the defect is")
print("  confined to the two sites that splice into a flow collection.")
print()

print("=" * 72)
print("2. Which characters does block context admit but flow context refuse?")
print("=" * 72)
if strict_yaml is None:
    print("  SKIPPED (PyYAML not importable)")
else:
    offenders = []
    for code in range(32, 127):
        ch = chr(code)
        for shape in (f"a{ch}", f"{ch}a", f"a{ch}b"):
            line = "worker: " + _emit_worker({"who": shape, "where": "main"}) + "\n"
            ok, _ = strict_read(line)
            if ok is not True or strict_yaml.safe_load(line) != {
                "worker": {"who": shape, "where": "main"}
            }:
                offenders.append((ch, shape))
    chars = sorted({ch for ch, _ in offenders})
    print(f"  offending characters: {chars!r}  ({len(offenders)} shapes)")
    print("  `,` `[` `]` `{` `}` are already quoted anywhere by _YAML_NEEDS_QUOTE;")
    print("  `?` is the single character the block-context oracle lets through.")
print()

print("=" * 72)
print("3. Reachable through a real goc verb (git user.name -> worker.who)")
print("=" * 72)
with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp)
    env_run = dict(cwd=repo, capture_output=True, text=True)
    subprocess.run(["git", "init", "-q", "."], **env_run)
    subprocess.run(["git", "config", "user.email", "probe@example.com"], **env_run)
    # A question mark in a git author name is unusual but perfectly legal.
    subprocess.run(["git", "config", "user.name", "who?knows"], **env_run)
    (repo / ".game-of-cards" / "deck").mkdir(parents=True)

    def goc(*argv):
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *argv],
            cwd=repo,
            capture_output=True,
            text=True,
            env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT), "HOME": str(repo)},
        )

    goc("new", "probe-card", "--summary", "Probe.", "--contribution", "low",
        "--gate", "none", "--tag", "bug")
    card = repo / ".game-of-cards" / "deck" / "probe-card" / "README.md"
    card.write_text(
        card.read_text()
        .replace("  - [ ] (replace with real criteria)", "  - [ ] TDD: criterion")
        .replace("(write the design doc here)", "Body.")
    )
    goc("publish", "probe-card")
    claim = goc("status", "probe-card", "active")
    print(f"  $ goc status probe-card active   (exit {claim.returncode})")
    print(f"    {claim.stdout.splitlines()[0] if claim.stdout else ''}")

    text = card.read_text()
    worker_line = next(ln for ln in text.splitlines() if ln.startswith("worker:"))
    print(f"  emitted: {worker_line!r}")

    block = text.split("---")[1]
    print(f"  goc validate      : {goc('validate').stdout.strip().splitlines()[-1]}")
    fm, _ = parse_frontmatter(text)
    print(f"  yaml_lite reads   : worker={fm.get('worker')!r}")
    ok, detail = strict_read(block)
    print(f"  strict YAML reads : {'OK' if ok else ('SKIPPED' if ok is None else 'REJECT')}"
          f" -- {detail if not ok else 'parsed'}")
    print()
    print("  Three readers, three answers. The card is committed to the deck in")
    print("  a form no standard YAML reader can load -- and every later")
    print("  full-frontmatter re-emit rewrites it the same way.")

print()
print("=" * 72)
print("4. Does the repo's own strict-YAML guard catch it?")
print("=" * 72)
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "goc_card_yaml_guard", ROOT / "scripts" / "check_card_frontmatter_yaml.py"
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
broken = (
    "title: probe-card\n"
    "status: active\n"
    "worker: {who: who?knows, where: main}\n"
)
findings = guard.flag_frontmatter(broken)
print(f"  check_card_frontmatter_yaml.flag_frontmatter(...) -> {findings!r}")
print("  No finding: the guard skips every value opening with `\"`, `'`, `[` or")
print("  `{`, so the emitter's own flow-collection output is outside its reach.")
