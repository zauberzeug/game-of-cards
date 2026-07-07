---
name: upgrade
description: Run goc upgrade, then drive LLM reconciliation of evolving .game-of-cards/ files from the engine's divergence report, preserving user-owned content. AUTO-INVOKE on "upgrade goc", "run goc upgrade", "sync goc templates".
---

## When to invoke

Invoke when the user says "upgrade goc", "pull the latest goc", "sync goc templates", "run goc upgrade", or asks how to upgrade the GoC version in this repo. The engine's safety guarantee — never overwrite authored project state — holds with or without this skill; the skill exists to reconcile *evolving* upstream content into the local copy where the engine's "preserve" verdict alone leaves real upstream changes on the floor.

# Upgrade GoC

`goc upgrade` is deterministic and safe by construction — it never
overwrites authored content under `.game-of-cards/`. That guarantee
holds for every consumer regardless of whether an agent is present
(headless CI runs, scheduled cron, scripted upgrades).

But "never overwrite" is not the same as "stay current". Two files
under `.game-of-cards/` ship real, evolving content that the upstream
template may have changed across versions:

- `README.md` — the hook-point catalogue documenting which content
  stubs and workflow hooks the skills consume, and where.
- `config.yaml` — the runtime-neutral closure attestation config
  (`layer_2_project_dod`, `layer_3_goc_dod`) plus workflow options.

If the engine has preserved a *diverged* copy of either, the engine
itself has nothing to say about whether real upstream changes need to
land in the consumer's local copy. **That is this skill's job.**

For the 12 user-owned content stubs and workflow hooks, the engine's
"preserved" verdict is the whole story — the templates ship blank by
design, so there is nothing to reconcile. This skill confirms that to
the user so they know nothing was lost.

For the `AGENTS.md` / `CLAUDE.md` GoC marker block, the engine
regenerates the goc-owned region wholesale via the marker-bounded
merge (`<!-- BEGIN GOC vX.Y.Z -->` … `<!-- END GOC -->`). That region
is goc-owned, not user-owned, so nothing to reconcile — this skill
summarizes what methodology guidance changed across the upgrade so
the user knows what new behavior the agents will now follow.

## Workflow

1. **Run `goc upgrade` and capture stdout.** The engine emits a
   sentinel-marked JSON divergence report after its normal upgrade
   output:

   ```
   GoC project-state divergence report (JSON):
   {"version": 1, "templates_root": "...", "files": [...]}
   ```

   Parse the JSON on the line immediately following the marker. Each
   entry has `path` (relative to `.game-of-cards/`), `status`
   (`create` / `unchanged` / `preserved`), and `ownership`
   (`user-owned` / `evolving`).

2. **For each `evolving` file with `status: preserved`** — read the
   local file at `.game-of-cards/<path>` AND the shipped template at
   `<templates_root>/<path>`. Drive a 2-way reconcile:

   - Diff the two files mentally. Identify what changed *upstream*
     (lines present in the template that are absent or different in
     the local copy).
   - For each upstream change, decide whether it should land:
     - **Mechanical updates** (new key with default value, new
       comment, new doc paragraph that does not contradict local
       customization) → propose the merged content and `AskUserQuestion`
       for confirmation.
     - **Conflicting with the user's customization** → describe both
       sides and ask the user how to resolve. Default to keeping the
       user's value; surface the upstream change as informational.
   - When the user approves, write the merged content back to
     `.game-of-cards/<path>` directly. Do not invoke `goc upgrade`
     again — the engine has already done its work; this is a one-shot
     reconciliation.
   - If the local file and template are obviously compatible (e.g.,
     local added a new top-level key the template doesn't know about,
     and the template added an unrelated comment), apply both sides
     and report the merged result.

3. **For each `user-owned` file with `status: preserved`** — confirm
   to the user, in one line per file: "kept your `<path>` (nothing
   upstream)". The shipped template is permanently blank by design,
   so there is no upstream content to bring across. The confirmation
   exists so the user does not have to wonder whether the upgrade
   silently overwrote anything.

4. **For files with `status: create`** — these are absent locally and
   were scaffolded by the engine. Mention them so the user knows new
   files appeared (e.g., a new workflow-hook stub for a skill that
   landed in this version).

5. **For files with `status: unchanged`** — silent. The local copy
   already matches the template; nothing to report.

6. **Summarize AGENTS.md / CLAUDE.md GoC block changes.** Diff the
   `<!-- BEGIN GOC vX.Y.Z -->` … `<!-- END GOC -->` region before and
   after the upgrade (the engine already rewrote it; `git diff` on
   the working tree surfaces the delta), and present a short list of
   substantive methodology changes — new verbs documented, new
   conventions enforced, behavioral defaults flipped. This is
   informational, not a merge — the marker-bounded region is
   goc-owned and the upgrade contract is that it gets regenerated.

7. **Commit follows repo policy.** If the reconciliation pass
   modified any files, the user typically wants those staged
   alongside the engine's own changes (the bumped `.goc-version`,
   the rewritten methodology block, any newly-scaffolded files). The
   engine's `goc upgrade` does NOT auto-commit; commit the union of
   engine writes + reconciliation edits with a subject like
   `chore(goc): upgrade to vX.Y.Z`.

## Why the engine is safe without this skill

The engine's `_sync_game_of_cards_config` classifies every shipped
file against the on-disk copy and only writes when the destination is
absent. Diverged files are preserved unconditionally — no prompt, no
confirmation, no agent in the loop. This means:

- A scripted upgrade in CI does not lose authored content.
- A scheduled cron `goc upgrade` does not lose authored content.
- A user running `goc upgrade` in a terminal without invoking this
  skill does not lose authored content.

What the user loses without this skill is *informational reconciliation*
of upstream changes to the two evolving files. The local copies stay
exactly as the user left them; the upstream changes sit in the
template payload until the next time someone runs this skill (or
manually diffs `.game-of-cards/README.md` against
`<templates_root>/README.md`).

## What this skill does NOT do

- Does NOT re-run `goc upgrade`. The engine has already done its
  work by the time this skill is reading the report. Re-running
  would be a no-op (version is now current).
- Does NOT overwrite user-owned content stubs or workflow hooks. The
  templates are blank by design — there is nothing upstream to
  bring across, so the reconcile pass for those files is purely a
  confirmation.
- Does NOT touch the `AGENTS.md` / `CLAUDE.md` GoC marker block.
  The engine regenerates that region wholesale on every upgrade; the
  contract is "do not edit between the markers."
- Does NOT bisect or `git revert` the engine's writes. If the
  reconciliation pass produces a result the user dislikes, the user
  edits the file by hand or invokes the `create-card` skill to file
  the disagreement as a card for follow-up.

## Cross-references

- the `kickoff` skill — first-time setup in a fresh repo. The kickoff
  skill writes the initial `.game-of-cards/` scaffold; this skill is
  the follow-up that runs every time the user wants to pull a new
  goc version into an existing repo.
- the `card-schema` skill — frontmatter and DoD conventions the upgraded
  engine may have evolved.
- the `deck` skill — the methodology surface the regenerated AGENTS.md /
  CLAUDE.md block documents.
