---
title: misspelled-workflow-config-boolean-silently-turns-the-feature-on
summary: "`_coerce_config_bool` recognizes four false spellings and falls through to Python truthiness for everything else, so any unrecognized non-empty scalar in `.game-of-cards/config.yaml`'s `workflow` block reads as True. A typo turns a default-off opt-in ON — `claim_push: nope` arms the remote-push path — and defeats an intentional `auto_commit: off`, whose own \"auto_commit is disabled\" warning then never fires. The sibling reader `get_skills_source` answers the same question with a documented fall-back-to-default, so the fix direction is settled; only silent-vs-warn is open."
status: open
stage: null
contribution: medium
created: "2026-08-26T04:56:56Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: Decision recorded in the body's `## Decision required` section (silent, matching `get_skills_source`, vs warn-once-per-key on stderr) and the gate lowered to `none`. The fall-back-to-default *direction* is already settled by precedent and is not re-litigated here.
  - [ ] TDD: `reproduce.py` exits zero — no misspelling in its table coerces to the opposite of the intent, and neither end-to-end symptom (armed `claim_push`, silently-still-on `auto_commit`) reproduces.
  - [ ] TDD: a regression test under `tests/` drives `_coerce_config_bool` over the recognized true set, the recognized false set, and at least three unrecognized scalars, asserting the chosen behaviour for each — including that `default=False` keys cannot be turned on by an unrecognized value.
  - [ ] MECHANICAL: `_coerce_config_bool` returns the caller's `default` for an unrecognized value, matching `get_skills_source` (`goc/engine.py:5392`); if the decision picks warn-once, the diagnostic names the offending key and value (`workflow.claim_push`, `'nope'`), which means the three call sites at `goc/engine.py:5185`, `:5156` and `:5210` pass their key name in — no call site may report a bare "invalid boolean".
  - [ ] MECHANICAL: non-string non-bool values (a list, a mapping, a float) reach the same path as an unrecognized string — the fallback must not stay `bool(value)` for them either; mirror `get_skills_source`'s `isinstance(value, str)` guard.
  - [ ] MECHANICAL: `goc/templates/game_of_cards/config.yaml` states the accepted spellings beside `auto_commit` (line 30) so the vocabulary is discoverable without reading the engine; this repo's own `.game-of-cards/config.yaml` is user-owned and is NOT rewritten by the fix.
  - [ ] TDD: `uv run goc validate` clean and `uv run python -m unittest discover -s tests` green.
---

# Misspelled workflow config boolean silently turns the feature on

## Location

- `_coerce_config_bool` — `goc/engine.py:5082-5093` (the fallback)
- `auto_commit_enabled` — `goc/engine.py:5185` (`default=True`)
- `_enforce_closure_on_integration_or_exit` — `goc/engine.py:5206` (`default=False`)
- `claim_push_enabled` — `goc/engine.py:5260` (`default=False`)
- the "auto_commit is disabled" warning that never fires — `goc/engine.py:5189`
- `get_skills_source` — `goc/engine.py:5392-5404`, the sibling config reader
  that answers the same question the other way (see the section below)
- the config template the user copies from — `goc/templates/game_of_cards/config.yaml:30`

## What's broken

Every `workflow` boolean in `.game-of-cards/config.yaml` is read through one
helper (`goc/engine.py:5082`):

```python
def _coerce_config_bool(value, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)
```

The two recognized vocabularies are symmetric. The **fallback is not**: a
value that matches neither set lands on `bool(value)`, and every non-empty
string is truthy in Python. So the helper can only ever fail toward `True`.

There is no way for a user to discover this. `.game-of-cards/config.yaml`
is user-owned, hand-edited, and never validated — `goc validate` walks card
frontmatter, not config values — so nothing prints, nothing exits non-zero,
and the run proceeds with the opposite of what the file says.

The template the user copies documents the intent in prose and offers no
vocabulary at all (`goc/templates/game_of_cards/config.yaml:19-30`):

> State-change commands auto-commit by default so active-card claims and
> decision handoffs are visible to parallel agents. **Set false** to leave
> those mutations in the working tree unless a command is run with
> `--commit`.

"Set false" is the whole specification. A reader who writes `off` is right;
a reader who writes `disabled`, `none`, or a slipped `of` gets the feature
they were switching off, silently.

