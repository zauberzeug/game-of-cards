## 2026-10-14 — Instance: the deck-root resolution

`python-hooks-ignore-git-worktree-shared-deck-resolution` (advances this card)
is the first instance linked here outside the waiting/frontmatter predicates:
the hooks' `_find_project_dir` mirrored the engine's walk but not the
shared-deck worktree redirect before it, so from a linked worktree both hooks
read the checkout's own deck and config. The same resolution drifted once
before, when the hooks did not walk at all
(`goc-finds-the-deck-from-a-subdirectory-but-attests-validates-and-installs-there`,
closed). The fix mirrors the redirect, which brings a hand-rolled
reader of `workflow.worktree_deck` into both hooks. The reader is pinned with
the engine as its oracle:
`HookProjectDirWalkTest.test_hook_config_reading_agrees_with_the_engine`
compares it with `engine._shared_worktree_deck_root` over 19 hand-picked config
texts. That is the shape of option 1 below, over a chosen matrix rather than a
generated one, for one predicate. Known residue: a flow-style
`workflow: {...}` turns the engine's redirect on and not the hooks'.

## 2026-10-14 — Instance: the undecodable-card read

`session-start-hook-crashes-on-a-card-whose-bytes-do-not-decode` (advances
this card) is the second instance linked here outside the
waiting/frontmatter predicates: the card read itself. On 2026-10-10 the
engine's reads learned the corrupt-card path
(`card-with-non-utf-8-bytes-crashes-validate-and-every-deck-view-without-naming-it`):
`read_card_text` turns `UnicodeDecodeError` into `FrontmatterError`, and
`load_all_cards` warns and skips the card. The hook's four `_card_*`
readers caught only `OSError`, so the same card made the hook exit 1 before
it printed any reminder. They now catch `UnicodeDecodeError` too and skip
the card, as the engine does. The pin is a hand-written case again:
`SessionStartHookUndecodableCardTest` checks each reader against its own
unreadable-file fallback, not against the engine. An engine-derived parity
harness (option 1 of the README's decision) would cover this cell if it
compares which cards each side lists, not only the parsed fields. Known
residue: the engine reads cards in the host's default encoding and the hook
in UTF-8, so on a non-UTF-8 host they can disagree about which cards decode
at all (`goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8`).
