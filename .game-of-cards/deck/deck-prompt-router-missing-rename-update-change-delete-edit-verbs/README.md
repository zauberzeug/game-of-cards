---
title: deck-prompt-router-missing-rename-update-change-delete-edit-verbs
summary: "The shipping `deck_prompt_router.py` WORK_INITIATING list is missing the edit verbs `rename | update | change | delete | remove | move`, so prompts like `rename the button to Export` no longer fire the GoC reminder — the exact failure mode the closed card `prompt-hook-misses-rename-work-requests` (done 2026-05-05) claimed to have fixed. Root cause is a stale-tree merge: commit 33d000a (2026-05-05 08:27) introduced `deck_prompt_router.py` as a fresh copy of an older `user-prompt-submit.py` version, and commit 14864cc (2026-05-05 22:56) then added the rename verbs to the now-orphaned `user-prompt-submit.py`. Commit 8277962 (2026-05-09) deleted the orphan, taking the fix with it. The closed card's DoD never re-checked the renamed file."
status: open
stage: null
contribution: high
created: "2026-05-30T02:15:24Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the canonical AGENTS examples (`rename the button to Export`, `add a CSV export`, `fix the auth bug`) AND four sibling edit verbs (`update the timeout to 30s`, `change the default port`, `delete the legacy module`, `move the helper to utils/`) all fire the GoC reminder.
  - [ ] TDD: existing regression cases stay green — exploration prompts that today are silent (`we should review the recent commits`) remain silent.
  - [ ] MECHANICAL: the same verb additions land in the OpenClaw plugin's TypeScript port at `openclaw-plugin/index.ts` so the three-host parity is restored.
  - [ ] MECHANICAL: `python scripts/sync_plugin_assets.py --check` clean (the hook file ships in three plugin payloads + the `.claude/hooks/` dogfood copy).
  - [ ] PROCESS: amend the closed card `prompt-hook-misses-rename-work-requests` with a forward pointer to this card per AGENTS.md's "Closure is not frozenness" rule — append to its `log.md` documenting the regression and the date.
---

# `deck_prompt_router` WORK_INITIATING list is missing rename/update/change/delete/remove/move

## Location

- `goc/templates/hooks/deck_prompt_router.py:16-26` — current WORK_INITIATING list:

  ```python
  WORK_INITIATING = [
      r"\blet'?s\s+(do|build|implement|make|add|create|fix|introduce|write|refactor)\b",
      r"\b(implement|build|introduce|refactor)\s+\w",
      r"\b(fix|add|create|write)\s+(a|an|the|this|that|some)\b",
      r"\bi\s+(want|need)\s+(to|a|an|the|this)\b",
      r"\bwe\s+(need|should|want)\s+to\b",
      r"\bcan\s+you\s+(add|fix|build|create|implement|introduce|write)\b",
      r"\bplease\s+(add|fix|build|create|implement|introduce|write)\b",
      r"\bmake\s+it\s+(work|do|so|happen)\b",
      r"\bship\s+(it|this|the)\b",
  ]
  ```

  Patterns 1, 3, 6, and 7 are the four locations where the closed-card fix
  added `rename|update|change|delete|remove|move`. None of those verbs
  appear in the current file.

- `goc/templates/AGENTS_GOC.md` — agent guidance presents
  `rename the button to Export` as a canonical persistent-work example.
  The hook must classify that prompt as work for the documentation claim
  to hold.

## What's broken (and how it got broken)

Reading the file as it stands, "rename the button to Export" trips none
of the nine WORK_INITIATING patterns:

| pattern | match? |
|---|---|
| `let's (do\|build\|...) ` | no — no `let's` prefix |
| `(implement\|build\|introduce\|refactor) \w` | no — wrong verb |
| `(fix\|add\|create\|write) (a\|an\|the\|...)` | no — wrong verb |
| `i (want\|need) (to\|a\|...)` | no — no `I` prefix |
| `we (need\|should\|want) to` | no — no `we` prefix |
| `can you (add\|fix\|...)` | no — no `can you` prefix |
| `please (add\|fix\|...)` | no — no `please` prefix |
| `make it (work\|...)` | no — `make` not at start |
| `ship (it\|this\|the)` | no — wrong verb |

`has_work` is False, line 75 doesn't print the reminder, the hook stays
silent. The agent never gets the GoC pipeline prompt for a textbook
work request.

### Root cause: stale-tree merge of two parallel fixes

