---
title: goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8
summary: "Nothing in goc pins UTF-8: 67 `read_text`/`write_text` calls across `goc/engine.py` and `goc/install.py` omit `encoding=`, and stdout is never reconfigured, so every card/template read, write and print falls back to the host locale encoding. On a host whose default encoding is not UTF-8 the bare `goc` queue dies with `UnicodeEncodeError` on the table em-dash, and `goc install` dies with `UnicodeDecodeError` reading `AGENTS_GOC.md` — exiting 1 after leaving a half-written `.game-of-cards/` tree with no briefing and no skills. 27 of the 49 shipped template files carry characters the Windows default ANSI code page cannot encode, so the write path fails too."
status: open
stage: null
contribution: high
created: "2026-09-13T04:42:48Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: the mechanism in `## Decision required` is chosen and recorded in `log.md` with its rationale — per-site `encoding="utf-8"`, a process-wide UTF-8 pin in `goc/cli.py:main`, or both. Question 2 must be answered explicitly: whether the plugin `bin/goc` wrappers and the OpenClaw `python3 -m goc.cli` tool handler are in scope, since they are the invocation path most consumers actually use.
  - [ ] TDD: `reproduce.py` exits zero — encoding-less IO sites are 0, cp1252-unwritable templates are 0 *or* the write path no longer depends on the host code page, and `goc install` plus the bare queue both exit 0 with the host default encoding forced to ASCII.
  - [ ] TDD: a regression test drives at least `install`, the bare queue, `new` and `done` in a subprocess whose environment forces a non-UTF-8 default encoding, and asserts exit 0 with no `UnicodeDecodeError` / `UnicodeEncodeError` in stderr. It must fail against today's code.
  - [ ] TDD: a guard test pins the chosen mechanism against regrowth — if the decision is per-site, it asserts no `read_text(` / `write_text(` / bare `open(` in `goc/*.py` omits `encoding=`; if it is a process-wide pin, it asserts the pin is installed before any verb dispatches.
  - [ ] EMPIRICAL: a card written on a non-UTF-8 host round-trips byte-identically — `goc new` then `goc show` then `goc validate` under the forced encoding produce the same UTF-8 bytes a UTF-8 host produces, with the verdict recorded in `log.md` either way. Silent mojibake in a committed card is the failure this item exists to exclude.
  - [ ] MECHANICAL: `goc install` never leaves a partially-written `.game-of-cards/` tree behind when the briefing read fails — either the read cannot fail, or the failure is reported as a `goc: error:` line rather than a raw traceback.
  - [ ] MECHANICAL: mirrors regenerate clean — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` both pass.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# goc crashes on hosts whose default encoding is not UTF-8

## Location

- `goc/install.py:165` — `_briefing_body`, the read that kills `goc install`.
- `goc/engine.py:4382` — `_cmd_default`, the `print` that kills the bare queue.
- `goc/engine.py:99` — the first of 47 encoding-less text reads in the engine.
- `goc/cli.py:35` — `main()`, the one place a process-wide UTF-8 pin could go.

## What's broken

The package never states an encoding. Every text read, every text write and
every `print` inherits `locale.getpreferredencoding(False)`, so goc's
behaviour is a function of the host's locale rather than of the bytes on
disk. Two call sites stand in for sixty-seven:

```python
# goc/install.py:165
agents_body = (templates / AGENTS_GUIDANCE.template).read_text().rstrip()
```

```python
# goc/engine.py:4382
print("\n".join(lines))
```

Neither is wrong on a UTF-8 host, and neither is reachable in CI, whose
matrix runs under a UTF-8 locale. But the shipped data is unambiguously
UTF-8 — 38 of the 49 files under `goc/templates/` contain non-ASCII text,
and the queue table's own column rule is an em-dash — so on any other host
the two lines decode and encode against the wrong codec.

`goc/cli.py` already knows this program runs on hosts that are not POSIX:

```python
# goc/cli.py:38-40 — the SIGPIPE guard
# Guarded for Windows (no SIGPIPE) and non-main threads
# (signal.signal raises ValueError off the main thread).
```

Windows is exactly the host whose Python default encoding is the ANSI code
page rather than UTF-8, and it is the host this defect hits without anyone
setting an environment variable.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8/reproduce.py`:

```
simulated host default encoding: ANSI_X3.4-1968

[1] behaviour on a non-UTF-8 host
  goc install            -> exit 1: UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2 in position 17: ordinal not in range(12
      left behind: .game-of-cards/ exists=True, AGENTS.md briefing exists=False
  goc (queue listing)    -> exit 1: UnicodeEncodeError: 'ascii' codec can't encode character '\u2014' in position 65: ordinal not in

[2] package text IO that inherits the host encoding
  goc/engine.py: 47 read_text/write_text call(s) without encoding=
      first: goc/engine.py:99: cfg = yaml.safe_load(config_path.read_text()) or {}
  goc/install.py: 20 read_text/write_text call(s) without encoding=
      first: goc/install.py:165: agents_body = (templates / AGENTS_GUIDANCE.template).read_text().rstrip()
  goc/cli.py: 0 read_text/write_text call(s) without encoding=

[3] shipped templates vs the Windows default code page
  shipped template files scanned: 49
  files unwritable under cp1252:  27
  offending characters: '→'x117, '≥'x13, '≤'x11, '─'x8, '∧'x7, '≠'x5, '⇔'x5, '⚠'x4

SUMMARY: encoding-less IO sites=67, cp1252-unwritable templates=27, commands failing on a non-UTF-8 host=2
FAIL: goc still depends on the host's default encoding.
```

