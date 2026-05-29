---
title: goc-move-leaves-cross-reference-rewrites-uncommitted
summary: "`goc move OLD NEW` stages the directory rename via `git mv` but never auto-commits the cross-reference rewrites it performs across the repo or the `## ...: renamed from <old>` log entry it appends to the renamed card. HEAD does not advance, and `git status` shows mixed staged-rename + unstaged-modifications. Every other state-mutation verb (status, decide, advance, unadvance, wait) auto-commits by default and exposes `--commit` / `--no-commit`; `move` exposes neither and never commits."
status: open
stage: null
contribution: medium
created: "2026-05-29T20:18:30Z"
closed_at: null
human_gate: decision
advances:
  - goc-repair-edges-apply-leaves-edge-repairs-uncommitted
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `deck/<title>/reproduce.py` exits zero — after `goc move OLD NEW` on a fixture where another card cross-references `OLD`, HEAD advances and `git status --short` is clean.
  - [ ] PROCESS: decide fix path — add `--commit` / `--no-commit` flags + a single `_git_auto_commit` call that captures the rename, the cross-reference rewrite, and the renamed-from log entry; or document `goc move` as an intentional stage-only verb that requires a follow-up commit (and surface that requirement in the success message). Record reasoning in log.md.
  - [ ] TDD: regression test in `tests/` exercises the chosen behavior end-to-end (both the in-git path and the `shutil.move` fallback path).
  - [ ] MECHANICAL: `goc validate` clean across the deck; plugin mirrors regenerated; pre-commit clean.
  - [ ] PROCESS: sweep the remaining engine verbs for the same shape (only `_cmd_new` and `_cmd_repair_edges` remain on the meta-fix list once this card and its predecessors close); update the meta-fix family's parent card or close-out note.
---

# `goc move` leaves cross-reference rewrites uncommitted

## Location

- `goc/engine.py:2697-2703` — `move` subparser. No `--commit` /
  `--no-commit` flags (every other state-mutation verb pair has them).
- `goc/engine.py:4487-4544` — `_cmd_move`. Calls `git mv` (which
  stages the directory rename), then `_move_rewrite_tracked_files`
  (which mutates tracked text files across the repo with no staging),
  then appends a `## <iso>: renamed from <old>` entry to the renamed
  card's `log.md` — and returns without calling `_git_auto_commit`.
- `goc/engine.py:4458-4468` — `_move_rewrite_tracked_files`. Iterates
  every tracked text file from `git ls-files`, applies the rewrites,
  and writes them back in place. No `git add` follows.

## What's broken

Every other state-mutation verb in the engine auto-commits by default
and exposes a `--commit` / `--no-commit` pair. The advance verb is
representative (`engine.py:4382-4400`):

```python
def _cmd_advance(args):
    ...
    _mutate_pair(title, advancer, "advanced_by", "advances", add=True)
    print(f"advance: {title}.advanced_by += {advancer}; {advancer}.advances += {title}")
    commit_policy = _commit_override(commit, no_commit)
    if auto_commit_enabled(commit_policy):
        if _git_auto_commit([DECK_DIR / title, DECK_DIR / advancer], f"deck: {advancer} advances {title}"):
            print("  committed")
```

`_cmd_move` ends without that block:

```python
def _cmd_move(args):
    ...
    try:
        subprocess.run(["git", "mv", str(src), str(dst)], cwd=REPO_ROOT, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        shutil.move(str(src), str(dst))

    # Repo-wide text rewrite: H1s, markdown links, path forms, bare slugs,
    # frontmatter title/advances/advanced_by fields.
    _move_rewrite_tracked_files(old_title, new_title)

    now = _utc_now_iso()
    log_path = dst / "log.md"
    existing = log_path.read_text() if log_path.exists() else ""
    sep = "\n\n" if existing.strip() else ""
    log_path.write_text(existing.rstrip("\n") + sep + f"## {now}: renamed from {old_title}\n")

    print(f"{old_title} → {new_title}")
```

Result on a fixture where `foo.advanced_by: [bar]` and we run `goc
move bar bar-renamed` — `git status --short` reports:

```
RM .game-of-cards/deck/bar/README.md -> .game-of-cards/deck/bar-renamed/README.md
RM .game-of-cards/deck/bar/log.md -> .game-of-cards/deck/bar-renamed/log.md
 M .game-of-cards/deck/foo/README.md
```

