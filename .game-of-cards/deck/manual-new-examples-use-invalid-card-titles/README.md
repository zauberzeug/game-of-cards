---
title: manual-new-examples-use-invalid-card-titles
summary: "The README and CLI guide still show manual `goc new \"rename the button...\"` examples, but the command only accepts lower-kebab card slugs. New users following the advertised manual path hit a title-pattern error before creating their first card."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [documentation, api-contract]
definition_of_done: |
  - [x] `uv run python .game-of-cards/deck/manual-new-examples-use-invalid-card-titles/reproduce.py` exits zero
  - [x] README manual examples use valid lower-kebab titles or clearly route natural-language requests through the agent workflow
  - [x] `docs/cli.md` daily-command examples use valid lower-kebab titles (file removed; no invalid examples)
  - [x] A focused docs regression prevents quoted `goc new` examples with spaces from returning to README/docs
---

# manual-new-examples-use-invalid-card-titles

## Location

- `README.md:19`
- `README.md:66`
- `README.md:116`
- `docs/cli.md:83`
- `goc/engine.py:1626`

## What's broken

The README and CLI guide advertise natural-language titles as direct
`goc new` arguments:

```markdown
goc new "rename the button to Export"
```

But `goc new` enforces the schema title pattern directly:

```python
if not re.match(schema.title_pattern, title):
    click.echo(f"ERROR: title {title!r} does not match {schema.title_pattern!r}", err=True)
    sys.exit(2)
```

Running the advertised form fails:

```text
ERROR: title 'rename the button' does not match '^[a-z0-9][a-z0-9-]*[a-z0-9]$'
```

## Empirical evidence

Current output from `uv run python deck/manual-new-examples-use-invalid-card-titles/reproduce.py`:

```text
invalid_doc_examples=4
README.md:19: It works without any of that, too. `goc new "rename the button"`, `goc` to see what's open, `goc done rename-the-button` to close it. No AI required. The deck is just markdown files; you read, write, edit, and revert them with the same git you already use.
README.md:66: goc new "rename the button to Export"
README.md:116: This repo uses Game of Cards to track its own work. The `deck/` directory is the backlog; each card is a directory under that with a frontmatter-validated `README.md` and an append-only `log.md`. If you want to contribute to existing work, pick an open card and update that card as part of your change. If you want to propose new work, run `uv run goc new "card title"` to scaffold the card directory.
docs/cli.md:83: goc new "rename the button to Export"
advertised_shape_exit=2
advertised_shape_stderr=ERROR: title 'rename the button' does not match '^[a-z0-9][a-z0-9-]*[a-z0-9]$'
defect present: docs advertise a goc new title shape the CLI rejects
```

## Why it matters

The docs correctly make agent prompting the primary interface, but they
still present CLI snippets as the manual equivalent and debug path. The
first manual card command should work when pasted. Right now it teaches
a command shape that the CLI rejects.

The older
[`readme-starter-card-and-doc-polish-session`](../readme-starter-card-and-doc-polish-session/)
card noticed this pattern as evidence while reshaping onboarding, but
the invalid examples remain in the current README and CLI guide.

## Fix

Use valid slugs in direct CLI examples, for example:

```bash
goc new rename-the-button-to-export
```

For natural-language examples, keep them as agent prompts:

```text
"create a card for renaming the export button"
```

Add a small docs regression that fails when README/docs contain
`goc new "<text with spaces>"`.
