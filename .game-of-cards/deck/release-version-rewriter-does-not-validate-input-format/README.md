---
title: release-version-rewriter-does-not-validate-input-format
summary: "`scripts/release_rewrite_versions.py` accepts any non-empty argv[1] as the version and writes all eight publish/dogfood targets (six JSON/Python literal patterns, the `.goc-version` full-file write, AND the AGENTS.md marker) without validating the format. Empirically confirmed (see reproduce.py): passing `1.0` succeeds with exit 0 and mutates every target. The script's docstring promises it 'fails loudly on any expected-vs-actual mismatch — versions are too important to silently no-op,' but the only `\\d+\\.\\d+\\.\\d+` regex (the AGENTS.md pattern) anchors on the OLD value being replaced, not the new value being written — so it never validates input format."
status: active
stage: null
contribution: medium
created: "2026-05-30T12:43:43Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — a malformed-version dispatch leaves zero files mutated (script rejects up front)
  - [ ] TDD: `rewrite_all` raises / `main` returns non-zero with a clear error message naming the expected format BEFORE any `_replace` or `.goc-version` write fires
  - [ ] TDD: valid release-mode inputs (`1.2.3`), dry-run mode (`0.99.0`), and tag-recovery mode (existing semver tag) still succeed end-to-end — regression tested against the format `re.fullmatch(r"\d+\.\d+\.\d+", version)`
  - [ ] MECHANICAL: the script docstring's "fails loudly … silently no-op" sentence is left in place (it is now accurate) or strengthened to "validates input format before writing any file"
worker: {who: "claude[bot]", where: main}
---

# Release version rewriter does not validate input format

## Location

`scripts/release_rewrite_versions.py:60-138` — specifically the `_replace`
calls in `rewrite_all` and the bare argv length check in `main`.

## What's broken

The script's docstring (lines 32-37) promises:

> The rewrite is surgical: each match is anchored on enough surrounding context
> that bumping a real release version cannot collide with unrelated `"version"`
> fields (e.g. transitive-dep entries inside package-lock.json). The script
> fails loudly on any expected-vs-actual mismatch — versions are too important
> to silently no-op.

The contract the reader takes from this is "validation runs before any write."
The actual implementation has zero input validation:

```python
def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: release_rewrite_versions.py X.Y.Z", file=sys.stderr)
        return 2
    rewrite_all(argv[1])           # ← argv[1] is passed through with zero format checks
    ...
```

Every pattern inside `rewrite_all` either uses a `[^"]+` payload placeholder
(matches any non-quote string) or — for the one regex that names a semver
shape — anchors on the OLD value being SEARCHED, not the new value being
WRITTEN:

```python
_replace(
    ROOT / "goc" / "__init__.py",
    r'^__version__\s*=\s*"[^"]+"$',          # search pattern; replacement isn't validated
    f'__version__ = "{version}"',
    expected=1,
)
# … five more _replace calls, each with [^"]+ payload patterns …

(ROOT / ".game-of-cards" / "deck" / ".goc-version").write_text(f"{version}\n")

_replace(
    ROOT / "AGENTS.md",
    r"^<!-- BEGIN GOC v\d+\.\d+\.\d+ -->$",  # ← matches the CURRENT marker (well-formed)
    f"<!-- BEGIN GOC v{version} -->",        # ← replacement uses {version} as-is
    expected=1,
)
```

Because `re.subn` validates the *pattern* against existing text but treats the
*replacement* as opaque, the AGENTS.md call finds the well-formed marker that
is already in the file, replaces it with `<!-- BEGIN GOC v1.0 -->`, and reports
count=1 → success. The "format-validating" regex never actually validates the
input.

**Empirically confirmed** (see `reproduce.py`): passing `1.0` to the script
exits with status 0, writes `__version__ = "1.0"` into `goc/__init__.py`,
`"version": "1.0"` into all five JSON manifests, `1.0\n` into `.goc-version`,
AND `<!-- BEGIN GOC v1.0 -->` into AGENTS.md. The script's "fails loudly"
claim does not hold — it fails silently, producing eight mutated files with a
malformed version.

## Why it matters

**Reachability.** The script is called exactly once per release, by
`.github/workflows/release.yml:288-291`:

```yaml
- name: Rewrite version literals
  env:
    RELEASE_VERSION: ${{ steps.version.outputs.release_version }}
  run: python3 scripts/release_rewrite_versions.py "$RELEASE_VERSION"
```

