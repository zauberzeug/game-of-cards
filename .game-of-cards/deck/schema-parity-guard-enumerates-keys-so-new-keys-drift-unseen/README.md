---
title: schema-parity-guard-enumerates-keys-so-new-keys-drift-unseen
summary: "The schema-parity guard compares an enumerated key list, not the whole schema. tests/test_skill_schema_yaml_parity.py asserts six named keys plus every '*_values' key, so any other top-level key can differ between goc/schema.yaml and the card-schema skill's bundled copy in either direction with the suite green — while the guard's own docstring claims 'Drift in either file fails the test'. Two open cards would add exactly such a key."
status: done
stage: null
contribution: medium
created: "2026-08-02T05:50:06Z"
closed_at: "2026-08-02T05:54:37Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, test, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — a new top-level key present in only one of the two schema files turns `SkillSchemaParityTest` red, in both directions, while both controls still fire.
  - [x] TDD: `tests/test_skill_schema_yaml_parity.py` gains a derived assertion comparing the two parsed mappings wholesale, so coverage needs no edit when a future schema version adds a key.
  - [x] MECHANICAL: the guard's module docstring no longer claims more than the code delivers — it states that the named tests are diagnostics and the mapping equality is the contract.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` green, `uv run goc validate` clean, `python scripts/sync_plugin_assets.py --check` clean.
worker: {who: "claude[bot]", where: main}
---

# The schema-parity guard enumerates keys, so a new schema key drifts unseen

## Location

- Guard: [`tests/test_skill_schema_yaml_parity.py`](../../../tests/test_skill_schema_yaml_parity.py) — `SkillSchemaParityTest`, lines 44–71.
- Authoritative schema: [`goc/schema.yaml`](../../../goc/schema.yaml), read at runtime by `engine.load_schema()`.
- Skill-bundled copy: [`goc/templates/skills/card-schema/schema.yaml`](../../../goc/templates/skills/card-schema/schema.yaml) — installed into every consumer's `card-schema` skill and mirrored to five downstream trees.

## What's broken

The guard is a list of named assertions, one per key:

```python
    def test_schema_version(self) -> None:
        self._assert_equal("schema_version")

    def test_required_fields(self) -> None:
        self._assert_equal("required_fields")
    ...
    def test_all_enum_value_lists(self) -> None:
        engine_enum_keys = {k for k in self.engine if k.endswith("_values")}
```

Six keys are named outright (`schema_version`, `required_fields`,
`optional_fields`, `title_pattern`, `canonical_tags`,
`human_gate_default`); `test_all_enum_value_lists` covers the `*_values`
family by derivation. Nothing compares the two mappings as a whole, so a
top-level key that is neither named nor `*_values`-suffixed is compared by
nothing at all — in either direction.

Its own module docstring states the opposite:

> Plugin-mirror parity (`engine.validate_plugin_mirror_parity`) already
> guards the four downstream mirrors against the template; this test
> closes the remaining gap between the template and the engine's
> authoritative copy. **Drift in either file fails the test.**

That last sentence is the contract readers act on, and it is false for
every key outside the enumeration.

Today's schema happens to have no such key — all eleven top-level keys
fall inside the covered set — which is why the hole is invisible from
inspection alone and needs the probe below.

## Empirical evidence

`reproduce.py` runs the real `SkillSchemaParityTest` against temp schema
pairs. Two controls establish that the guard does work on covered keys;
two cases add a plausible new key to one copy only. Before the fix:

```
byte-identical today: True

[control] drop 'blocked' from status_values   -> guard green: False
[control] extra canonical tag in skill copy   -> guard green: False
[case 1]  new key 'required_when', engine only -> guard green: True
[case 2]  new key 'required_when', skill only  -> guard green: True

DEFECT: 2 drift(s) the guard cannot see:
  - engine-only key 'required_when' is invisible to the guard
  - skill-only key 'required_when' is invisible to the guard
```

Both controls turn the guard red, so the harness was not simply failing to
run the tests; the two drift cases left it green. After the fix, all four
turn it red and `reproduce.py` exits 0.

One harness detail is worth keeping: `_assert_equal` builds its failure
message with `relative_to(ROOT)` eagerly, on passing calls too, so a probe
that redirects the schema paths must move `ROOT` with them. A first draft
that did not reported all four cases as "caught" — the tests were erroring
on the message construction, not on drift. Both controls exist to catch
exactly that class of harness lie.

## Why it matters

The reachability path is short and already queued. Two open cards land a
new top-level schema key as their normal implementation:

- [schema-yaml-omits-closed-at-conditional-requirement-for-terminal-status](../schema-yaml-omits-closed-at-conditional-requirement-for-terminal-status/) — expresses "`closed_at` is required when status is terminal" in the schema, which needs a conditional-requirement table (`required_when:` in the probe).
- [support-custom-frontmatter-fields-with-enum-and-required-when-rules](../support-custom-frontmatter-fields-with-enum-and-required-when-rules/) — adds custom-field declarations with enum and `required_when` rules.

Whichever lands first will edit `goc/schema.yaml`. If the author does not
also hand-edit the skill copy, CI stays green and the drift ships: the
skill copy is what `goc install` writes into every consumer's
`card-schema` skill, so agents author cards against a schema the
validator does not enforce, or miss a rule it does. That is the exact
failure the guard was written for — see its originating card
[card-schema-skill-bundled-schema-omits-supersedes-superseded-by-and-worker](../card-schema-skill-bundled-schema-omits-supersedes-superseded-by-and-worker/),
whose DoD asked for parity on a *named list* of keys. The guard honoured
that DoD literally, and inherited its scope as a permanent ceiling.

The five downstream mirrors do not help: `sync_plugin_assets.py` and
`validate_plugin_mirror_parity` compare each mirror against
`goc/templates/skills/`, so they would faithfully propagate the stale
copy to all five trees. The hole is at the head of the chain.

This repo already states the principle the guard misses — from
`scripts/check_card_language.py`:

> Deriving converges where enumerating cannot […] no future prefix
> combination can become a new false positive.

`test_all_enum_value_lists` applies exactly that reasoning to the
`*_values` family. The remaining six assertions do not.

## Fix (landed)

`tests/test_skill_schema_yaml_parity.py` gains one derived assertion that
compares the parsed mappings wholesale, so no key can escape by being
unnamed:

```python
    def test_no_unguarded_top_level_key(self) -> None:
        self.assertEqual(self.engine, self.skill, ...)
```

The six named tests stay. They cost nothing and give a precise diagnostic
("`canonical_tags` drift") where the wholesale assertion can only say the
two files disagree — so the class is now one contract with six
diagnostics under it, and the docstring says so instead of overclaiming.

Whole-mapping equality rather than a key-set comparison is the part that
converges: a key-set check would re-open the hole for any key whose
*value* drifts. Byte-equality was the other candidate and was not taken —
the two files are byte-identical today, but nothing requires the skill
copy to stay commentless, and comparing parsed mappings is the property
the guard actually exists to protect.

Suite 888 → 889 tests, green.

## Scope note

This was about the guard's *shape*, not a live drift: the two files are
byte-identical today (`reproduce.py` confirms it on every run), and
neither schema file was touched. Sibling guards were checked and are not
affected — `test_schema_enum_surface_parity.py` already derives from
`schema.*` lists, and the plugin-mirror walks compare whole trees rather
than named keys.