The asymmetry bites hardest on the two `default=False` keys, because there
the fallback does not merely ignore an instruction — it **manufactures an
opt-in the user never gave**:

```yaml
workflow:
  claim_push: nope        # reads as True → `goc status <card> active` pushes
```

`claim_push` is documented as off by default precisely "to preserve solo
workflows where pushes are user-driven"
(`goc/templates/game_of_cards/config.yaml:32-39`). An unrecognized scalar
arms it.

## Empirical evidence

`uv run python .game-of-cards/deck/misspelled-workflow-config-boolean-silently-turns-the-feature-on/reproduce.py`:

```
=== 1. _coerce_config_bool over YAML scalars ===
config value |    yaml_lite | default=True | default=False
------------------------------------------------------------
        true |         True |         True |          True
       false |        False |        False |         False
        True |         True |         True |          True
       False |        False |        False |         False
         yes |         True |         True |          True
          no |        False |        False |         False
          on |         'on' |         True |          True
         off |        'off' |        False |         False
          of |         'of' |         True |          True  <-- meant OFF, reads ON
           n |          'n' |         True |          True  <-- meant OFF, reads ON
        none |       'none' |         True |          True  <-- meant OFF, reads ON
        nope |       'nope' |         True |          True  <-- meant OFF, reads ON
    disabled |   'disabled' |         True |          True  <-- meant OFF, reads ON
    Disabled |   'Disabled' |         True |          True  <-- meant OFF, reads ON

=== 2. end-to-end through the CLI ===
claim_push: nope  -> push attempted: True   (documented default: off)
auto_commit: of   -> auto-committed: True, warned: False
auto_commit: off  -> auto-committed: False, warned: True   (control)

FAIL: unrecognized workflow-config scalars silently read as True.
  6 misspelling(s) meant OFF but coerced ON: of, n, none, nope, disabled, Disabled
  claim_push: nope armed the remote-push path
  auto_commit: of kept auto-commit on, with no warning
```

The control line is the point: the correctly spelled `off` disables
auto-commit *and* prints the warning, so the harness is measuring the
coercion and not some unrelated failure. The end-to-end `claim_push` run
reaches a real `git push` — in the throwaway probe repo it surfaces as
`push failed and fetch failed: fatal: 'origin' does not appear to be a git
repository`, which is the push attempt itself, not a guard.

## Why it matters

The reachability path is short and entirely ordinary: a human hand-edits
`.game-of-cards/config.yaml` — the file `goc install` ships expressly for
customization — and types a word the helper does not know. Nothing between
that keystroke and the behaviour change reads the value again.

Two distinct symptoms follow, and they fail in opposite directions:

- **`auto_commit` (default True).** The user is trying to *stop* goc from
  committing. `auto_commit_enabled` has a dedicated warning for exactly this
  configuration (`goc/engine.py:5189`) — "auto_commit is disabled but the
  deck is version-controlled" — and it is gated on `not enabled`, so on a
  misspelling it does not fire either. The user gets commits they asked to
  suppress *and* the reassurance of silence.
- **`claim_push` / `closure_on_integration` (default False).** The user is
  not opting in at all, and the engine opts them in. `claim_push` reaches
  the network on every claim; `closure_on_integration` makes `goc done`
  refuse to close until HEAD is reachable from `origin/main`
  (`goc/engine.py:5232-5236`), which reads as a broken `done` verb rather
  than as a config error.

This is the engine's own canonical config-boolean reader — the one the two
open hook-side cards
[`pattern-generalization-opt-out-regex-misses-quoted-yaml-values`](../pattern-generalization-opt-out-regex-misses-quoted-yaml-values/)
and its closed sibling
[`pattern-generalization-hook-enable-regex-misses-capitalized-and-yes-yaml-booleans`](../pattern-generalization-hook-enable-regex-misses-capitalized-and-yes-yaml-booleans/)
would converge on if the hooks ever stopped reading config with a regex
(the pull named by
[`openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting`](../openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting/)).
Fixing the root before anything converges on it is cheaper than fixing it
after. Distinct from
[`load-deck-config-crashes-on-non-mapping-config-yaml`](../load-deck-config-crashes-on-non-mapping-config-yaml/),
which guards the *shape of the document*; this is the *value inside a
well-formed mapping*.

## The engine already has a policy for this — in the sibling reader

