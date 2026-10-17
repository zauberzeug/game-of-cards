---
title: reproduce-py-recipe-crashes-in-repos-without-a-pyproject-toml
summary: "FIXED: the reproduce.py repo-root recipe that Skill(create-card) ships to every consuming repo walked up to the nearest pyproject.toml, while the engine finds the project root by the nearest .game-of-cards/ directory. In a repo without a pyproject.toml (JS/TS, Go, Rust, the Node-based OpenClaw ecosystem) the recipe raised RuntimeError; in a repo nested inside a workspace whose parent has one, it silently returned the workspace. Step 6 now walks to .game-of-cards/ in code, error message and prose, and tests/test_reproduce_recipe_root.py runs the shipped recipe in fixture repos against _walk_to_deck_root."
status: done
stage: null
contribution: medium
created: "2026-10-16T04:52:10Z"
closed_at: "2026-10-17T04:31:32Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — the recipe extracted from the shipped template resolves the engine's project root in all four fixtures (JS repo, Go repo, repo nested in a pyproject workspace, Python repo).
  - [x] TDD: a regression test runs the recipe extracted from `goc/templates/skills/create-card/SKILL.md` in fixture repos and asserts it prints the same root as `goc.engine._walk_to_deck_root`; fed the pre-fix `pyproject.toml` recipe verbatim, the same check fails, so the guard is proven able to fire.
  - [x] MECHANICAL: Step 6 of `goc/templates/skills/create-card/SKILL.md` keys the walk on `.game-of-cards/` — the marker the engine walks to — in the code, the error message, and the prose around it; the generated mirrors are regenerated (`python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` green).
  - [x] PROCESS: the meta card's instance list gains this card's row (guard class, close date) and its `log.md` an entry; `uv run goc validate` clean; full `unittest` suite green.
worker: {who: "claude[bot]", where: main}
---

# The shipped reproduce.py recipe crashes in repos without a pyproject.toml

## Location

- `goc/templates/skills/create-card/SKILL.md:183-205` — Step 6, the
  repo-root recipe every bug-class `reproduce.py` is told to start with.
  Generated copies ship in `claude-plugin/skills/`, `codex-plugin/skills/`,
  `openclaw-plugin/skills/` and every vendored `.claude/skills/`.
- `goc/engine.py:150-166` — `_walk_to_deck_root`, the walk every goc verb
  uses to find the same project.

## What was broken

Step 6 told the author to find the repo root with the "parent-walk
pattern" and shipped this block for agents to copy:

```python
def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")
```

`pyproject.toml` is this repo's marker, not goc's. goc ships to repos of
any language, and the engine defines the project root differently — by
the directory goc itself installs:

```python
# goc/engine.py:162-163 (_walk_to_deck_root)
        if (candidate / ".game-of-cards").is_dir():
            return candidate
```

So the recipe and the engine disagreed whenever the nearest
`pyproject.toml` is not the directory holding `.game-of-cards/`:

1. **No `pyproject.toml` at all** — a JS/TS, Go or Rust repo, or any repo
   in the Node-based OpenClaw ecosystem the goc OpenClaw plugin targets.
   The walk reaches `/` and raises, so the first run of every evidence
   script the skill asks for is a traceback the author has to debug.
2. **A `pyproject.toml` above the project** — a repo checked out inside a
   workspace or monorepo whose root carries one. The walk passes the
   project and returns the workspace, with no error. `sys.path.insert`
   then puts the wrong tree first on the import path, and any path the
   script builds from the root points into the wrong tree.

The recipe was written when it served only this repo's own deck, which
has a `pyproject.toml` at the root, and it shipped unchanged with the
first packaged skill templates (`94975556`). A grep of `goc/templates/`
finds no other site with this marker: the `pyproject.toml` checks in
`_goc-bootstrap.sh` and `codex-kickoff` deliberately detect the goc
source repo itself.

## Empirical evidence

`uv run python .game-of-cards/deck/reproduce-py-recipe-crashes-in-repos-without-a-pyproject-toml/reproduce.py`
extracts the recipe from the template verbatim, writes it into fixture
repos as `.game-of-cards/deck/some-bug/reproduce.py`, runs it, and
compares its answer with `_walk_to_deck_root` on the same directory.