`release_version` is computed at `release.yml:201-235` and accepts whatever
the dispatcher passed in `-f version=…`:

```bash
elif [[ -n "$INPUT_VERSION" ]]; then
    release_version="$INPUT_VERSION"   # ← no format check, passed straight through
    mode=release
```

So `gh workflow run release.yml -f version=1.0` (a maintainer fat-fingers
the `.Z` segment) or `-f version=v1.2.3` (stray `v` from copy-pasting a
tag name) or `-f version=1.2.3-rc1` (someone tries a prerelease before
the release pipeline supports one) all reach the rewriter unfiltered.

**Containment today.** A later step in the same job
(`Validate npm lockfile is internally consistent`, `release.yml:299-311`)
catches the npm-invalid shapes via `npm install --package-lock-only`. The
`Assert wheel version matches release version` step (`release.yml:328-346`)
catches Python-side mismatches by comparing the built wheel's filename
segment to `RELEASE_VERSION`. For inputs that npm rejects, the CI run
goes red and the commit-and-push step (`release.yml:355-404`) never runs.

But several malformed shapes pass BOTH checks:

- `1.2.3.4` — valid PEP 440 (post-release tuple), but bypasses semver
  expectations everywhere downstream. npm rejects with "Invalid Version,"
  so CI red. Disk on CI runner dirty.
- `1.2.3a1` — valid PEP 440 prerelease, valid npm semver (`1.2.3-a1`?
  npm uses strict semver — would be rejected). CI red.
- `1.2.3` followed by a stray trailing whitespace from a quoting accident
  in the workflow — `\d+\.\d+\.\d+ ` would slip past every search pattern
  because `[^"]+` matches everything except `"`.

For every malformed shape the npm step or the wheel step does NOT
catch, the rewrite commit would land on `main` with a broken version
literal. The current pipeline survives by luck (the strict steps are
downstream of the rewrite) not by design.

**Why file.** Three reasons.

1. The script's docstring sets an expectation ("fails loudly on any
   expected-vs-actual mismatch") that does not match the implementation.
   The "format-validating" AGENTS.md regex is actually a "old marker
   shape" regex — it doesn't validate the replacement. A maintainer
   reading the docstring assumes a stronger guarantee than the code
   provides.
2. Defense in depth in the release pipeline is cheap. A one-line
   `re.fullmatch(r"\d+\.\d+\.\d+", version)` guard at the top of
   `rewrite_all` (or `main`) raises before any byte hits disk, makes the
   error message precise ("expected X.Y.Z, got '1.0'") instead of the
   later-stage "Invalid Version" from npm or "wheel version does not
   match" from the assert step.
3. The current containment relies on downstream tools (`npm`, the wheel
   name regex) for input validation that the source-of-truth rewriter
   should be doing itself. That coupling is fragile: if the release
   flow ever stops calling `npm install --package-lock-only` (e.g., the
   OpenClaw plugin is dropped, or a future refactor moves lockfile
   validation to its own job), the malformed-version surface becomes
   consumer-visible.

## Fix

Add an explicit format guard before any file is touched. Two equivalent
landing sites:

**Option A** — at the top of `rewrite_all`, so the function is atomic
on malformed input regardless of caller:

```python
import re

_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

def rewrite_all(version: str) -> None:
    if not _VERSION_PATTERN.match(version):
        sys.exit(
            f"ERROR: invalid version {version!r}: expected X.Y.Z "
            f"(three dot-separated non-negative integers)."
        )
    # … existing _replace calls …
```

**Option B** — at the top of `main`, before calling `rewrite_all`:

```python
def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: release_rewrite_versions.py X.Y.Z", file=sys.stderr)
        return 2
    version = argv[1]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print(
            f"ERROR: invalid version {version!r}: expected X.Y.Z.",
            file=sys.stderr,
        )
        return 2
    rewrite_all(version)
    ...
```

Either works. Option A is slightly preferred because it keeps the
guarantee with the function that makes the on-disk changes — a future
caller (a test, a one-off maintenance script) that imports `rewrite_all`
directly would still get the validation.

## Empirical evidence

Run `uv run python .game-of-cards/deck/release-version-rewriter-does-not-validate-input-format/reproduce.py`
to demonstrate the half-apply (the script snapshots and restores the
six tracked files plus `.goc-version` so the working tree is untouched).
Expected output is in the closing line of the reproducer: a
non-zero script exit AND seven files mutated before the failure.