The `RM` lines mean the rename is staged but the renamed files have
unstaged content modifications on top — the renamed-from `log.md`
entry and (when the card body referenced the old slug) the body
rewrite. The ` M` line is the cross-reference rewrite in `foo` that
`_move_rewrite_tracked_files` left in the working tree. HEAD does
not advance.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-move-leaves-cross-reference-rewrites-uncommitted/reproduce.py`
prints the verbatim `git status --short` and a side-by-side with
`goc advance`, which IS expected to auto-commit. See the script.

## Why it matters

`goc move` is reachable from any of three places that mutate the deck
on behalf of an agent: hand-typed by a human cleaning up a title, the
`Skill(refine-deck)` retitle suggestion path, and the migration
tooling (`--allow-jargon`). In every path the operator's mental model
is the same as for `goc advance` and `goc status` — "the verb
finishes a unit of work and commits it." The asymmetry means:

- A parallel agent's next auto-committing verb (e.g. `goc advance` on
  an unrelated card) may silently bundle the move's rewrites into its
  commit, attributing the rename to the wrong card and breaking the
  one-card-per-commit invariant the rest of the engine maintains.
- The human reviewing the eventual commit sees a rename without the
  reverse-edge rewrites or the `renamed from` log entry, *or* sees
  both bundled into an unrelated change. Either side of that split
  is a review-time surprise.
- `pre-commit run --all-files` (which runs the asset sync and `goc
  validate`) may pick up the half-state on its next invocation and
  attempt to "fix" the orphan rewrites under a different author.

This is the third instance of the same family — `goc new --advances`
and `goc repair-edges --apply` already have cards filed under
`api-contract,meta-fix` tags. The predecessor card
`goc-repair-edges-apply-leaves-edge-repairs-uncommitted` explicitly
anticipated this one in its DoD ("sweep `_cmd_move` for the same
shape"); this card closes that sweep item.

## Reachability

The producer is `_cmd_move` itself — there is no upstream that hands
it pre-mutated state. Reachability is direct: any caller of `goc move
OLD NEW` whose card or cross-references are non-trivial reaches the
defect on the first invocation. Confirmed locally on 2026-05-29
against this repo's own engine via the reproduce script.

## Decision required

Two credible fix paths. Both close the asymmetry; they differ on
where the commit boundary lands.

**Option A — symmetric auto-commit (matches the family).** Add
`--commit` / `--no-commit` to the `move` subparser; after the rewrite
phase, call `_git_auto_commit` with the list of `card_dirs` to
include (`dst`, plus any deck directory containing a cross-reference
hit returned by `_move_rewrite_tracked_files`). Message
`deck: rename OLD → NEW`. Same shape as `advance` / `unadvance` /
`status` — the operator's mental model holds.

**Option B — stage-only with explicit follow-up.** Document `move`
as an intentional stage-only verb (rationale: cross-reference
rewrites can hit any tracked text file in the repo, including
non-deck files where the operator may want to inspect the rewrite
before committing). Change `_cmd_move` to `git add` the rewritten
files so `git status` shows everything staged (no `M` lines), and
print a final `Run \`git commit\` to finalize.` hint instead of
exiting silently. This preserves the operator's chance to review
non-deck-file rewrites — which Option A would commit unreviewed.

The recommendation should weigh `move-rewrites-card-slug-inside-urls-paths-and-code-identifiers`
(the over-broad rewrite already on the queue): Option A makes that
defect louder (auto-commits the false-positive rewrites); Option B
keeps the review checkpoint that catches them. If
`move-rewrites-card-slug-inside-urls-paths-and-code-identifiers`
closes first with a tighter boundary class, Option A becomes the
clear pick.

## Fix sketch (under Option A)

In `_build_parser` near the `move` subparser:

```python
p_move.add_argument("--commit", action="store_true",
                    help="Force auto-commit for this rename.")
p_move.add_argument("--no-commit", action="store_true",
                    help="Skip auto-commit for this rename.")
```

In `_cmd_move`, after the rewrite phase and log append:

```python
commit_policy = _commit_override(args.commit, args.no_commit)
if auto_commit_enabled(commit_policy):
    rewrite_dirs = _move_collect_rewrite_dirs(old_title, new_title)
    if _git_auto_commit([dst, *rewrite_dirs], f"deck: rename {old_title} → {new_title}"):
        print("  committed")
```

`_move_collect_rewrite_dirs` is a new helper that returns the
deduplicated set of card directories where rewrites landed (so
`_git_auto_commit`'s pathspec covers every modified card).
