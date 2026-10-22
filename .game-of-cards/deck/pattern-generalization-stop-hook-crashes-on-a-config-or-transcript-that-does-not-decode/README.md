---
title: pattern-generalization-stop-hook-crashes-on-a-config-or-transcript-that-does-not-decode
summary: "The pattern-generalization Stop hook read .game-of-cards/config.yaml and the session transcript in the host's default encoding and caught only OSError, so a config the host could not decode made it exit 1 at every turn end, even with the hook off: one Latin-1 byte did it on a UTF-8 host, and the shipped template's em dash did it where the default encoding is ASCII or a CJK code page. With the hook on, a UTF-8 transcript holding an emoji crashed it there too. Fixed: both reads now use encoding='utf-8' and treat a decode failure as an unreadable file, as the same file's _shared_worktree_deck_root already did for config.yaml."
status: done
stage: null
contribution: medium
created: "2026-10-14T05:18:20Z"
closed_at: "2026-10-14T05:24:17Z"
human_gate: none
advances:
  - hook-scripts-keep-spawning-one-crash-fix-per-malformed-input-shape
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — both hook-off cases exit 0 and the hook-on case exits 2 with the reminder
  - [x] TDD: regression tests in `tests/test_pattern_generalization_hook.py` cover a config.yaml that does not decode (`_enabled` returns False) and the hook script run with an ASCII default encoding (template config exits 0; hook on with a non-ASCII UTF-8 transcript exits 2), and fail against today's hook
  - [x] MECHANICAL: `_enabled` and `_had_code_mutation` in `goc/templates/hooks/pattern_generalization_check.py` read with `encoding="utf-8"` and treat a decode failure the way they treat an unreadable file, as `_shared_worktree_deck_root` in the same file already does
  - [x] MECHANICAL: mirrors regenerated — `python scripts/sync_plugin_assets.py --check` is clean
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass
worker: {who: "claude[bot]", where: main}
---

# The pattern-generalization Stop hook crashes on a config or transcript that does not decode

## Location

`goc/templates/hooks/pattern_generalization_check.py`, mirrored into
`claude-plugin/hooks/`, `codex-plugin/hooks/` and `.claude/hooks/`, and
into the `goc/templates/hooks/` copy inside both plugin payloads:

- `:235-241` (`_enabled`): `config.read_text(encoding="utf-8")` inside
  `except (OSError, ValueError):`. It was `config.read_text()` inside
  `except OSError:`.
- `:304-308` (`_had_code_mutation`): `path.read_text(encoding="utf-8")`
  inside `except (OSError, ValueError):`. It was `path.read_text()`
  inside `except OSError:`.
- `:339-370` (`main`): calls `_enabled` (`:359`) on every Stop event
  before it reads the transcript path or the transcript.
- `tests/test_pattern_generalization_hook.py:386`
  (`UndecodableInputTest`): the regression tests.

## What was broken

