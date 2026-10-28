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


## 2026-10-28T05:09:43Z — Closure

- **What changed**: `goc/engine.py` `_cmd_attest` — after the closed-card and no-checks-configured refusals, ahead of the all-skipped refusal and the run loop, each `--skip` value that names no configured check in either layer is refused through the parent epic's shared `_refuse_invalid_input`: `ERROR: <title>: unknown --skip name 'x' — the configured closure checks are: a, b`, exit 2, no check run, nothing written. Unknown names are reported once each in the order given (`unknown --skip names 'a', 'b'` for several). The `--skip` help text says an unknown name is refused, and the `_refuse_invalid_input` docstring lists the case. Synced to the three plugin engine mirrors.
- **Ordering**: the check needs the config, so unlike `_cmd_decide`'s pure argument check it cannot run before the card is read. It sits ahead of the all-skipped refusal on purpose: `--skip a --skip b --skip typo` with checks `a` and `b` names the typo instead of reporting that every check was skipped, since fixing the typo may be all the call needed.
- **Docs**: `Skill(finish-card)` `reference.md` § "Attest details and skip policy" now says an unknown name is refused with the configured names listed. Template edited, mirrors regenerated, OpenClaw port re-run.
- **Reproducer**: rewritten to the deck's exit-code contract (0 = defect no longer fires, 1 = fires, 2 = harness broken). It drives the real CLI over a typo alone and a typo beside a valid skip, each on its own card, with a valid skip as the control. As filed it returned 0 on its defect-present branch, and it recognised a fix only by phrases from the fix sketch that the landed message does not use.
- **Verification**: `reproduce.py` exits 0: both cases get exit 2, `ERROR:` naming the unknown name and listing both configured checks, no check run and log.md untouched, and the control is recorded with exit 0. Against the pre-fix engine (HEAD's `goc/` extracted to a scratch dir) it exits 1. There the typo alone ran `placeholder` and wrote a FAIL block, and the typo beside a valid skip exited 0 with `Attestation OK`. `AttestCliTest` (5 tests) has its 4 refusal tests failing against the pre-fix engine and all passing now.
- **Re-run contract**: unchanged. `tests/test_verb_rerun_safety.py` declares `attest` `APPENDS`, and its probe passes no `--skip`.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1411 passed / 0 failed (`uv run python -m unittest discover -s tests`)
- **Records updated**: the parent epic (roster closure and a log entry); `reproducers-can-exit-zero-while-their-defect-still-fires` (log entry: this reproducer was inverted and was fixed on close).
- **Corrected in place**: "Why it matters" said `goc attest` is wired into `goc done`'s bundled closure. It is not — `bundled-closure-skips-configured-attestation-checks` is open because `goc done --bundle` runs no configured check — so the section now names `Skill(finish-card)` Step 5, which runs `goc attest` before `goc done`.

## Closure verification (2026-10-28T05:09:45Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-28 — Closure' present
