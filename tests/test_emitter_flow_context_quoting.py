"""Scalars spliced into a YAML *flow* collection need a wider quote trigger.

`_yaml_inline`'s quote trigger reasons about block context: it exempts `-`, `?`
and `:` from the indicator check because those bind only when space-bound —
`?query` really is an ordinary plain scalar as a block mapping value. Two
emitter sites do not write a block mapping value, though. `_yaml_inline`'s own
list branch builds a flow sequence (`tags: [a, b]`) and `_emit_worker` builds a
flow mapping (`worker: {who: a, where: b}`), and inside a flow collection a
plain scalar may carry none of `,[]{}?` anywhere. `,[]{}` were already quoted
everywhere by `_YAML_NEEDS_QUOTE`, which left `?` writing frontmatter that
`goc validate` reported OK, `yaml_lite` read back exactly, and a strict YAML
reader refused with a `ParserError` that took the whole block with it.

Reachable with no hand-edit: `goc status <card> active` stamps `worker.who`
from `git config user.name`, and git places no restriction on `?` in an author
name.

This suite pins four halves of the contract:

* the two flow sites quote a `?`-bearing scalar, and the result still
  round-trips through the vendored parser unchanged;
* block context is untouched — a `?`-bearing summary and the *flat* worker form
  stay bare, so the widening churns no existing card;
* `_YAML_FLOW_HAZARDS` really is the flow-context rule, enumerated
  independently here so shrinking it in `goc/engine.py` cannot make the test
  vacuous;
* every writer of the worker field renders through one helper, so the claim
  path cannot drift from `emit_frontmatter` again.

Filed and fixed on
`a-question-mark-in-a-worker-or-tag-writes-frontmatter-no-yaml-reader-accepts`.
"""

from __future__ import annotations

import unittest

from goc import engine
from goc._vendor import yaml_lite


HAZARD = "who?knows"


def _roundtrip(line: str):
    """Read a single frontmatter line back through the vendored parser."""
    fm, _body = engine.parse_frontmatter(f"---\n{line}\n---\n\nbody\n")
    return fm


class FlowContextQuotingTests(unittest.TestCase):
    def test_flow_sequence_element_is_quoted(self) -> None:
        rendered = engine._yaml_inline(["bug", HAZARD])
        self.assertEqual(f'[bug, "{HAZARD}"]', rendered)
        self.assertEqual({"tags": ["bug", HAZARD]}, _roundtrip(f"tags: {rendered}"))

    def test_worker_flow_mapping_members_are_quoted(self) -> None:
        rendered = engine._emit_worker({"who": HAZARD, "where": f"feat/{HAZARD}"})
        self.assertEqual(
            f'{{who: "{HAZARD}", where: "feat/{HAZARD}"}}',
            rendered,
        )
        self.assertEqual(
            {"worker": {"who": HAZARD, "where": f"feat/{HAZARD}"}},
            _roundtrip(f"worker: {rendered}"),
        )

    def test_block_context_stays_bare(self) -> None:
        """Precision: the widening is scoped to flow collections.

        A `?`-bearing summary and the flat `worker: <who>` form are both legal
        plain scalars in block context. Quoting them would rewrite the
        frontmatter of every card carrying a question mark, for nothing.
        """
        self.assertEqual(HAZARD, engine._yaml_inline(HAZARD))
        self.assertEqual(HAZARD, engine._emit_worker({"who": HAZARD}))
        self.assertEqual(HAZARD, engine._emit_worker(HAZARD))
        block = engine.emit_frontmatter({"summary": f"is {HAZARD} around"})
        self.assertIn(f"summary: is {HAZARD} around", block)

    def test_flow_hazard_set_is_the_flow_context_rule(self) -> None:
        """The set is YAML's `c-flow-indicator` plus the flow key indicator.

        Enumerated here independently of `goc/engine.py` so narrowing the set
        there — the drift that produced this defect — turns the build red
        instead of silently passing the tests above.
        """
        self.assertEqual(frozenset(",[]{}?"), engine._YAML_FLOW_HAZARDS)
        # Every hazard is refused in flow context...
        for ch in sorted(engine._YAML_FLOW_HAZARDS):
            with self.subTest(char=ch):
                self.assertTrue(engine._yaml_inline(f"a{ch}b", flow=True).startswith('"'))
        # ...and `?` is the one the block-context trigger lets through, which is
        # what makes the `flow=` parameter load-bearing rather than decorative.
        bare_in_block = {
            ch for ch in engine._YAML_FLOW_HAZARDS
            if not engine._yaml_inline(f"a{ch}b").startswith('"')
        }
        self.assertEqual({"?"}, bare_in_block)

    def test_claim_path_renders_through_the_shared_worker_emitter(self) -> None:
        """`goc status <card> active` must not restate `_emit_worker`.

        `_auto_populate_worker` carried its own copy of the flat-vs-mapping
        branch, so it kept emitting an unquoted flow mapping after the shared
        emitter was fixed. Pin the delegation, not just the output.
        """
        card = engine.Card(
            title="probe",
            path=None,
            frontmatter={"title": "probe", "worker": None},
            body="body\n",
            dod_open=0,
            dod_done=0,
        )
        text = "---\ntitle: probe\nworker: null\n---\n\nbody\n"
        out = engine._auto_populate_worker(text, card, HAZARD, "main")
        self.assertIn(f'worker: {{who: "{HAZARD}", where: main}}', out)
        fm, _body = engine.parse_frontmatter(out)
        self.assertEqual({"who": HAZARD, "where": "main"}, fm["worker"])


if __name__ == "__main__":
    unittest.main()
