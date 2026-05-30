---
title: emit-frontmatter-silently-strips-unknown-worker-sub-keys
summary: "`_emit_worker` writes only `who` and `where`; any other sub-keys present in a `worker:` mapping are silently dropped on every full frontmatter re-emit. `validate_card` accepts unknown sub-keys with no warning, so the round-trip through `goc wait` / `goc decide` / `goc migrate-list-style` is silent data loss. Forward-compatibility hazard: a future schema bump that adds `worker.since` or `worker.role` would have older `goc` binaries corrupt cards on the next mutating verb."
status: open
stage: null
contribution: medium
created: "2026-05-30T06:06:08Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: pick a fix path in the Decision-required section below — (A) tighten the validator to reject unknown worker sub-keys, OR (B) widen the emitter to preserve unknown sub-keys, OR (C) both (reject by default, opt-in preservation). Record the choice and reasoning in log.md.
  - [ ] TDD: reproduce.py exits zero (the chosen fix prevents silent drop OR raises an explicit error on the offending input).
  - [ ] TDD: a regression test in `tests/` covers a `worker: {who, where, <unknown-key>}` round-trip through `emit_frontmatter` and the chosen `goc` verb path.
  - [ ] MECHANICAL: `goc validate` clean; plugin mirrors synced; `tests/test_*` suite passes under `uv run python -m unittest discover -s tests`.
---

# `emit_frontmatter` silently strips unknown worker sub-keys

## Location

- Emitter: `goc/engine.py:272-288` (`_emit_worker`).
- Validator: `goc/engine.py:1224-1237` (`validate_card`, worker branch).
- Reachable from any full-emit verb that calls `emit_frontmatter(fm, body=body)`
  — e.g. `goc wait` at `goc/engine.py:4366`, `goc decide` at `goc/engine.py:4586`,
  `goc migrate-list-style` at `goc/engine.py:4821`, `goc move` at
  `goc/engine.py:4157`, `goc triage` at `goc/engine.py:4366`.

## What's broken

`_emit_worker` only reads `who` and `where` from the mapping:

```python
def _emit_worker(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return _yaml_inline(value)
    if isinstance(value, dict):
        who = value.get("who", "")
        where = value.get("where")
        if where:
            return f"{{who: {_yaml_inline(who)}, where: {_yaml_inline(where)}}}"
        return _yaml_inline(who)
    return _yaml_inline(str(value))
```

Anything else in the mapping — `since`, `role`, `gpu-id`, `claim-ts`, or any
key a future schema (or a project-local convention) might introduce — is
silently dropped on the next emit.

`validate_card` only checks that `who` is a non-empty string and (if present)
that `where` is a string. It does NOT reject unknown sub-keys:

```python
elif isinstance(worker, dict):
    if "who" not in worker:
        errors.append(f"{t.title}: worker: mapping must have a 'who' key")
    elif not isinstance(worker.get("who"), str) or not worker["who"]:
        errors.append(f"{t.title}: worker: 'who' must be a non-empty string")
    if "where" in worker and not isinstance(worker.get("where"), str):
        errors.append(f"{t.title}: worker: 'where' must be a string")
else:
    errors.append(f"{t.title}: worker: must be a string or mapping with 'who'")
```

This is an **accept-then-strip asymmetry**: the validator permits a shape the
emitter cannot preserve. Either tighten the validator or widen the emitter,
but not both as today.

The AGENTS.md note that `worker.who` may be "a capability tag (e.g.
`gpu-required`, `human`, `rendering-expert`)" and the unregistered
free-form contract of the field actively encourages project-local
extensions to the mapping. The current behavior makes any such extension a
silent landmine.

## Empirical evidence

`reproduce.py` (see sibling file) constructs a card with
`worker: {who: alice, where: feat/x, since: "2026-01-01", role: lead}`,
runs `goc wait <card> --reason external --no-commit`, and prints the
before/after `worker:` line.

```
$ uv run python .game-of-cards/deck/emit-frontmatter-silently-strips-unknown-worker-sub-keys/reproduce.py
before: worker: {who: alice, where: feat/x, since: "2026-01-01", role: lead}
after:  worker: {who: alice, where: feat/x}
DROPPED KEYS: ['role', 'since']
```

The validator accepts both shapes without warning:

```
$ uv run goc validate
... OK emit-frontmatter-silently-strips-unknown-worker-sub-keys
```

## Why it matters

Reachability — three concrete paths produce the offending input:

1. **Hand-authored cards.** AGENTS.md documents `worker.who` as a free-form
   identifier and explicitly invites capability tags; an author who reasons
   by analogy and adds `worker: {who: alice, since: "..."}` gets no
   diagnostic, then loses the key on the next `goc wait`.
2. **Project-local conventions.** A consuming repo could plausibly stash
   custom worker metadata (e.g. `gpu-id`, `pid`, `claim-ts`) via a hook;
   nothing in the validator says "don't."
3. **Forward-compat hazard.** If a future schema bump adds `worker.since` or
   `worker.role`, an older `goc` binary still installed in a consumer repo
   silently strips the new key on the next mutating verb. The consumer has
   no symptom until a downstream reader notices the missing field.

The data loss is silent: no warning, no log.md entry, no commit-message hint.
The first symptom is a downstream consumer noticing the missing key —
typically after the corrupted state has been auto-committed.

Sibling reference: `worker-mapping-with-only-a-branch-emits-invalid-empty-who`
covers a different defect in the same function (empty `who` + `where`
producing an invalid round-trip); this card is about unknown-sub-key drop.

## Decision required

Pick one of:

- **(A) Reject at the validator.** Add an unknown-sub-key check in
  `validate_card`'s worker branch — `set(worker) - {"who", "where"}` → error.
  Cheap; consistent with the existing emit contract; breaks any consumer
  already storing extra worker metadata.
- **(B) Preserve at the emitter.** Rewrite `_emit_worker` to emit all
  sub-keys via a `**rest` after `who`/`where`. Forward-compatible; widens
  the de facto schema beyond what `schema.yaml` documents; needs careful
  YAML escaping for arbitrary scalar values.
- **(C) Reject by default, opt-in preservation.** Validator rejects unknown
  sub-keys; a `schema.yaml` extension point or a project-local hook can
  whitelist additional keys. Most future-proof; biggest implementation cost.

The choice depends on whether `worker` is meant to be a closed, schema-
defined shape (→ A) or an open extension point (→ B/C). Current AGENTS.md
prose leans toward open extension, but the validator currently treats it as
closed-by-omission.

## Fix

Once decided, edit `_emit_worker` (path B/C) and/or the worker branch of
`validate_card` (path A/C) and add a regression test in `tests/` exercising
the round-trip.
