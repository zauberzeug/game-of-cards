## 2026-05-30T08:00:18Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Two credible paths for the matcher extension:

1. **Enumerate the three documented aliases in the regex** — the
   minimal fix shown above. Mirrors the existing alternation shape
   and the family precedent (the prior card's fix was also a regex
   tweak). Cost: one regex term plus three test rows. Risk: a future
   git release that adds a new long-form alias (precedent: `--no-ignore-removal`
   was a later addition) reopens the gap.

2. **Switch to a tokenized parser** — `shlex.split` the command,
   then inspect tokens: `git`, `add`, and any token that starts with
   `-` and is in the set `{-A, -p, -u, --all, --update, --patch}`,
   OR the bare token `.`. More resilient to future git flag
   additions; rejects `git add foo.py` and `git add -- foo.py`
   naturally. Cost: ~10 LOC, slightly slower than regex (negligible
   on a single command string), and the parser must handle quoting.

The family precedent and the maintenance ratio (this code path has
churned twice for matcher bugs in the last quarter) point at option
2; option 1 keeps the diff minimal and preserves the family's
visual shape. The choice also affects whether a fourth card in this
family is plausible — option 2 closes the meta-fix loop; option 1
leaves the "what about `--no-all`?" / "what about `--intent-to-add`?"
question open by default.


## 2026-05-30T14:00:28Z: decision recorded

Option 2: replace the git-add regex matcher with a tokenized shlex.split parser that inspects tokens — match when the command is git add with any flag in {-A,-p,-u,--all,--update,--patch} or the bare '.' token, rejecting 'git add foo.py' and 'git add -- foo.py' — this code path has churned twice for matcher bugs this quarter; a tokenized parser is resilient to future git long-form alias additions and closes the meta-fix loop so no fourth card in the family is needed, at a cost of ~10 LOC. Gate decision → none.
