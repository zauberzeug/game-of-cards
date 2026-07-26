## 2026-07-26T19:16:00Z — Supporting evidence from an audit round

A pull-card session whose ready queue was empty fell through to
`Skill(audit-deck)` and independently reached this card's `_walk` site while
checking AGENTS.md's claim that the plugin payloads "must be real files (not
symlinks pointing outside the subtree, which silently disappear on consumer
install)". Rather than file a near-duplicate, the finding is recorded here.

- **Added**: a fourth shape in the body — a *valid* outside-pointing symlink
  with matching target content. Verified directly against `engine._DeepDircmp`
  on a scratch pair of trees: `same_files: ['engine.py']`, with `left_only`,
  `right_only`, `diff_files`, `common_funny` and `funny_files` all empty.
- **Why it widens this card**: the currently-proposed fix (read `common_funny`
  and `funny_files`) would NOT catch it — `filecmp` follows the link and
  compares the target's bytes, and the "funny" buckets only collect stat
  failures and type mismatches. Closing this card by reading those buckets
  alone would leave the shape AGENTS.md explicitly warns about undetected, so
  the fix should assert entry type (`Path.is_symlink()` / `os.lstat`) across
  the mirror trees.
- **Not changed**: status, gate, DoD. Still `unverified` and awaiting the
  decision this card was parked on; the new shape is one more input to it.