`_coerce_config_bool` is not the only place goc reads a user-authored value
out of `.game-of-cards/config.yaml`. `get_skills_source`
(`goc/engine.py:5392-5404`) does the same job for the `skills_source` key,
and it states the policy for an unrecognized value outright:

```python
def get_skills_source() -> str:
    """Return the configured `skills_source` value, or 'auto' if absent/invalid.

    Invalid values fall back to 'auto' silently — the config is meant to be
    forward-compatible.
    """
    value = load_deck_config().get("skills_source")
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in SKILLS_SOURCE_VALUES:
            return normalized
    return DEFAULT_SKILLS_SOURCE
```

Same file, same "read a hand-edited value" job, same unrecognized-input
question — and the answer is **fall back to the declared default**, with a
recorded rationale (forward-compatibility). `_coerce_config_bool` is the
outlier: it is the only config reader in the module that discards the
caller's declared default and substitutes Python truthiness.

That is what narrows the decision below. This is not a greenfield policy
choice; it is one reader disagreeing with its own sibling.

## Decision required

The direction is settled by the precedent above — the fallback becomes the
caller's `default`, not `bool(value)`. Two options are therefore recorded
as **rejected**, and the open question is a narrow one.

**Rejected — refuse and exit.** Print
`ERROR: .game-of-cards/config.yaml: workflow.claim_push: 'nope' is not a boolean`
and `sys.exit(2)`. It matches how goc treats invalid *card* fields and CLI
flags, but not how it treats config: `load_deck_config` is read by nearly
every verb, so one typo would brick the whole CLI — including the `goc show`
the user would run to diagnose it. `get_skills_source` already declined this,
and the closed card
[`load-deck-config-crashes-on-non-mapping-config-yaml`](../load-deck-config-crashes-on-non-mapping-config-yaml/)
moved deliberately away from hard failure on a malformed config.

**Rejected — widen the recognized false vocabulary** (add `n`, `none`,
`disabled`, …) and keep truthiness for the rest. It treats the symptom as a
missing-synonyms problem, leaves the fallback direction unfixed, and the
enumeration is exactly the shape that
[`frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`](../frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting/)
records as drift-prone.

**Open: silent, or warn once on stderr?** `get_skills_source` is silent and
says so on purpose. But the two readers are not quite symmetric:

- *Silent* is the literal precedent, and keeps a config typo from spraying
  stderr into every autonomous-loop transcript.
- *Warn once* fits `auto_commit` specifically, where falling back to the
  declared default means falling back to `True` — the user misspelled their
  way out of auto-commit and still gets commits. This exact function's
  caller already carries a warn-once-and-carry-on shape for the neighbouring
  case (`goc/engine.py:5186-5192`), as do
  `_enforce_closure_on_integration_or_exit`'s fetch and merge-base
  fallbacks. A `_warned_keys` set would keep it to one line per key per run.

Whichever is picked, a warn path needs the key name, which
`_coerce_config_bool` does not currently receive — so the decision also
settles whether the three call sites (`goc/engine.py:5185`, `:5156`,
`:5210`) pass a label in, or whether the reader moves up into
`load_deck_config` and validates the whole `workflow` block at load time.

If the answer is "silent, matching `get_skills_source`", the fix collapses
to a one-line change at `goc/engine.py:5093` with no call-site churn, and
this card is mechanical from there.

## Fix sketch (pending the decision above)

Replace the `return bool(value)` fallback at `goc/engine.py:5093` with
`return default`, plus the warn branch if that is the pick — threading a
`key: str` parameter through the three call sites only in that case, so the
message can name `workflow.<key>`. Non-string, non-bool values take the same
branch: today a list or a mapping also rides Python truthiness, and
`get_skills_source`'s `isinstance(value, str)` guard is the shape to mirror.
Then state the accepted spellings in
`goc/templates/game_of_cards/config.yaml` beside `auto_commit` so the
vocabulary is discoverable from the file the user is editing.

## Fix sketch (pending the decision above)

Replace the `return bool(value)` fallback at `goc/engine.py:5093` with the
chosen branch, threading a `key: str` parameter through the three call
sites so the message can name `workflow.<key>`. Non-string, non-bool values
take the same branch — today a list or a mapping also rides Python
truthiness. Then state the accepted spellings in
`goc/templates/game_of_cards/config.yaml` beside `auto_commit` so the
vocabulary is discoverable from the file the user is editing.
