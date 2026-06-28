---
title: goc-help-omits-install-and-upgrade-subcommands
summary: "`goc --help` lists 16 engine verbs but omits `install` and `upgrade` — they are intercepted upstream in cli.py before argparse runs, so the parser that powers --help never registers them. Every kickoff/AGENTS.md/skill that tells a user to run `goc --help` for the verb list misleads them: the two bootstrap commands needed to onboard are invisible at the top-level discovery surface."
status: open
stage: null
contribution: medium
created: "2026-05-30T11:34:33Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — `uv run goc --help` output contains both `install` and `upgrade` in the subcommand list
  - [ ] TDD: `uv run goc install --help` and `uv run goc upgrade --help` continue to work (early intercept preserved OR subparser dispatch wired correctly)
  - [ ] TDD: regression test in tests/ asserting both verbs appear in `goc --help` output
  - [ ] MECHANICAL: implementation lands per chosen Decision option (stub subparser registration in `_build_parser`, OR explicit epilog/usage note, OR full move into engine parser)
  - [ ] MECHANICAL: `uv run goc validate` passes
---

# `goc --help` omits the `install` and `upgrade` subcommands

## Location

- `goc/cli.py:41-99` — early-intercept short-circuit
- `goc/engine.py:2576-2748` — `_build_parser` subparser registrations (no `install` / `upgrade`)

## What's broken

`goc/cli.py` routes `install` and `upgrade` to argparse-independent
functions *before* the engine's argparse parser is built:

```python
# goc/cli.py:38-46
argv = sys.argv[1:]

# --version / -V before any other parsing
if argv and argv[0] in ("-V", "--version"):
    print(f"goc, version {__version__}")
    return

# Route install / upgrade to their argparse-independent functions
if argv and argv[0] in ("install", "upgrade"):
    sub = argv[0]
    ...
    return

# Everything else goes to the argparse engine
engine_cli(argv)
```

The only path that runs `_build_parser()` (and therefore the only
path that prints `goc --help`) is `engine_cli(argv)`, which never
sees `install` / `upgrade` as registered subcommands. `_build_parser`
itself registers 16 verbs (`goc/engine.py:2576-2748` — `validate`,
`quality-pass`, `done`, `attest`, `status`, `new`, `wait`, `advance`,
`unadvance`, `repair-edges`, `move`, `decide`, `triage`, `show`,
`migrate`, `migrate-list-style`) and stops there.

Verified live (2026-05-30):

```text
$ uv run goc --help
usage: goc [-h] ...
           {validate,quality-pass,done,attest,status,new,wait,advance,
            unadvance,repair-edges,move,decide,triage,show,migrate,
            migrate-list-style}
           ...
```

No `install`. No `upgrade`. Yet:

```text
$ uv run goc install --help
usage: goc install [-h] [--dry-run] [--agents AGENTS] [--claude] [--codex]
                   [--local-skills]
                   [--briefing-target {AGENTS.md,CLAUDE.md,CLAUDE.local.md}]
```

— proving the verbs *exist*; they are just invisible at the discovery
surface.

The team is aware the two are "special": the closed card
[agents-md-architecture-section-cites-removed-click-and-omits-verbs](../agents-md-architecture-section-cites-removed-click-and-omits-verbs/)
explicitly says *"all 14 engine verbs (minus install/upgrade)"*. But
no card has filed the user-facing consequence — a `--help` whose own
output cannot tell a new user how to install.

## Why it matters (reachability)

Every doc that tells a user "run `goc --help` for the verb list"
leads them astray:

- `goc/templates/AGENTS_GOC.md:5` — *"The CLI is `goc` (`goc --help`)."*
  This is installed into every consumer repo's AGENTS.md/CLAUDE.md by
  `goc install`, so every shipped repo carries the misleading hint.
- `goc/templates/skills/deck/SKILL.md:140` — *"Run `goc --help` for
  the full verb list."*
- `goc/templates/skills/codex-kickoff/SKILL.md:70` — kickoff itself
  invokes `goc --help` while onboarding the user.