Git history (verified with `git log --all --diff-filter=AR --name-status -- 'goc/templates/hooks/*'`):

| commit | date (UTC) | action |
|---|---|---|
| `7ce2b72` | earlier | created `goc/templates/hooks/user-prompt-submit.py` with the original (broken) WORK_INITIATING list |
| `33d000a` | 2026-05-05 08:27 | created `goc/templates/hooks/deck_prompt_router.py` as a **fresh new file** (status `A`, not `R`) carrying the original list verbatim; orphaned `user-prompt-submit.py` from any wiring |
| `14864cc` | 2026-05-05 22:56 | added `rename\|update\|change\|delete\|remove\|move` to the WORK_INITIATING list — **but on the now-orphaned `user-prompt-submit.py`**, not on the new `deck_prompt_router.py` |
| `8277962` | 2026-05-09 | deleted the orphaned `user-prompt-submit.py` ("hadn't been wired to anything since deck_prompt_router.py replaced [it]") — the rename-fix went with it |

The closed card `prompt-hook-misses-rename-work-requests` (closed
2026-05-05) cites the file `goc/templates/hooks/user-prompt-submit.py`
and reports its reproducer passing. The reproducer ran against the
orphaned file — by then no longer the file Claude installs actually
invoked. The card's DoD did not re-verify against the canonical hook
path (`deck_prompt_router.py`), so the regression slipped through
attestation.

## Empirical evidence

`uv run python .game-of-cards/deck/deck-prompt-router-missing-rename-update-change-delete-edit-verbs/reproduce.py`:

```text
Probing goc/templates/hooks/deck_prompt_router.py with 7 prompts:

  [BUG] work: rename — fires=False (want=True): "rename the button to Export"
  [BUG] work: update — fires=False (want=True): "update the timeout to 30s"
  [BUG] work: change — fires=False (want=True): "change the default port"
  [BUG] work: delete — fires=False (want=True): "delete the legacy module"
  [BUG] work: move   — fires=False (want=True): "move the helper to utils/"
  [OK]  work: add    — fires=True  (want=True): "add a CSV export"
  [OK]  work: fix    — fires=True  (want=True): "fix the auth bug"

DEFECT: 5 edit-verb prompt(s) silently classified as non-work.
```

Five of seven canonical edit-style work prompts get no reminder.

## Why it matters

The previously-closed card established that **silently treating edit
work as non-work is the worse failure mode**: an agent that doesn't see
the reminder may skip the deck pipeline entirely and execute against an
unfiled card, defeating the read-pattern guarantee the whole runtime
exists to enforce. The AGENTS.md guidance promises the agent will catch
these prompts; today it doesn't.

Reachability: every plugin-payload and dogfood Claude install runs this
hook on every UserPromptSubmit event. The prompts most affected are the
day-to-day edit verbs (`rename`, `update`, `change`, `delete`, `remove`,
`move`) — i.e. the most common kinds of work requests.

## Decision required

Two reasonable fix paths.

1. **Restore the closed-card fix verbatim on `deck_prompt_router.py`.**
   Re-apply the `14864cc` diff to the new filename. Adds the six verbs to
   the three pattern locations (patterns 1, 3, 6 — pattern 7 `please …`
   too). Smallest possible diff; keeps WORK_INITIATING's structure intact.

2. **Refactor WORK_INITIATING to a shared `WORK_VERBS` constant.** Same
   semantics, but extract `WORK_VERBS = r"(add|fix|build|create|write|
   implement|refactor|introduce|rename|update|change|remove|delete|move
   |ship|extract)"` and reference it from every pattern. Makes the next
   "you missed verb X" miss a one-line fix and lets the TypeScript port
   in `openclaw-plugin/index.ts` mirror the same constant. Slightly
   bigger diff; reduces the chance of a third regression by collapsing
   four edit sites into one.

Option 2 is the meta-fix path — it removes the maintenance shape that
caused the original miss. Option 1 is the literal "restore the closed
card's fix" path.

### Sibling defect (separately filed)

The same WORK_INITIATING list is also mis-tuned in the **opposite**
direction — pattern 4 (`i (want|need) (to|a|an|the|this)`) matches purely
exploratory prompts like `I want to understand X`. Tracked as
[deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts](../deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts/).
A single coordinated rewrite of WORK_INITIATING (option 2 above) can
fix both, but the two cards stay separate because the decision-required
trade-offs differ (over-fire vs under-fire, conservative whitelist vs
liberal whitelist).