`_enabled` is the opt-in gate, and its docstring promises a quiet
default ("Absent config, absent key, `false`, or any other value leaves
the hook disabled."). It read the config like this:

```python
    try:
        m = re.search(
            r"pattern_generalization_check\s*:\s*(\S+)", config.read_text()
        )
        return bool(m and m.group(1) in _TRUE_SET)
    except OSError:
        return False
```

`config.read_text()` decodes in the host's default encoding, and a
decode failure raises `UnicodeDecodeError`, a `ValueError` that
`except OSError` let through. `main` calls `_enabled` first on every
Stop event, so the hook exited 1 before it learned whether it was even
on.

The same file already read the same `config.yaml` correctly, in the
shared-deck redirect added by
[python-hooks-ignore-git-worktree-shared-deck-resolution](../python-hooks-ignore-git-worktree-shared-deck-resolution/):

```python
    config_path = common_root / ".game-of-cards" / "config.yaml"
    try:
        text = config_path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return None
```

`_had_code_mutation` had the same gap for the transcript, which Claude
Code and Codex write as UTF-8 JSONL:
`lines = path.read_text().splitlines()` inside `except OSError:`.

## Empirical evidence

`reproduce.py` runs the hook template with JSON on stdin in three
scratch projects. It forces Python's UTF-8 mode for the first case and
an ASCII default encoding (`LC_ALL=C`, `PYTHONUTF8=0`,
`PYTHONCOERCECLOCALE=0`) for the other two, so the result does not
depend on the host. Before the fix (913ac168):

```
shipped config.yaml template under common Windows code pages:
  cp1252: decodes
  cp932: does not decode (illegal multibyte sequence at byte 3467)
  cp936: does not decode (illegal multibyte sequence at byte 3467)
  cp949: does not decode (illegal multibyte sequence at byte 3465)
  cp950: does not decode (illegal multibyte sequence at byte 3465)

[FAIL] hook off, config.yaml with one Latin-1 byte, UTF-8 mode: exit 1, expected 0 (UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 36: invalid continuation byte)
[FAIL] hook off, shipped template config.yaml, ASCII default encoding: exit 1, expected 0 (UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2 in position 3465: ordinal not in range(128))
[FAIL] hook on, UTF-8 transcript with an emoji, ASCII default encoding: exit 1, expected 2 (UnicodeDecodeError: 'ascii' codec can't decode byte 0xf0 in position 70: ordinal not in range(128))

FAIL: 3 of 3 cases crash the Stop hook.
```

After the fix:

```
[OK] hook off, config.yaml with one Latin-1 byte, UTF-8 mode: exit 0, expected 0
[OK] hook off, shipped template config.yaml, ASCII default encoding: exit 0, expected 0
[OK] hook on, UTF-8 transcript with an emoji, ASCII default encoding: exit 2, expected 2

OK: the hook exits 0 when off and reminds when on, whatever the bytes.
```

The code-page lines are unchanged by the fix: they describe the
template, whose comments (`goc/templates/game_of_cards/config.yaml:65`
onwards) carry the em dashes the CJK code pages reject. The hook no
longer reads the file in the host's code page.

## Why it matters

The Stop hook is registered by both plugin payloads and by the
vendored install, and fires at every turn end whether or not the repo
opted in. A config it could not decode therefore turned every turn end
into a hook error, in repos that never enabled the hook.

Reachability:

- **Windows with a CJK code page.** Before Python 3.15 (PEP 686),
  Python on Windows reads text in the ANSI code page unless UTF-8 mode
  is on. On a Japanese, Chinese or Korean system that is cp932, cp936,
  cp949 or cp950, and none of them decodes the shipped template. Every
  goc repo on such a host errored at every turn end.
- **Any host, a hand-edited config.** An editor that saves Latin-1 or
  cp1252 leaves a byte UTF-8 rejects. Nothing else reports it: the
  engine's `load_deck_config` catches every exception and reads the
  file as no config.
- **The transcript**, once the hook is on: on the same non-UTF-8 hosts,
  any prompt or tool output holding a character outside the code page
  crashed the hook at the end of that turn and every later one.

The engine and installer side of the codec question is
[goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8](../goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8/),
which is decision-gated and counts only `goc/engine.py` and
`goc/install.py`. The hooks had already chosen UTF-8: the SessionStart
hook reads cards and config with `encoding="utf-8"`, and so did this
file's redirect helper. These two reads were the outliers. The
SessionStart hook had the same gap for card READMEs
([session-start-hook-crashes-on-a-card-whose-bytes-do-not-decode](../session-start-hook-crashes-on-a-card-whose-bytes-do-not-decode/)).

## Fix

- `_enabled` reads with `config.read_text(encoding="utf-8")` and
  returns False on `(OSError, ValueError)`, the read
  `_shared_worktree_deck_root` already does on the same file. A config
  that does not decode reads as absent, which is how the engine's
  `load_deck_config` treats it, so the hook stays off even if the file
  opts in. The regex now runs outside the `try`, unchanged.
- `_had_code_mutation` reads with `path.read_text(encoding="utf-8")`
  and returns False on `(OSError, ValueError)`. Pinning the codec reads
  the hosts' UTF-8 transcripts correctly on every host; a transcript
  that still does not decode is treated like an unreadable one, so no
  reminder fires.
- The five mirrors were regenerated by `scripts/sync_plugin_assets.py`.

`UndecodableInputTest` covers both reads in-process (a config holding
`pattern_generalization_check: true` plus a Latin-1 byte leaves the
hook off; a transcript with a stray 0xFF byte counts as no mutation)
and runs the hook script with an ASCII default encoding (the shipped
template config exits 0; the hook on, with an emoji in a UTF-8
transcript, exits 2 with the reminder). The two script runs skip where
the host cannot be given an ASCII default encoding. All four fail
against the pre-fix hook.

`deck_prompt_router.py` reads no file; its stdin decode errors already
land in `except (json.JSONDecodeError, ValueError)`. Every file read in
`goc/templates/hooks/` now names its encoding.

## Artifacts

- reproduce.py
