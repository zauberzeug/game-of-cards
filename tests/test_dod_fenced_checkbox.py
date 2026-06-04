from __future__ import annotations

import unittest


class DodFencedCheckboxTest(unittest.TestCase):
    """A `- [ ]` checkbox shown as an example inside a fenced code block within
    a card's `definition_of_done` must NOT be counted as a real DoD item.
    Otherwise an illustrative checkbox inflates the unchecked-box count and
    makes the card impossible to close (`goc done` / `goc done --force` both
    refuse). The three DoD scanners must agree on the same non-fenced line set.
    """

    DOD = (
        "- [x] MECHANICAL: the one real DoD item, completed\n"
        "For future authors, a DoD checkbox line looks like:\n"
        "```\n"
        "- [ ] write a failing test first\n"
        "```\n"
    )

    def test_count_dod_boxes_skips_fenced_example(self) -> None:
        from goc.engine import count_dod_boxes

        # One checked real item; the fenced `- [ ]` example is not a box.
        self.assertEqual(count_dod_boxes(self.DOD), (0, 1))

    def test_untagged_dod_items_skips_fenced_example(self) -> None:
        from goc.engine import untagged_dod_items

        # The only checkbox outside the fence is tagged (MECHANICAL:), and the
        # fenced example must not surface as an untagged item.
        self.assertEqual(untagged_dod_items(self.DOD), [])

    def test_box_indices_skips_fenced_example(self) -> None:
        from goc.engine import _dod_box_indices

        lines = self.DOD.splitlines()
        # Only line 0 (the real checked item) is a box; the fenced example at
        # line 3 is excluded.
        self.assertEqual(_dod_box_indices(lines), [0])

    def test_scanners_agree_on_box_line_set(self) -> None:
        from goc.engine import _dod_box_indices, count_dod_boxes

        lines = self.DOD.splitlines()
        open_n, done_n = count_dod_boxes(self.DOD)
        # The counter and the index space the quality-pass rewriter targets must
        # report the same number of boxes.
        self.assertEqual(open_n + done_n, len(_dod_box_indices(lines)))

    def test_tilde_fence_also_skipped(self) -> None:
        from goc.engine import count_dod_boxes

        dod = (
            "- [x] MECHANICAL: real item\n"
            "~~~\n"
            "- [ ] example inside a tilde fence\n"
            "~~~\n"
        )
        self.assertEqual(count_dod_boxes(dod), (0, 1))

    def test_real_open_box_outside_fence_still_counts(self) -> None:
        from goc.engine import count_dod_boxes

        dod = (
            "- [ ] TDD: a real, still-open item\n"
            "```\n"
            "- [ ] illustrative example\n"
            "```\n"
            "- [x] MECHANICAL: a real, done item\n"
        )
        # One real open + one real done; the fenced example is ignored.
        self.assertEqual(count_dod_boxes(dod), (1, 1))


if __name__ == "__main__":
    unittest.main()
