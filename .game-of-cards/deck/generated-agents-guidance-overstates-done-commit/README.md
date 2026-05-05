---
title: generated-agents-guidance-overstates-done-commit
summary: "Generated agent guidance still tells agents that closure commands close and commit, but the shipped finish-card contract and engine make `done` a non-committing closure-state flip. This can leave autonomous agents believing the closure landed in git when the final work commit is still required."
status: active
stage: null
contribution: high
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation, api-contract, infra]
definition_of_done: |
  - [ ] `goc/templates/AGENTS_GOC.md` no longer describes `goc done <title>` as the commit step
  - [ ] `goc/templates/hooks/user-prompt-submit.py` no longer describes `Skill(finish-card)` as "close + commit" without the separate final commit workflow
  - [ ] The repo-local generated `AGENTS.md` block is aligned with the corrected template wording
  - [ ] Any CLI/user-facing docs that mention closure keep `done` as DoD-gated state change and leave committing to finish-card/runtime workflow
  - [ ] A focused test or grep-based regression prevents generated guidance from reintroducing "Close + commit: `goc done <title>`" or "close + commit" as a single finish-card step
---

# generated-agents-guidance-overstates-done-commit

## Location

- `goc/templates/AGENTS_GOC.md:19`
- `goc/templates/AGENTS_GOC.md:70`
- `goc/templates/hooks/user-prompt-submit.py:55`
- `AGENTS.md:29`
- `AGENTS.md:80`
- `goc/templates/skills/finish-card/SKILL.md:179`
- `goc/engine.py:1286`

## What's broken

The generated shared agent guidance says the session-mode close step is also
the commit step:

```markdown
5. Close + commit: `goc done <title>`.
```

The generated daily-verb table repeats the same contract:

```markdown
| `goc done <title>` | Close + DoD enforcement + commit. |
```

The generated Claude prompt hook carries the same stale shortcut for the
skill-level close operation:

```text
5. Skill(finish-card) <title> — close + commit.
```

That contradicts the current finish-card contract:

```markdown
`done` does NOT auto-commit.
```

It also contradicts the engine implementation. `done()` mutates
`status` and `closed_at`, writes the README, and returns without calling
`_git_auto_commit`:

```python
def done(title, force):
    ...
    text = mutate_frontmatter_field(text, "status", "done")
    text = mutate_frontmatter_field(text, "closed_at", today)
    (card_dir / "README.md").write_text(text)
    click.echo(f"{title}: {prior} -> done")
```

## Evidence

The citation set above is the evidence: three generated guidance surfaces
claim commit behavior, while the shipped finish-card skill and engine say
the command is non-committing until the final runtime commit workflow.

`rg -n 'goc done <title>|Close \+ commit|done` does NOT auto-commit|def done\(' ...`
found the conflicting lines in `goc/templates/AGENTS_GOC.md`,
repo-local `AGENTS.md`, `goc/templates/hooks/user-prompt-submit.py`,
`goc/templates/skills/finish-card/SKILL.md`, and `goc/engine.py`.

## Why it matters

The AGENTS block is the cross-runtime operating contract. In autonomous
or session-mode work, an agent following it can run `goc done <title>`,
believe it has also committed the closure, and stop with a dirty
working tree. That directly undermines the deck's "work lands as commits"
handoff guarantee.

The drift appears to be fallout from
[`configurable-auto-commit`](../configurable-auto-commit/): that card
correctly scoped auto-commit to state-only coordination commands, but the
AGENTS template still carries the older shortcut wording.

## Fix

Update `goc/templates/AGENTS_GOC.md`,
`goc/templates/hooks/user-prompt-submit.py`, and the generated
repo-local `AGENTS.md` block so the session pipeline separates closure
from commit. For example:

```markdown
5. Close with `goc done <title>`, then commit the work and closure.
```

In the daily-verb table, describe `goc done <title>` as "Close + DoD
enforcement" without promising a commit.

Add a small regression assertion in the installer/guidance tests so the
template cannot reintroduce the stale phrase.
