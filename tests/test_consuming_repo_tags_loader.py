"""Regression: `_load_consuming_repo_tags` must treat a non-list
`canonical_tags` block value as structurally absent, not iterate it
character-by-character. Same root-cause family as the closed siblings
on card frontmatter list fields, but on the canonical-tags.md
deck-extension surface.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from goc import engine


class ConsumingRepoTagsLoaderGuardTest(unittest.TestCase):
    def _run_with_canonical_tags_md(self, body: str) -> set[str]:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = Path(tmp) / ".game-of-cards"
            game_dir.mkdir()
            (game_dir / "canonical-tags.md").write_text(body)
            with mock.patch.object(engine, "DECK_ROOT", Path(tmp)):
                return engine._load_consuming_repo_tags()

    def test_bare_string_canonical_tags_does_not_split_into_chars(self) -> None:
        loaded = self._run_with_canonical_tags_md(
            "```yaml\ncanonical_tags: my-tag\n```\n"
        )
        # Buggy behavior produced {'-', 'a', 'g', 'm', 't', 'y'}; the
        # guard drops the malformed shape silently.
        self.assertEqual(loaded, set())

    def test_canonical_list_form_passes_through_unchanged(self) -> None:
        loaded = self._run_with_canonical_tags_md(
            "```yaml\ncanonical_tags:\n  - my-tag\n  - other-tag\n```\n"
        )
        self.assertEqual(loaded, {"my-tag", "other-tag"})

    def test_other_non_list_canonical_tags_shapes_coerce_to_empty(self) -> None:
        # Each malformed shape under test: a YAML scalar, a YAML mapping,
        # and a YAML int. All must be ignored, not iterated.
        for body, label in (
            ("```yaml\ncanonical_tags: just-a-string\n```\n", "scalar"),
            ("```yaml\ncanonical_tags:\n  nested: mapping\n```\n", "mapping"),
            ("```yaml\ncanonical_tags: 42\n```\n", "int"),
        ):
            with self.subTest(shape=label):
                self.assertEqual(self._run_with_canonical_tags_md(body), set())

    def test_unhashable_list_element_does_not_crash(self) -> None:
        # A nested list under canonical_tags is unhashable; the buggy
        # `set.update(value)` raised TypeError (unhashable type: 'list')
        # and, via load_schema(), crashed every goc command. The guard
        # must drop the bad element and keep the valid string tags.
        loaded = self._run_with_canonical_tags_md(
            "```yaml\ncanonical_tags:\n  - good-tag\n  - [nested, list]\n```\n"
        )
        self.assertEqual(loaded, {"good-tag"})

    def test_hashable_non_string_list_elements_are_dropped(self) -> None:
        # Ints/bools are hashable, so the buggy code silently added them
        # to the set ({'good-tag', 123, True}) where they can never match
        # a string tag. The guard must filter them out.
        loaded = self._run_with_canonical_tags_md(
            "```yaml\ncanonical_tags:\n  - good-tag\n  - 123\n  - true\n```\n"
        )
        self.assertEqual(loaded, {"good-tag"})

    def test_non_mapping_block_is_skipped_not_get_ed(self) -> None:
        # A fenced ```yaml block that parses to a bare list is not a
        # mapping. The buggy code called `block.get("canonical_tags")`
        # unconditionally, raising AttributeError ('list' has no `.get`)
        # and — via load_schema() at import — crashing every goc command.
        # The guard must skip the non-mapping block and return set().
        loaded = self._run_with_canonical_tags_md(
            "```yaml\n- frontend\n- backend\n```\n"
        )
        self.assertEqual(loaded, set())

    def test_non_mapping_block_does_not_poison_valid_block(self) -> None:
        # A valid mapping block followed by a bare-list block: the valid
        # tags must survive and the list block must be skipped, not crash.
        body = (
            "```yaml\ncanonical_tags:\n  - good-tag\n```\n"
            "\n"
            "```yaml\n- frontend\n- backend\n```\n"
        )
        self.assertEqual(self._run_with_canonical_tags_md(body), {"good-tag"})

    def test_multiple_blocks_accumulate_only_valid_lists(self) -> None:
        # One well-formed block, one malformed bare-string block. The
        # accumulator must keep the valid block's entries and drop the
        # bad one — not poison the set with single characters.
        body = (
            "```yaml\ncanonical_tags:\n  - good-tag\n```\n"
            "\n"
            "```yaml\ncanonical_tags: bad-tag\n```\n"
        )
        self.assertEqual(self._run_with_canonical_tags_md(body), {"good-tag"})


if __name__ == "__main__":
    unittest.main()
