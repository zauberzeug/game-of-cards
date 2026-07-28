#!/usr/bin/env python3
"""The OpenClaw plugin has no host-valid route to a no-subcommand `goc` read.

The engine renders the queue / `--board` / `--ready` / `--json` deck dump only
when argparse resolves `args.command is None` (`goc/engine.py` `cli()`:
`if args.command is None: _cmd_default(args)`). Every other verb is a
subcommand that ignores the top-level filter flags.

Three checks, all static on the shipped artifacts:

1. The registered `goc` tool cannot express that invocation — `verb` is a
   required literal union of engine subparsers plus tool-only verbs, and
   `buildArgs` unconditionally splices `input.verb` into the argv.
2. The porter's own fallback ("shell out via the `exec` tool") names a bare
   `goc` binary that the OpenClaw payload does not ship: no `bin/` directory,
   no `bin` field in `package.json`, no PATH-prepend (the plugin's premise),
   and the README explicitly disclaims the `pipx install` prerequisite.
3. Every `goc` bullet the porter emits into the ported `## Context` blocks is
   a no-subcommand invocation, so check 1 applies to all of them.

Exits non-zero while any no-subcommand `goc` read is unreachable by both
routes; exits zero once the chosen surface can express one.
"""
from __future__ import annotations

import json
import re
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

PLUGIN = ROOT / "openclaw-plugin"
DIST = PLUGIN / "dist" / "index.js"
INDEX_TS = PLUGIN / "index.ts"
PORTER = ROOT / "scripts" / "port_skills_to_openclaw.py"

failures: list[str] = []


# ── 1. the registered tool always injects a verb ────────────────────────────

def js_array(text: str, name: str) -> list[str]:
    m = re.search(rf"(?:var|const)\s+{re.escape(name)}\s*=\s*\[(.*?)\]", text, re.S)
    if not m:
        raise SystemExit(f"could not find {name} in the shipped bundle")
    return re.findall(r'"([^"]+)"', m.group(1))


dist_src = DIST.read_text(encoding="utf-8")
ts_src = INDEX_TS.read_text(encoding="utf-8")

verbs = js_array(dist_src, "GOC_VERBS") + js_array(dist_src, "TOOL_ONLY_VERBS")
print(f"tool verb union ({len(verbs)}): {', '.join(verbs)}")

# `verb` is required: TypeBox marks every property not wrapped in
# `Type.Optional` as required, and `verb:` is not wrapped.
verb_optional = re.search(r"verb:\s*Type\.Optional", dist_src) is not None
print(f"verb declared Type.Optional: {verb_optional}")

build_args = re.search(r"function buildArgs\(input\)\s*\{(.*?)\n\}", dist_src, re.S)
if not build_args:
    raise SystemExit("could not find buildArgs in the shipped bundle")
returns_verb = "input.verb" in build_args.group(1).split("return", 1)[-1]
print(f"buildArgs unconditionally splices input.verb: {returns_verb}")

if not verb_optional and returns_verb:
    failures.append(
        "the registered `goc` tool cannot emit a no-subcommand argv "
        "(verb is required and buildArgs always splices it), so the engine's "
        "`args.command is None` renderer — queue / --board / --ready / --json — "
        "is unreachable through the tool"
    )

# The engine really does gate the queue renderer on "no subcommand".
engine_src = (ROOT / "goc" / "engine.py").read_text(encoding="utf-8")
gated = "if args.command is None:\n        _cmd_default(args)" in engine_src
print(f"engine gates _cmd_default on `args.command is None`: {gated}")


# ── 2. the documented `exec` fallback has no binary to run ──────────────────

pkg = json.loads((PLUGIN / "package.json").read_text(encoding="utf-8"))
has_bin_field = "bin" in pkg
bin_dir_shipped = (PLUGIN / "bin").is_dir() or "bin/" in pkg.get("files", [])
no_path_prepend = "no auto-PATH-prepend" in ts_src
disclaims_pipx = "no `pipx`" in (PLUGIN / "README.md").read_text(encoding="utf-8")
print(
    f"payload ships a goc binary: bin field={has_bin_field} bin/ dir={bin_dir_shipped}"
)
print(f"index.ts states OpenClaw has no auto-PATH-prepend: {no_path_prepend}")
print(f"README disclaims the pipx prerequisite: {disclaims_pipx}")

porter_src = PORTER.read_text(encoding="utf-8")
exec_fallback = "shell out via the `exec` tool" in porter_src
print(f"porter emits the `exec` fallback instruction: {exec_fallback}")

if exec_fallback and not has_bin_field and not bin_dir_shipped:
    failures.append(
        "the porter instructs agents to `exec` a bare `goc …` while the "
        "OpenClaw payload ships no `goc` binary (no bin/, no bin field) and "
        "documents no PATH-prepend — the fallback is command-not-found on a "
        "stock host"
    )


# ── 3. every ported Context bullet is a no-subcommand invocation ────────────

SUBCOMMANDS = set(js_array(dist_src, "GOC_VERBS"))
BULLET = re.compile(r"^- `(.+)`$", re.MULTILINE)
MARKER = "shell out via the `exec` tool:"

total = 0
expressible = 0
per_skill: list[tuple[str, int]] = []
for skill_md in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
    text = skill_md.read_text(encoding="utf-8")
    if MARKER not in text:
        continue
    block = text.split(MARKER, 1)[1].split("\n#", 1)[0]
    goc_bullets = [c for c in BULLET.findall(block) if c.startswith("goc")]
    if not goc_bullets:
        continue
    per_skill.append((skill_md.parent.name, len(goc_bullets)))
    for cmd in goc_bullets:
        total += 1
        # First non-flag token after `goc` — a subcommand makes it tool-expressible.
        tokens = cmd.split()[1:]
        head = next((t for t in tokens if not t.startswith("-")), None)
        if head in SUBCOMMANDS:
            expressible += 1

print(
    "ported Context `goc` bullets: "
    + ", ".join(f"{name}={n}" for name, n in per_skill)
    + f" (total {total})"
)
print(f"  expressible through the tool (carry a subcommand): {expressible}/{total}")

if total and expressible == 0:
    failures.append(
        f"all {total} `goc` bullets the porter emits across "
        f"{len(per_skill)} ported skills are no-subcommand invocations, so none "
        "is expressible through the tool the same paragraph points at"
    )


# ── verdict ─────────────────────────────────────────────────────────────────

print()
if failures:
    for f in failures:
        print(f"FAIL: {f}")
    sys.exit(1)
print("PASS: a no-subcommand goc read is reachable on OpenClaw")