`goc install` does not merely fail — it fails *after* scaffolding. The probe
records `.game-of-cards/ exists=True, AGENTS.md briefing exists=False`: the
content stubs, `config.yaml` and the deck directory are on disk (they arrive
through a binary copy that never decodes), while the briefing block, the
skills and the hook registrations never land. A consumer who retries after
fixing their locale meets a repo that is already half-installed.

## Reachability

The probe forces the non-UTF-8 default with `LC_ALL=C` plus `PYTHONUTF8=0`
and `PYTHONCOERCECLOCALE=0`. Those two opt-outs are an artifact of the
*simulation*, not of the defect: PEP 538 and PEP 540 auto-upgrade the `C`
locale specifically, so the C locale is the one non-UTF-8 setting Python
repairs for you. Turning them off reproduces what other hosts present with
no environment variables at all:

- **Windows.** `locale.getpreferredencoding(False)` is the ANSI code page
  (cp1252, cp932, cp936, …) on every Python this project supports. PEP 686's
  UTF-8-by-default lands in 3.15; `.github/workflows/ci.yml` pins the matrix
  at 3.10–3.13. `pipx install game-of-cards` is a documented install channel,
  and the Claude Code desktop app ships for Windows.
- **A POSIX host with an installed non-UTF-8 locale** — `LANG=en_US.ISO-8859-1`
  and friends are not coerced, because they are not the C locale. Latin-1
  decodes every byte without raising, so there the read path produces
  *mojibake* rather than a traceback: a `goc new` on such a host writes a card
  whose em-dashes have been round-tripped through the wrong codec.

The two faces differ in severity. The crash is loud and self-limiting. The
silent one is worse: a card is a committed artifact, so a mis-encoded write
ships the corruption into the deck and into everyone else's checkout.

## Why it matters

`goc install` is the first command a consumer runs and the bare `goc` queue
is the most-run command afterwards. Both are broken on the one host family
whose Python default is not UTF-8, and neither failure is diagnosable from
its output: the user sees a Python traceback naming `pathlib` and `codecs`,
with nothing pointing at their locale.

This is one root cause with 67 sites, not 67 defects, which is why it is
filed as a single architectural card rather than a per-site sweep. It is
adjacent to but distinct from
[goc-leaks-brokenpipeerror-when-stdout-pipe-closes-early](../goc-leaks-brokenpipeerror-when-stdout-pipe-closes-early/)
— that card fixed how `goc` behaves when stdout *closes*; this one is about
which codec stdout uses while it is open. Both land in `goc/cli.py:main`,
which is the argument for option (b) below.

## Decision required

**Question 1 — which mechanism?**

| | Option | For | Against |
|---|---|---|---|
| (a) | `encoding="utf-8"` on all 67 sites | Explicit at every call site; survives being imported as a library, where no entry point runs | 67-site diff across `engine.py` + `install.py`; a new call site can silently omit it again unless a guard test pins it |
| (b) | Pin UTF-8 once in `goc/cli.py:main` — set `PYTHONUTF8`-equivalent behaviour and `sys.stdout.reconfigure(encoding="utf-8")` | One small diff; fixes the stdout face, which (a) does not touch at all | Only covers the console-script path. `goc.engine` imported directly — by `scripts/`, by `tests/`, by the OpenClaw tool handler — keeps the host default |
| (c) | Both | Covers every face and every entry path | Two changes to keep in step |

The two faces are not symmetrical: (a) alone leaves the queue crash, (b)
alone leaves every library consumer. That asymmetry is the substance of the
choice and is why this is gated rather than mechanical.

**Question 2 — what is in scope?**

The mirrors (`claude-plugin/goc/`, `codex-plugin/goc/`, `openclaw-plugin/goc/`)
are byte-synced, so they follow whatever lands in `goc/`. But the *invocation*
paths are hand-written and are how consumers actually reach the engine:
`claude-plugin/bin/goc` and `codex-plugin/bin/goc` shell out to
`python3 -m goc.cli`, and the OpenClaw plugin's tool handler spawns the same
module from `openclaw-plugin/index.ts`. If the decision is (b), those three
files are the ones that decide whether the pin is reached; if it is (a), they
are out of scope. Answer this explicitly rather than by omission.

**Not in scope.** The repo-local `scripts/*.py` already pass
`encoding="utf-8"` where they read cards, and they are never shipped to a
consumer. A separate question — whether `goc` should *reject* a non-UTF-8
card file rather than transcode it — is a different card if anyone wants it.

## Fix

Determined by the decision above. Whichever option wins, the guard test in
the DoD is the part that keeps it from regrowing: this defect exists because
67 call sites each independently omitted one keyword argument, and nothing
in the build has ever looked for that.