A user with no GoC scaffolding follows the kickoff skill, which tells
them to run `goc install`. They run `goc --help` (as the AGENTS.md
they just read told them to) to confirm — and learn that `install`
does not exist as a subcommand. The bootstrap command is not
discoverable through the surface every other command is discoverable
through.

## Empirical evidence

See `reproduce.py`. Output (2026-05-30):

```text
goc --help output (subcommands line):
  {validate,quality-pass,done,attest,status,new,wait,advance,unadvance,repair-edges,move,decide,triage,show,migrate,migrate-list-style}

ASSERT install in --help output: FAIL
ASSERT upgrade in --help output: FAIL

goc install --help: OK (verb exists, just hidden from --help)
goc upgrade --help: OK (verb exists, just hidden from --help)
```

## Decision required

Three credible fix paths; the choice changes the engine/cli boundary:

### Option A — Register stub subparsers on `_build_parser`, keep cli.py intercept

Add lightweight `subparsers.add_parser("install", help="...")` and
`subparsers.add_parser("upgrade", help="...")` entries in
`_build_parser` (`goc/engine.py:2576`) with the same flag set the cli.py
intercept defines. The cli.py early-route keeps short-circuiting the
actual invocation (so `install` / `upgrade` continue to bypass the
engine's deck loader, which is appropriate — they run before a deck
exists). The subparsers are *discovery-only*: their dispatch is never
reached.

- **Pro:** smallest change; help text stays consistent; engine remains
  unaware of install/upgrade implementation.
- **Con:** flag definitions duplicated between cli.py and engine.py;
  future drift risk.

### Option B — Add a synthetic epilog / usage note to `_build_parser`

Append to the parser's `epilog=`: *"Bootstrap commands: `install`,
`upgrade` — see `goc install --help` and `goc upgrade --help`."*
No subparser changes; the verbs remain absent from the
`{...}` choices line but are visible at the bottom of `--help`.

- **Pro:** zero duplication; smallest possible patch.
- **Con:** the canonical subcommand list still lies; users grepping
  the `{...}` choices line still miss them; tab-completion (if added)
  still misses them.

### Option C — Move `install` / `upgrade` fully into `_build_parser`

Register real subparsers that dispatch into `install._install` /
`install._upgrade`. Delete the cli.py intercept. The engine parser
becomes the single source of truth for the verb set.

- **Pro:** eliminates the two-place definition; --help becomes
  authoritative; consistent argparse error formatting across verbs.
- **Con:** requires `_build_parser` to import from `install.py`
  (currently the dependency runs the other way: cli.py imports
  from both); the engine's deck-loader assumptions may need to be
  guarded for these two verbs since they run before a deck exists.

Recommended default: **Option A** — preserves the existing
engine/cli boundary, fixes discoverability, and the duplicated
flag set is small (5 flags × 2 commands). Pick B if reviewers
prefer zero new code; pick C if the cli.py/engine.py split feels
like accidental complexity worth removing.

## Fix sketch (Option A)

In `goc/engine.py` `_build_parser`, after the existing subparser
registrations:

```python
# Discovery-only stubs — actual dispatch is intercepted in cli.py
# before the engine parser runs. Keeping help text in sync with
# cli.py is enforced by tests/test_help_lists_install_and_upgrade.py.
p_install = subparsers.add_parser(
    "install",
    help="Scaffold a fresh repo with the shared GoC files and selected harnesses.",
)
p_upgrade = subparsers.add_parser(
    "upgrade",
    help="Re-sync skill templates, AGENTS.md, and CLAUDE.md sections.",
)
```

(The actual flag-level help is reachable via `goc install --help` /
`goc upgrade --help`, which already render correctly through the
cli.py intercept — so the stubs need only the verb-line help text.)

## Cross-references

- [agents-md-architecture-section-cites-removed-click-and-omits-verbs](../agents-md-architecture-section-cites-removed-click-and-omits-verbs/)
  — closed; noted the install/upgrade carve-out without filing this
  user-facing bug.
- [global-cli-flags-silently-dropped-by-subcommand-flag-defaults](../global-cli-flags-silently-dropped-by-subcommand-flag-defaults/)
  — open; related subparser-vs-top-level-parser issue, distinct
  root cause.
