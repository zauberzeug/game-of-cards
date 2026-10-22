## 2026-05-31T03:20:21Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Two credible fix paths exist; one needs a human pick.

### Option A — strict rejection at command entry (recommended)

Before the per-check loop, compute the set of valid skip names
from the config:

```python
valid_skip_names = {
    check["name"]
    for layer_key in ("layer_2_project_dod", "layer_3_goc_dod")
    for check in (config.get(layer_key) or [])
}
unknown = set(skips) - valid_skip_names
if unknown:
    print(
        f"ERROR: --skip name(s) {sorted(unknown)!r} do not match any "
        f"configured check; valid: {sorted(valid_skip_names)!r}",
        file=sys.stderr,
    )
    sys.exit(2)
```

Matches the existing pattern in `_cmd_status` / `_cmd_decide` for
flagged-unknown rejection. Breaking change for any script that
relied on the silent-no-op behavior, but that behavior is itself
the bug — no caller should be relying on it.

### Option B — warn-and-continue

Same validation, but print a warning to stderr and let the
attestation proceed. Preserves any backwards compat with scripts
that pass `--skip` names speculatively but still surfaces the
typo to a human in the terminal.

### What the human picks

- A or B (strict-error vs warn-continue).
- Whether the policy should generalize across the rest of the CLI
  surface — `goc decide`, `goc status`, `goc advance` already have
  pieces of this pattern; this card may want to be promoted to a
  `meta-fix` epic for "uniform unknown-input validation across CLI
  verbs" if the answer is consistently A.


## 2026-10-22T05:20:22Z: decision recorded

Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: Option A, strict rejection at command entry — an unknown --skip name exits 2 and lists the valid check names — The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question. Gate decision → none.
