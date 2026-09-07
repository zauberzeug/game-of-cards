---
title: agents-md-cli-bullet-describes-parser-wiring-the-entry-point-never-does
summary: "AGENTS.md's `## Code architecture` section says `goc/cli.py` \"Builds the engine's argparse parser via `_build_parser`, bolts on `install` + `upgrade` from `install.py`, and adds `--version`\". All three clauses are false: cli.py imports `_build_parser` and never calls it (the parser is built inside `engine.cli()`), install/upgrade are intercepted on `argv[0]` before argparse and routed to two standalone parsers rather than registered as subcommands, and `--version` is registered by `engine._build_parser` — as cli.py's own comment three lines above the interception says. The bullet is the always-loaded briefing an agent reads before touching the CLI, and it contradicts the open card `goc-help-omits-install-and-upgrade-subcommands`, whose whole premise is that the two verbs are never registered on that parser."
status: done
stage: null
contribution: high
created: "2026-08-15T04:34:08Z"
closed_at: "2026-08-15T04:42:31Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [documentation, infra, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — no clause of the AGENTS.md `goc/cli.py` bullet asserts wiring `goc/cli.py` does not perform.
  - [x] TDD: `tests/test_guidance_accuracy.py` gains assertions in `AgentsArchitectureAccuracyTest` that derive each claim from the tree (cli.py's AST and the engine parser) rather than restating it, so the bullet turns the build red the day the wiring changes back.
  - [x] MECHANICAL: the `goc/cli.py` bullet in `AGENTS.md` describes what the entry point actually does — restores SIGPIPE, intercepts `install`/`upgrade` on `argv[0]` and routes them to standalone parsers in `install.py`, delegates everything else to `engine.cli()` (which builds the parser and owns `--version`).
  - [x] MECHANICAL: the unused `_build_parser` import is removed from `goc/cli.py:13` — it is the mechanical evidence for the false first clause, and leaving it invites the claim back.
  - [x] PROCESS: cross-referenced from [goc-help-omits-install-and-upgrade-subcommands](../goc-help-omits-install-and-upgrade-subcommands/), whose premise the stale bullet contradicts.
  - [x] PROCESS: `uv run goc validate` passes, and `uv run python -m unittest discover -s tests` introduces no new failure — the suite's only red is the pre-existing `test_canonical_tag_rows.test_live_cards_satisfy_every_state_row`, tracked by [regression-suite-red-on-main-over-the-unverified-tag-row](../regression-suite-red-on-main-over-the-unverified-tag-row/) and red on the same test before this card's first edit.
worker: {who: "claude[bot]", where: main}
---

# AGENTS.md's `goc/cli.py` bullet describes parser wiring the entry point never does

## Location

`AGENTS.md:148-151`, the first bullet of `## Code architecture`:

```markdown
- **`goc/cli.py`** — thin argparse entry point. Builds the engine's
  argparse parser via `_build_parser`, bolts on `install` + `upgrade`
  from `install.py`, and adds `--version`. Wired as
  `goc = "goc.cli:main"` in `pyproject.toml`.
```

The code it describes: `goc/cli.py:13` (the import), `goc/cli.py:45-98`
(the interception), `goc/engine.py:4029` (where the parser is really
built), `goc/engine.py:3772` (where `--version` is really registered).

## What's broken

Three clauses, three contradictions with the code.

**1. "Builds the engine's argparse parser via `_build_parser`."**
`goc/cli.py:13` imports the symbol and nothing calls it — the only two
occurrences in the file are the import and a prose comment:

```python
# goc/cli.py:13
from goc.engine import _build_parser, cli as engine_cli
```

The parser is built one level down, inside the function cli.py delegates
to:

```python
# goc/engine.py:4028-4030
def cli(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
```

So the import is dead weight, and the bullet's mental model — cli.py holds
the parser object and composes onto it — is exactly backwards.

**2. "bolts on `install` + `upgrade` from `install.py`."** Nothing is
bolted onto the engine parser. The two verbs are intercepted on `argv[0]`
*before* argparse runs and handed to two freshly constructed, standalone
parsers:

```python
# goc/cli.py:45-52
if argv and argv[0] in ("install", "upgrade"):
    sub = argv[0]
    rest = argv[1:]
    import argparse

    if sub == "install":
        p = argparse.ArgumentParser(prog="goc install", ...)
```

The engine parser therefore registers 17 subcommands and neither of these
is among them. That is not a cosmetic distinction: it is the *cause* of
the already-filed
[goc-help-omits-install-and-upgrade-subcommands](../goc-help-omits-install-and-upgrade-subcommands/),
whose summary states the opposite of this bullet —

> they are intercepted upstream in cli.py before argparse runs, so the
> parser that powers --help never registers them

— so AGENTS.md and the deck currently disagree about the same six lines of
code.

**3. "and adds `--version`."** cli.py registers no arguments at all.
`--version` is an action on the engine parser:

```python
# goc/engine.py:3772
parser.add_argument("--version", "-V", action="version",
```

and cli.py's own comment, three lines above the interception block, says so
in as many words:

```python
# goc/cli.py:39-42
# --version / -V is registered as an argparse action on the engine
# parser (see goc.engine._build_parser), so it works at any top-level
# position and is listed in `goc --help`. It is handled inside
# engine_cli below alongside every other global flag.
```

A file that contradicts the doc describing it, in a comment the doc's
author had to scroll past, is the cleanest possible statement of the drift.

## Empirical evidence

`uv run python .game-of-cards/deck/agents-md-cli-bullet-describes-parser-wiring-the-entry-point-never-does/reproduce.py`:

```
=== what goc/cli.py actually does ===
imports `_build_parser`            : True
calls   `_build_parser`            : False
registers `--version` itself       : False

=== what the engine parser actually holds ===
engine parser registers `--version`: True
engine subcommands (17)            : ['advance', 'attest', 'decide', 'done', 'migrate', 'migrate-list-style', 'move', 'new', 'publish', 'quality-pass', 'repair-edges', 'show', 'status', 'triage', 'unadvance', 'validate', 'wait']
of which install/upgrade           : (none)

=== verdict ===
[FAIL] AGENTS.md claims 'builds the engine parser via _build_parser' — cli.py imports `_build_parser` but never calls it; `engine.cli()` builds the parser itself
[FAIL] AGENTS.md claims 'bolts install + upgrade onto that parser' — install/upgrade are intercepted on argv[0] before argparse and routed to two standalone parsers; neither is an engine subcommand (this is why `goc --help` omits them)
[FAIL] AGENTS.md claims 'adds --version' — `--version` is registered by `engine._build_parser`, as cli.py's own comment states

3 false claim(s) in AGENTS.md:148-151.
```

After the fix, the same script exits 0:

```
=== what goc/cli.py actually does ===
imports `_build_parser`            : False
calls   `_build_parser`            : False
registers `--version` itself       : False
...
claims still asserted              : (none)

=== verdict ===
[ok]   AGENTS.md no longer claims 'builds the engine parser via _build_parser'
[ok]   AGENTS.md no longer claims 'bolts install + upgrade onto that parser'
[ok]   AGENTS.md no longer claims 'adds --version'

AGENTS.md's goc/cli.py bullet matches what cli.py does.
```

The three new negative assertions in
`tests/test_guidance_accuracy.py` were each checked against the stale
bullet text and match it, and the two new positive assertions
(`engine.cli()`, `argv[0]`) each fail on it — so the guard demonstrably
catches the offender rather than merely reporting a clean tree.

## Why it matters

`AGENTS.md` is loaded into every agent session in this repo (`CLAUDE.md` is
just `@AGENTS.md`), and `## Code architecture` is the map an agent consults
before touching the CLI. All three false clauses point the same wrong way —
"the composition happens in cli.py" — so an agent asked to add a verb, move
a global flag, or fix `goc --help` starts by editing the wrong file and
looking for a parser object that is not there.

The `goc --help` case is not hypothetical: that fix is already filed and
open, and an agent that pulls it while trusting this bullet will look for
the missing `add_parser("install", ...)` call the bullet implies, rather
than the `argv[0]` interception that actually has to change.

This is the seventh recorded instance of an AGENTS.md claim drifting from
the code — after
[agents-md-architecture-section-cites-removed-click-and-omits-verbs](../agents-md-architecture-section-cites-removed-click-and-omits-verbs/),
[agents-md-claims-bundled-engine-omits-hook-templates-it-now-ships](../agents-md-claims-bundled-engine-omits-hook-templates-it-now-ships/),
[agents-md-claims-no-test-suite-but-ci-runs-regression-tests](../agents-md-claims-no-test-suite-but-ci-runs-regression-tests/),
[agents-md-claims-the-card-schema-is-inlined-into-the-skill-body](../agents-md-claims-the-card-schema-is-inlined-into-the-skill-body/),
[agents-md-documents-removed-system-flag-as-the-ci-install](../agents-md-documents-removed-system-flag-as-the-ci-install/) and
[agents-md-mislabels-claude-settings-json-as-user-owned-permission-list](../agents-md-mislabels-claude-settings-json-as-user-owned-permission-list/),
all closed. The family already has its architectural answer:
`tests/test_guidance_accuracy.py`, which pins doc claims by *deriving* them
from the tree. So this card connects to that root rather than filing an
eighth umbrella — the gap is that the guard's `AgentsArchitectureAccuracyTest`
only pins what the bullet must *not* say (`click`) and the exhaustiveness of
the sibling verb list. The three positive claims about cli.py's own wiring
were never pinned, which is why the 2026-05-27 Click→argparse rewrite of
this bullet introduced three new false statements while turning the guard
green.

## Fix (applied)

1. `AGENTS.md:148-156` — the bullet now describes what the file does:

   ```markdown
   - **`goc/cli.py`** — thin console-script entry point. Restores the
     default SIGPIPE disposition, intercepts `install` / `upgrade` on
     `argv[0]` and routes them to standalone argparse parsers over
     `install.py`, and delegates every other invocation to
     `engine.cli()`, which builds the engine parser (`_build_parser`)
     and owns the global flags including `--version`. Because the two
     install verbs never reach that parser, they do not appear in
     `goc --help` — see
     [goc-help-omits-install-and-upgrade-subcommands](../goc-help-omits-install-and-upgrade-subcommands/).
     Wired as `goc = "goc.cli:main"` in `pyproject.toml`.
   ```

2. `goc/cli.py:11` — the unused import is gone, and the module docstring
   (which carried the same three false claims) now matches the bullet:

   ```python
   from goc.engine import cli as engine_cli
   ```

   The three plugin mirrors (`claude-plugin/goc/cli.py`,
   `codex-plugin/goc/cli.py`, `openclaw-plugin/goc/cli.py`) were
   regenerated by `scripts/sync_plugin_assets.py`.

3. `tests/test_guidance_accuracy.py` — `AgentsArchitectureAccuracyTest`
   gained a behavioural test (`test_entry_point_wiring_is_what_the_cli_bullet_describes`,
   deriving all three facts from cli.py's AST and the engine parser) plus
   three doc tests that pin the bullet against the stale phrasing and
   require it to name `engine.cli()` and `argv[0]`. The shared
   `_agents_cli_bullet()` helper replaces the inline slice the pre-existing
   `click` test used.

   The behavioural test is the important half: if somebody later
   implements Option A on
   [goc-help-omits-install-and-upgrade-subcommands](../goc-help-omits-install-and-upgrade-subcommands/)
   and registers stub subparsers, that test fails first and points the
   editor back at this bullet — the failure mode this card is a record of.
