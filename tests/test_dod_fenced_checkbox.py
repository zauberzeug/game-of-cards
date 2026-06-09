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


class DodMismatchedFenceTest(unittest.TestCase):
    """Per CommonMark §4.5, a fenced code block is closed only by a fence of the
    *same* character with a run length >= the opener's. A `~~~` line shown as
    text inside a ```-opened block (or a shorter same-character run) is content,
    not a close. The shared mask must not toggle on such a line, otherwise it
    desynchronizes and a genuine `- [ ]` item after the real closing fence is
    hidden — letting `goc done` close a card with unfinished work.
    """

    # Backtick block illustrating a tilde fence, then a real open item after the
    # genuine closing backtick fence.
    DOD = (
        "- [x] MECHANICAL: the one real, completed item\n"
        "```\n"
        "an alternate fence syntax looks like:\n"
        "~~~\n"
        "```\n"
        "- [ ] TDD: a genuine unfinished item that MUST block closure\n"
    )

    def test_tilde_line_does_not_close_backtick_block(self) -> None:
        from goc.engine import count_dod_boxes

        # The `~~~` is content inside the backtick block; the real `- [ ]` after
        # the closing ``` counts as one open box.
        self.assertEqual(count_dod_boxes(self.DOD), (1, 1))

    def test_box_indices_include_real_item_after_mismatched_fence(self) -> None:
        from goc.engine import _dod_box_indices

        lines = self.DOD.splitlines()
        # Line 0 (done item) and line 5 (the real open item) are boxes; the
        # tilde line inside the block is not.
        self.assertEqual(_dod_box_indices(lines), [0, 5])

    def test_shorter_same_char_run_does_not_close(self) -> None:
        from goc.engine import count_dod_boxes

        # A 4-backtick opener is not closed by a 3-backtick run; only the
        # matching 4-backtick fence closes it. The real open item follows.
        dod = (
            "- [x] real done item\n"
            "````\n"
            "- [ ] illustrative ``` inside\n"
            "```\n"
            "- [ ] still illustrative\n"
            "````\n"
            "- [ ] TDD: a genuine unfinished item\n"
        )
        self.assertEqual(count_dod_boxes(dod), (1, 1))

    def test_longer_run_still_closes(self) -> None:
        from goc.engine import count_dod_boxes

        # A 3-backtick opener is closed by a longer (4-backtick) same-char run.
        dod = (
            "- [x] real done item\n"
            "```\n"
            "- [ ] illustrative example\n"
            "````\n"
            "- [ ] TDD: a genuine unfinished item\n"
        )
        self.assertEqual(count_dod_boxes(dod), (1, 1))

    def test_info_string_fence_line_does_not_close_block(self) -> None:
        from goc.engine import count_dod_boxes, _dod_box_indices

        # Per CommonMark §4.5 a closing fence may not carry an info string. A
        # ```yaml line inside a backtick block is content, not a close, so the
        # illustrative `- [ ]` after it must stay masked.
        dod = (
            "- [x] MECHANICAL: the one real, completed item\n"
            "```\n"
            "an example block:\n"
            "```yaml\n"
            "- [ ] TDD: illustrative checkbox that must NOT count\n"
            "```\n"
        )
        self.assertEqual(count_dod_boxes(dod), (0, 1))
        # Only the real done item at line 0 is a box; the example is masked.
        self.assertEqual(_dod_box_indices(dod.splitlines()), [0])

    def test_bare_close_still_closes_then_real_item_counts(self) -> None:
        from goc.engine import count_dod_boxes

        # A bare ``` (no info string) is the genuine close; the info-string
        # guard must not prevent a legitimate closing fence from closing.
        dod = (
            "- [x] real done item\n"
            "```python\n"
            "- [ ] illustrative example\n"
            "```\n"
            "- [ ] TDD: a genuine unfinished item after the close\n"
        )
        self.assertEqual(count_dod_boxes(dod), (1, 1))


if __name__ == "__main__":
    unittest.main()