Before the fix (exit 1):

```text
[FAIL] JS repo (package.json, no pyproject.toml)
       engine root : <tmp>/app
       recipe says : CRASH: RuntimeError: repo root (pyproject.toml) not found
[FAIL] Go repo (go.mod, no pyproject.toml)
       engine root : <tmp>/app
       recipe says : CRASH: RuntimeError: repo root (pyproject.toml) not found
[FAIL] repo nested in a workspace whose root has pyproject.toml
       engine root : <tmp>/app
       recipe says : <tmp>
[OK] Python repo (pyproject.toml at the repo root)
       engine root : <tmp>/app
       recipe says : <tmp>/app

3 of 4 fixtures: the shipped recipe disagrees with the engine's root
```

After the fix (exit 0):

```text
[OK] JS repo (package.json, no pyproject.toml)
       engine root : <tmp>/app
       recipe says : <tmp>/app
[OK] Go repo (go.mod, no pyproject.toml)
       engine root : <tmp>/app
       recipe says : <tmp>/app
[OK] repo nested in a workspace whose root has pyproject.toml
       engine root : <tmp>/app
       recipe says : <tmp>/app
[OK] Python repo (pyproject.toml at the repo root)
       engine root : <tmp>/app
       recipe says : <tmp>/app

0 of 4 fixtures: the shipped recipe disagrees with the engine's root
```

## Why it matters

`reproduce.py` is the evidence a bug card's DoD turns on:
`Skill(finish-card)` re-runs it before closing, and `Skill(audit-deck)`
won't file a behavioral defect without one. The recipe is a procedure
agents follow literally. In a non-Python consumer repo the first output
is a crash, which a careful agent patches by hand and a hurried one
reports as "reproduce.py fails". In the workspace case nothing fails: a
script rooted one level too high can import a different checkout of the
package or read the wrong files, and still exit 0. Evidence that passes
for the wrong reason is worse than evidence that crashes.

This is another instance of the family catalogued in
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/):
shipped guidance restating something the tree defines, here which
directory is the project root, without a guard tying it to that
definition. Like that card's fourteenth instance, the restatement is a
procedure, so it can only be guarded by running it against a fixture.
The closest sibling is
[card-schema-reference-links-to-a-deck-card-no-consumer-repo-has](../card-schema-reference-links-to-a-deck-card-no-consumer-repo-has/):
a shipped surface that assumes the consuming repo is this one.

## What changed

- `goc/templates/skills/create-card/SKILL.md` Step 6: the walk keys on
  `.game-of-cards/` (`is_dir()`), the error message names that marker, and
  the prose asks for "the repo root holding `.game-of-cards/`". The marker
  is the engine's own definition, not a taste call. The prose stays one
  clause because the skill sat 16 bytes under its hot-path cap in
  `tests/test_skill_body_size.py`; the why lives on this card. The four
  generated copies
  (`.claude/`, `.codex/`, `claude-plugin/`, `codex-plugin/`) are re-synced
  and `openclaw-plugin/skills/` is re-ported.
- `tests/test_reproduce_recipe_root.py`: `ShippedRecipeTest` extracts the
  python block after "parent-walk pattern" from the template and runs it in
  four fixture repos (JS, Go, a repo nested in a pyproject workspace,
  Python). It compares each answer with `_walk_to_deck_root` and checks that
  every shipped copy carries the template's recipe. `PreFixRecipeFiresTest`
  feeds the old `pyproject.toml` walk verbatim through the same check, which
  reports the JS, Go and workspace fixtures. So the guard is proven able to
  fire.

**Out of scope:** the `uv run python deck/<title>/reproduce.py` line under
the recipe. Its bare `deck/` path is tracked by the decision-gated
[shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates](../shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates/),
and this card does not pre-empt that choice. The existing reproduce.py
files in this repo's own deck keep the `pyproject.toml` walk. It is
correct here, and rewriting closed cards' evidence scripts would change
the record, not fix a defect.
