"""deck.py — deck CLI; lives inside the deck skill.

Computes filtered kanban-style views over `deck/<title>/README.md` frontmatter.
The deck is the project's card-tracking surface — one card per work item, with
status (open/active/blocked/done/disproved/superseded) on a kanban board.

Run via `uv run python .claude/skills/deck/deck.py …` per project's `uv run`
discipline. The schema is a YAML data file at the sibling card-schema skill:
`.claude/skills/card-schema/schema.yaml`. Cards (the data instances) live at
the project-root `deck/` directory; only the methodology (CLI + schema +
skill bodies) lives under `.claude/skills/`.
"""

from __future__ import annotations

import filecmp
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import argparse
from goc._vendor import yaml_lite as yaml

# ────────────────────────────────────────────────────────────────────────────
# Paths

PACKAGE_DIR = Path(__file__).resolve().parent  # installed package dir (goc/)
REPO_ROOT = Path.cwd()  # project being managed (consuming repo's root)


_DUAL_TREE_CONFLICT: bool = False
_LEGACY_ONLY: bool = False


def _detect_worktree_common_root(cwd: Path) -> Path | None:
    """Return primary working tree root if cwd is inside a git worktree, else None.

    Signal: git rev-parse --git-common-dir differs from --git-dir when cwd is
    a linked worktree; the common dir is then the primary .git directory.
    """
    try:
        r_git = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, cwd=str(cwd), timeout=5,
        )
        r_common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, cwd=str(cwd), timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if r_git.returncode != 0 or r_common.returncode != 0:
        return None
    git_dir = r_git.stdout.strip()
    common_dir = r_common.stdout.strip()
    if git_dir == common_dir:
        return None  # primary working tree, not a worktree
    common_path = Path(common_dir)
    if not common_path.is_absolute():
        common_path = (cwd / common_path).resolve()
    return common_path.parent


def _resolve_deck_root(cwd: Path) -> Path:
    """Return the root for deck and config file resolution.

    When running inside a git worktree AND worktree_deck=shared is enabled
    (GOC_WORKTREE_DECK=shared env var or workflow.worktree_deck: shared in
    the common root's config.yaml), returns the primary working tree root so
    all worktrees share a single deck. Otherwise returns cwd unchanged.
    """
    common_root = _detect_worktree_common_root(cwd)
    if common_root is None:
        return cwd
    # Env var wins without requiring the config to exist yet.
    if os.environ.get("GOC_WORKTREE_DECK", "").lower() == "shared":
        return common_root
    config_path = common_root / ".game-of-cards" / "config.yaml"
    if config_path.exists():
        try:
            cfg = yaml.safe_load(config_path.read_text()) or {}
            if (cfg.get("workflow") or {}).get("worktree_deck") == "shared":
                return common_root
        except Exception:
            pass
    return cwd


def _resolve_deck_dir(repo_root: Path) -> Path:
    """Return the deck directory for single-tree scenarios.

    Sets _DUAL_TREE_CONFLICT when both .game-of-cards/deck/ and deck/ exist
    so the CLI group can refuse before dispatching any mutating subcommand.
    Sets _LEGACY_ONLY when only deck/ exists so callers can warn.
    """
    global _DUAL_TREE_CONFLICT, _LEGACY_ONLY
    canonical = repo_root / ".game-of-cards" / "deck"
    legacy = repo_root / "deck"
    if canonical.exists() and legacy.exists():
        _DUAL_TREE_CONFLICT = True
        _LEGACY_ONLY = False
        return canonical
    _DUAL_TREE_CONFLICT = False
    if canonical.exists():
        _LEGACY_ONLY = False
        return canonical
    if legacy.exists():
        _LEGACY_ONLY = True
        return legacy
    _LEGACY_ONLY = False
    return canonical


DECK_ROOT = _resolve_deck_root(REPO_ROOT)
DECK_DIR = _resolve_deck_dir(DECK_ROOT)
SCHEMA_FILE = PACKAGE_DIR / "schema.yaml"
GAME_OF_CARDS_CONFIG_FILE = DECK_ROOT / ".game-of-cards" / "config.yaml"
LEGACY_DECK_CONFIG_FILE = DECK_ROOT / ".claude" / "config.yaml"

# ────────────────────────────────────────────────────────────────────────────
# Frontmatter parser — used for SCHEMA.md AND every card's README.md

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


class FrontmatterError(ValueError):
    """Raised when the opening `---` is present but frontmatter is malformed.

    Distinct from the legitimate ({}, text) return path of `parse_frontmatter`,
    which signals "no frontmatter delimiters present at all" — a normal state
    for non-card files. This exception is for the corrupt-card case where the
    opener is there but the closer is missing or the YAML inside is unparseable.
    """


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML between leading `---` markers; return (data, body).

    Three outcomes:
      - No opening `---` at line 1  → returns ({}, text) (non-frontmatter file)
      - Opening present, closing missing/unparseable → raises FrontmatterError
      - Both delimiters present, YAML valid → returns (data, body)
    """
    if not (text.startswith("---\n") or text.startswith("---\r\n")):
        return {}, text
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise FrontmatterError(
            "frontmatter unterminated: opening '---' at line 1 has no "
            "matching closing '---' delimiter"
        )
    try:
        data = yaml.safe_load(m.group(1))
    except ValueError as exc:
        raise FrontmatterError(
            f"YAML parse error inside frontmatter: {exc}"
        ) from exc
    if data is None:
        data = {}
    elif not isinstance(data, dict):
        raise FrontmatterError(
            "frontmatter is not a mapping: the YAML between the '---' "
            f"delimiters parsed to a {type(data).__name__}, expected key/value pairs"
        )
    return data, m.group(2)


_YAML_NEEDS_QUOTE = re.compile(r"[:#'\"\\\[\]\{\}\,`@]")
# Leading indicator chars the vendored parser rejects in value position:
# `&`/`*` crash the parse (anchors/aliases not supported). `[`/`{`/`"`/`'`
# are already caught anywhere by _YAML_NEEDS_QUOTE.
_YAML_INDICATOR_FIRST = frozenset("&*")
# Whole-value tokens the parser interprets as block/folded scalar indicators.
# Covers both bare-indicator forms (`|`, `|-`, `>+`) and the explicit-indent
# forms the vendored parser's `_BLOCK_INDICATOR_RE` / `_FOLDED_INDICATOR_RE`
# accept (`|2`, `|3`, `|10`, `|2-`, `|2+`, and the folded peers `>2`, `>10`,
# `>2-`, `>2+`). Both branches carry `\d*` so the explicit-indent digit run is
# recognized on the folded side too — the parser's folded recognizer accepts
# it, so an unquoted `>2` would crash on re-parse. Coupled by shape to
# `yaml._BLOCK_INDICATOR_RE` / `yaml._FOLDED_INDICATOR_RE` so the emitter's
# quote-trigger cannot drift from the parser's recognizers.
_YAML_BLOCK_HEADER_RE = re.compile(r"^(?:\|\d*[-+]?|>\d*[-+]?)$")


def _contains_line_break(s: str) -> bool:
    """True when `s` holds any character str.splitlines() treats as a line
    boundary (LF plus CR, VT, FF, FS, GS, RS, NEL, U+2028, U+2029).

    The vendored parser splits the document with str.splitlines()
    (`yaml_lite._Parser(text.splitlines())`), so any such character — not just
    LF — breaks a scalar on re-parse, truncating its value and dropping every
    frontmatter field below it. Deriving the predicate from str.splitlines()
    itself is what keeps the emitter's line-break guard from drifting from the
    parser's line-splitting: a hand-maintained character list near the `"\\n"`
    check would inevitably miss the other nine. `"".join(s.splitlines())` drops
    exactly the break characters and nothing else, so it differs from `s` iff
    `s` contains at least one.
    """
    return "".join(s.splitlines()) != s


def _parser_coerces_scalar(s: str) -> bool:
    """True when the vendored parser would coerce bare scalar `s` to a
    non-string (int / None / bool).

    Derived by reference from the parser's own recognizers
    (`yaml._INT_RE`, `yaml._NULL_SET`, `yaml._TRUE_SET`, `yaml._FALSE_SET`)
    plus its empty-string branch (`if not text` in `_parse_scalar`)
    so the emitter's quote-trigger and the parser's coercion cannot drift.
    `_DATE_RE` is intentionally excluded: the parser returns date-shaped
    scalars as the original string, so they round-trip bare unchanged.
    """
    return (
        s == ""
        or s in yaml._NULL_SET
        or s in yaml._TRUE_SET
        or s in yaml._FALSE_SET
        or bool(yaml._INT_RE.match(s))
    )


def _yaml_inline(value) -> str:
    """Render a scalar/list as inline YAML for flat-frontmatter use.

    Multi-line strings are NOT supported here — emit_frontmatter detects
    them and uses literal-block style (`|-`) instead.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[]" if not value else "[" + ", ".join(_yaml_inline(v) for v in value) + "]"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        # The vendored parser has no float recognizer (only `_INT_RE`), so a
        # bare float would read back as a string — silent type-loss. No card
        # frontmatter field is a float, so refuse at the boundary rather than
        # advertise a type that cannot round-trip.
        raise FrontmatterError(
            f"float frontmatter values are not supported (got {value!r}); "
            "store the value as a string or int."
        )
    s = str(value)
    if _contains_line_break(s):
        # The inline emitter has no double-quoted escape for line breaks that
        # round-trips through the vendored parser, and emitting bare destroys
        # every frontmatter field below this one (the parser splits the scalar
        # on the break via str.splitlines(), so the trailing lines are read as
        # top-level non-key text and end the mapping early). LF-delimited text
        # must route through `emit_frontmatter`, which detects it and uses
        # literal-block style (`|-`) — see the docstring above. Other line
        # breaks (CR, VT, FF, FS, GS, RS, NEL, U+2028, U+2029) cannot round-trip
        # at all — literal-block style would silently rewrite them to LF and the
        # parser has no escape that decodes them — so they are refused outright,
        # the same boundary posture as the float branch above.
        raise FrontmatterError(
            "frontmatter scalar contains a line-break character the vendored "
            "parser splits on (str.splitlines breaks on LF plus CR/VT/FF/FS/GS/"
            "RS/NEL/U+2028/U+2029); emitting it bare would truncate the value "
            "and drop every field below it. Route LF-delimited text through "
            "emit_frontmatter (block-scalar `|-`); other line breaks are "
            "unsupported."
        )
    if (
        _YAML_NEEDS_QUOTE.search(s)
        or _parser_coerces_scalar(s)
        or bool(_YAML_BLOCK_HEADER_RE.match(s))
        or (s and s[0] in _YAML_INDICATOR_FIRST)
        or s != s.strip()
    ):
        # Escape \ and " for safe inclusion in "..." YAML scalar.
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


def _emit_block_field(key: str, value: str, *, indicator: str) -> list[str]:
    """Render a multi-line string field with literal-block style (`|` or `|-`).

    Content lines get a fixed 2-space prefix. The parser infers the block
    indent from the first content line, so a content line whose own text begins
    with whitespace would otherwise corrupt the round-trip: the inflated first
    line either raises (a later, less-indented line is judged ambiguous) or
    silently folds a shared leading indent into the block indent. When the first
    content line begins with whitespace, emit an explicit indentation indicator
    (`|2` / `|2-`) that pins the block indent to the 2-space prefix regardless of
    the content's own leading whitespace.
    """
    text = (value or "").rstrip("\n")
    lines = text.splitlines()
    first_content = next((ln for ln in lines if ln.strip()), "")
    if first_content[:1].isspace():
        indicator = f"{indicator[0]}2{indicator[1:]}"
    out = [f"{key}: {indicator}"]
    for ln in lines:
        out.append(f"  {ln}" if ln else "")
    return out


_BLOCK_LIST_FIELDS = frozenset({"advances", "advanced_by", "supersedes", "superseded_by"})


def _emit_worker(value) -> str:
    """Emit the `worker` field value as inline YAML.

    Flat string (`worker: gpu-rig`) when only `who` is set; inline mapping
    (`worker: {who: gpu-rig, where: feature/foo}`) when both are set.
    """
    if value is None:
        return "null"
    if isinstance(value, str):
        return _yaml_inline(value)
    if isinstance(value, dict):
        who = value.get("who", "")
        where = value.get("where")
        if where:
            return f"{{who: {_yaml_inline(who)}, where: {_yaml_inline(where)}}}"
        return _yaml_inline(who)
    return _yaml_inline(str(value))


def emit_frontmatter(fm: dict, *, body: str = "") -> str:
    """Render frontmatter as flat YAML matching the schema's example format.

    `definition_of_done` always uses `|` block style. Every member of
    `_BLOCK_LIST_FIELDS` — the four bidirectional-edge fields `advances`,
    `advanced_by`, `supersedes`, and `superseded_by` — uses block-style lists
    (one `- item` per line) when non-empty; empty lists still render as `[]`.
    `worker` emits as a flat string when only `who` is set, or an inline
    mapping when `where` is also set. Other multi-line strings pick their block
    chomp indicator from the value: `|` (clip) when the value ends in a newline,
    `|-` (strip) when it does not, so the emit->parse round-trip is faithful.
    Single-line strings are rendered inline.
    """
    lines = ["---"]
    for key, value in fm.items():
        if key == "definition_of_done":
            lines.extend(_emit_block_field(key, value or "", indicator="|"))
            continue
        if key in _BLOCK_LIST_FIELDS and isinstance(value, list) and value:
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {_yaml_inline(item)}")
            continue
        if key == "worker":
            lines.append(f"{key}: {_emit_worker(value)}")
            continue
        if (
            isinstance(value, str)
            and "\n" in value
            and not _contains_line_break(value.replace("\n", ""))
        ):
            # Literal-block style faithfully round-trips ONLY LF line breaks:
            # _emit_block_field splits on str.splitlines() and the parser reads
            # the lines back joined with LF, so any *other* break character
            # (CR/VT/FF/...) would be silently rewritten to LF. A value carrying
            # such a character therefore falls through to `_yaml_inline` below,
            # which refuses it at the boundary rather than corrupting it here.
            #
            # Pick the chomp indicator from the value's own trailing-newline
            # state so the emit->parse round-trip is faithful: the parser reads
            # a clip block (`|`) back with one trailing newline and a strip
            # block (`|-`) back with none. Hard-coding `|-` silently dropped a
            # trailing newline (and flipped an authored `|` to `|-`) on every
            # re-emit of a clip-style field such as a multi-line `summary`.
            indicator = "|" if value.endswith("\n") else "|-"
            lines.extend(_emit_block_field(key, value, indicator=indicator))
            continue
        lines.append(f"{key}: {_yaml_inline(value)}")
    lines.append("---")
    out = "\n".join(lines) + "\n"
    if body:
        out += body if body.startswith("\n") else "\n" + body
    return out


def mutate_frontmatter_field(text: str, field_name: str, new_value: str) -> str:
    """Line-anchored regex replacement of `field: <whatever>`.

    Handles both single-line fields (`field: value`) and block-style fields
    (`field:\n  - item`). Avoids YAML round-trip (which reorders keys).
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("no frontmatter found")
    fm_text = m.group(1)
    body = m.group(2)
    # Match the field header and any block continuation that belongs to it.
    # A continuation only opens with an indented line directly after the
    # header, so a flat scalar (`status: x`) followed by a blank line keeps
    # the match on the header alone. Once inside the block, an internal blank
    # line is absorbed only when a further indented line follows it — so a
    # blank line preceding the next top-level `key:` line ends the match
    # instead of swallowing the structural separator (or the line after it).
    pattern = re.compile(
        rf"^{re.escape(field_name)}:[ \t]*[^\n]*"
        rf"(?:\n[ \t]+[^\n]*(?:\n[ \t]+[^\n]*|\n(?=\n*[ \t]))*)?",
        re.MULTILINE,
    )
    if not pattern.search(fm_text):
        # Field absent — append at the end of the frontmatter block.
        fm_text = fm_text.rstrip() + f"\n{field_name}: {new_value}"
    else:
        fm_text = pattern.sub(lambda _: f"{field_name}: {new_value}", fm_text, count=1)
    return f"---\n{fm_text}\n---\n{body}"


DECISION_REQUIRED_RE = re.compile(
    r"^## Decision required[^\n]*\n(.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)


def extract_decision_required_section(body: str) -> str | None:
    """Return the body of the `## Decision required` section, or None if absent."""
    m = DECISION_REQUIRED_RE.search(body)
    return m.group(1).strip() if m else None


# A *resolved* `## Decision` block, as opposed to a pending `## Decision
# required` section. Two shipped forms count as resolved: the bare
# `## Decision` heading `goc decide` writes, and the `## Decision
# (rubric-derived)` heading `Skill(create-card)` pre-writes when the project
# rubric resolves a gate-`none` card. The optional `(…)` qualifier admits the
# rubric-derived form (and any future parenthetical variant); the pending
# `## Decision required` section is still excluded because its heading carries a
# bare word, not a parenthetical, before the newline.
RESOLVED_DECISION_RE = re.compile(
    r"^## Decision(?: \([^)\n]*\))?[ \t]*\n(.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)


def extract_resolved_decision_text(body: str) -> str | None:
    """Return the text of a resolved `## Decision` block, or None if absent."""
    m = RESOLVED_DECISION_RE.search(body)
    return m.group(1).strip() if m else None


# Re-scope / reversal language in a recorded decision. When `goc decide`'s
# `--decision` matches this, the decision is overturning or re-framing a
# verdict the card already states elsewhere (summary, body banner, DoD,
# neighbor references) — surfaces `goc decide` does NOT auto-update. Drives
# both the decide-time reconciliation reminder and the advisory validator
# `validate_decision_verdict_coherence`. See
# goc-decide-leaves-stale-verdict-content-when-recording-a-rescope.
RESCOPE_MARKERS_RE = re.compile(
    r"\b(?:re-?scop\w*|supersed\w*|revers\w*|overturn\w*|no longer|"
    r"instead of|was wrong|now\s+viable|actually\s+viable)\b",
    re.IGNORECASE,
)

# Strong negative-verdict tokens. A summary or body banner carrying one of
# these alongside a re-scope/reversal decision is the self-contradiction we
# flag (a "REFUTED" summary over a "viable" decision). Bare "viable" is
# deliberately absent — only the negated forms count as a negative verdict.
NEGATIVE_VERDICT_RE = re.compile(
    r"\b(?:refuted|disproved|disproven|unviable|not viable|do not pursue|"
    r"don't pursue|does\s+not\s+(?:work|converge)|doesn't\s+(?:work|converge)|"
    r"won't\s+work|will\s+not\s+work)\b",
    re.IGNORECASE,
)


def _body_banner_lines(body: str) -> list[str]:
    """Blockquote (`> …`) banner lines in a card body — the `> ⚠ VERDICT`
    callouts a re-scope can leave stale."""
    return [ln for ln in body.splitlines() if ln.lstrip().startswith(">")]


def replace_or_append_decision(body: str, decision: str, reasoning: str, today: str) -> str:
    """Replace `## Decision required` with `## Decision`, or append a new section.

    The replace branch's regex stops at the lookahead `(?=^## |\\Z)` — it does
    not consume the next `## ` heading, but it does consume the blank line
    that previously separated the deliberation from that heading. The block
    therefore ends in `\\n\\n` so the result keeps a blank line before any
    following section. The append branch's leading `\\n\\n` already gives the
    new block its own separator from prior content; the trailing `\\n\\n` then
    leaves a single trailing blank line at end-of-file, matching the
    prevailing convention.
    """
    block = f"## Decision\n\n*Resolved {today}:* {decision}\n\n*Reasoning:* {reasoning}\n\n"
    if DECISION_REQUIRED_RE.search(body):
        return DECISION_REQUIRED_RE.sub(lambda _: block, body, count=1)
    return body.rstrip("\n") + "\n\n" + block


# ────────────────────────────────────────────────────────────────────────────
# Schema


@dataclass
class Schema:
    required_fields: list[str]
    optional_fields: list[str]
    title_pattern: str
    status_values: list[str]
    stage_values: list  # str or None
    contribution_values: list[str]
    human_gate_values: list[str]
    human_gate_default: str
    waiting_on_values: list[str]
    canonical_tags: set[str]


def load_schema() -> Schema:
    if not SCHEMA_FILE.exists():
        print(f"FATAL: {SCHEMA_FILE} missing", file=sys.stderr)
        sys.exit(3)
    fm = yaml.safe_load(SCHEMA_FILE.read_text()) or {}
    canonical_tags = set(fm.get("canonical_tags") or [])
    canonical_tags |= _load_consuming_repo_tags()
    try:
        return Schema(
            required_fields=fm["required_fields"],
            optional_fields=fm["optional_fields"],
            title_pattern=fm["title_pattern"],
            status_values=fm["status_values"],
            stage_values=fm["stage_values"],
            contribution_values=fm["contribution_values"],
            human_gate_values=fm["human_gate_values"],
            human_gate_default=fm["human_gate_default"],
            waiting_on_values=fm["waiting_on_values"],
            canonical_tags=canonical_tags,
        )
    except KeyError as e:
        print(f"FATAL: schema.yaml missing field {e}", file=sys.stderr)
        sys.exit(3)


_FENCED_YAML = re.compile(r"```ya?ml\n(.*?)```", re.DOTALL)

_UNKNOWN_TAG_REMEDY = (
    "add a project-local tag in .game-of-cards/canonical-tags.md "
    "(under a `canonical_tags:` YAML block, merged by `goc validate`); "
    "for a tag that should ship with goc, open a PR against the goc repo"
)


def _load_consuming_repo_tags() -> set[str]:
    """Merge tags declared in `.game-of-cards/canonical-tags.md`.

    Consuming repos extend goc's canonical_tags set by adding a fenced
    YAML block:

        ```yaml
        canonical_tags:
          - my-project-tag
          - another-tag
        ```

    Multiple blocks accumulate. Missing or empty file: no-op (returns set()).
    """
    extension_file = DECK_ROOT / ".game-of-cards" / "canonical-tags.md"
    if not extension_file.exists():
        return set()
    out: set[str] = set()
    for match in _FENCED_YAML.finditer(extension_file.read_text()):
        block = yaml.safe_load(match.group(1)) or {}
        value = block.get("canonical_tags") or []
        if not isinstance(value, list):
            continue
        out.update(value)
    return out


# ────────────────────────────────────────────────────────────────────────────
# Card model

DOD_OPEN_BOX = re.compile(r"^[ \t]*- \[ \]", re.MULTILINE)
DOD_DONE_BOX = re.compile(r"^[ \t]*- \[x\]", re.MULTILINE | re.IGNORECASE)
# Matches any DoD checkbox line (open or checked), case-insensitive so it
# agrees with DOD_OPEN_BOX + DOD_DONE_BOX on the same `[X]`/`[x]` set.
DOD_ANY_BOX = re.compile(r"^[ \t]*- \[[ xX]\]")

# A ```- or ~~~-fenced code block inside the (block-scalar) definition_of_done
# field shows checkbox lines as *examples*, not real DoD items. The scanners
# below must skip those lines, otherwise an illustrative `- [ ]` inflates the
# unchecked-box count and makes the card impossible to close.
DOD_FENCE_DELIM = re.compile(r"^[ \t]*((`{3,})|(~{3,}))")


def _dod_fenced_mask(lines: list[str]) -> list[bool]:
    """Per-line flag: True when the line opens/closes or sits inside a fenced
    code block, and so must not be treated as a DoD checkbox. All three DoD
    scanners (count_dod_boxes, _dod_box_indices, untagged_dod_items) route
    through this so they cannot drift apart on fence handling.

    Fence matching follows CommonMark §4.5: a block opened with a run of one
    fence character (``` or ~~~) is closed only by a fence of the *same*
    character whose run length is >= the opener's. A ``~~~`` line inside a
    backtick block (or vice versa, or a shorter run) is content, not a close —
    so it stays masked and the mask cannot desynchronize on mismatched fences.
    """
    mask: list[bool] = []
    fence_char: str | None = None  # "`" or "~" while inside a block; None outside
    fence_len = 0
    for ln in lines:
        m = DOD_FENCE_DELIM.match(ln)
        if m:
            run = m.group(1)
            char = run[0]
            length = len(run)
            # Text after the fence run. An opening fence may carry an info
            # string (e.g. ```yaml); a *closing* fence may not (CommonMark
            # §4.5) — it may be followed only by spaces or tabs.
            trailing = ln[m.end():]
            if fence_char is None:
                # Opening fence: remember its character and run length. Any
                # info string after the run is ignored for masking purposes.
                fence_char = char
                fence_len = length
                mask.append(True)
                continue
            if char == fence_char and length >= fence_len and not trailing.strip():
                # Matching closing fence (bare — no info string).
                fence_char = None
                fence_len = 0
                mask.append(True)
                continue
            # A fence delimiter that does not close the current block is just
            # content inside it (e.g. an illustrative ~~~ in a backtick block,
            # or a same-char run bearing an info string like ```yaml).
            mask.append(True)
        else:
            mask.append(fence_char is not None)
    return mask


def _dod_box_indices(lines: list[str]) -> list[int]:
    """0-based line indices of DoD checkbox lines, counted the same way the
    canonical box counter (DOD_OPEN_BOX + DOD_DONE_BOX) counts them — i.e.
    case-insensitively and skipping fenced-code-block lines. This is the index
    space LLM quality-pass verdicts target, so the rewriter must agree with the
    counter on which lines are boxes."""
    fenced = _dod_fenced_mask(lines)
    return [
        i
        for i, ln in enumerate(lines)
        if not fenced[i] and DOD_ANY_BOX.match(ln)
    ]

# Method-class tags declare each DoD item's closure semantic with a one-token
# colon-suffixed prefix (e.g. "- [ ] TDD: ..."). See Skill(card-schema)
# "DoD method tags" for the vocabulary. Detection is line-anchored, matching
# the DOD_*_BOX predicates above.
DOD_METHOD_TAGS = ("TDD", "EMPIRICAL", "MECHANICAL", "PROCESS")
DOD_TAGGED_BOX = re.compile(
    r"^[ \t]*- \[[ xX]\] (?:" + "|".join(DOD_METHOD_TAGS) + r"): "
)


@dataclass
class Card:
    title: str
    path: Path
    frontmatter: dict
    body: str
    dod_open: int
    dod_done: int

    @property
    def dod_freeform(self) -> bool:
        return self.dod_open == 0 and self.dod_done == 0

    @property
    def status(self) -> str:
        return self.frontmatter.get("status", "")

    @property
    def stage(self):
        return self.frontmatter.get("stage")

    @property
    def contribution(self) -> str:
        v = self.frontmatter.get("contribution")
        return "" if v is None else str(v)

    @property
    def human_gate(self) -> str:
        return self.frontmatter.get("human_gate", "")

    @property
    def tags(self) -> list[str]:
        v = self.frontmatter.get("tags")
        return v if isinstance(v, list) else []

    @property
    def created(self) -> str:
        v = self.frontmatter.get("created", "")
        return str(v)

    @property
    def closed_at(self):
        """ISO timestamp the card entered a terminal status (done, disproved,
        or superseded). Null on non-terminal cards. `status` disambiguates
        the outcome — `closed_at` is a single date per terminal exit, not a
        shipped-only marker."""
        return self.frontmatter.get("closed_at")

    @property
    def summary(self) -> str:
        return self.frontmatter.get("summary") or ""

    @property
    def worker(self) -> dict | None:
        """Normalize worker frontmatter to `{who, where?}` dict, or None."""
        v = self.frontmatter.get("worker")
        if v is None:
            return None
        if isinstance(v, str):
            return {"who": v}
        if isinstance(v, dict):
            return v
        return None

    @property
    def waiting_on(self) -> str | None:
        """Stored impediment reason: external, resource, deferred — or None."""
        v = self.frontmatter.get("waiting_on")
        return v if isinstance(v, str) and v else None

    @property
    def waiting_until(self):
        """Optional ISO date the wait is expected to clear. May be set without
        `waiting_on` — a bare `waiting_until` implies `deferred`."""
        return self.frontmatter.get("waiting_until")


def _worker_who(raw) -> str:
    """Extract `who` string from a raw worker frontmatter value (str or dict)."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return str(raw.get("who") or "")
    return ""


def count_dod_boxes(dod_field: str) -> tuple[int, int]:
    if not isinstance(dod_field, str):
        return 0, 0
    lines = dod_field.splitlines()
    fenced = _dod_fenced_mask(lines)
    open_n = done_n = 0
    for ln, in_fence in zip(lines, fenced):
        if in_fence:
            continue
        if DOD_DONE_BOX.match(ln):
            done_n += 1
        elif DOD_OPEN_BOX.match(ln):
            open_n += 1
    return open_n, done_n


def untagged_dod_items(dod_field: str) -> list[str]:
    """Return DoD checkbox lines (stripped) that lack a method-class tag.

    A tagged line carries one of DOD_METHOD_TAGS colon-suffixed right after
    the checkbox. Freeform (non-checkbox) DoD text yields no items.
    """
    if not isinstance(dod_field, str):
        return []
    lines = dod_field.splitlines()
    fenced = _dod_fenced_mask(lines)
    return [
        line.strip()
        for line, in_fence in zip(lines, fenced)
        if not in_fence and DOD_ANY_BOX.match(line) and not DOD_TAGGED_BOX.match(line)
    ]


def load_card(card_dir: Path) -> Card | None:
    """Load a card; return None if the directory has no card-shaped README.md.

    Raises `FrontmatterError` if README.md exists with an opening `---` but
    no matching closer (or YAML inside is unparseable). Callers that want
    a uniform exit-with-diagnostic should use `load_card_or_exit` instead.
    """
    readme = card_dir / "README.md"
    if not readme.exists():
        return None
    fm, body = parse_frontmatter(readme.read_text())
    if not fm:
        return None
    dod_field = fm.get("definition_of_done", "")
    dod_open, dod_done = count_dod_boxes(dod_field)
    return Card(
        title=fm.get("title", card_dir.name),
        path=card_dir,
        frontmatter=fm,
        body=body,
        dod_open=dod_open,
        dod_done=dod_done,
    )


def load_all_cards() -> list[Card]:
    if not DECK_DIR.exists():
        return []
    cards: list[Card] = []
    for sub in sorted(DECK_DIR.iterdir()):
        if not sub.is_dir():
            continue
        try:
            t = load_card(sub)
        except FrontmatterError as exc:
            # Don't let one broken card blank the whole queue — surface a
            # warning per card and skip. `goc validate` reports authoritatively.
            print(f"WARNING: {sub.name}: {exc}", file=sys.stderr)
            continue
        if t is not None:
            cards.append(t)
    return cards


def load_card_or_exit(card_dir: Path, title: str) -> "Card":
    """Load a card or exit(2) with a precise diagnostic.

    Distinguishes four failure modes that previous code collapsed into
    "not found at <path>":
      1. card directory missing
      2. README.md missing
      3. README.md has no opening `---` at line 1 (not a card-shaped file)
      4. frontmatter malformed (opener present, closer missing/invalid YAML)
    """
    if not card_dir.exists():
        print(f"ERROR: {title}: not found at {card_dir}", file=sys.stderr)
        sys.exit(2)
    readme = card_dir / "README.md"
    if not readme.exists():
        print(f"ERROR: {title}: README.md not found at {readme}", file=sys.stderr)
        sys.exit(2)
    try:
        card = load_card(card_dir)
    except FrontmatterError as exc:
        print(
            f"ERROR: {title}: frontmatter parse failed at {readme}: {exc}",
            file=sys.stderr,
        )
        sys.exit(2)
    if card is None:
        print(
            f"ERROR: {title}: README.md at {readme} has no frontmatter "
            f"(missing opening '---' at line 1)",
            file=sys.stderr,
        )
        sys.exit(2)
    return card


# ────────────────────────────────────────────────────────────────────────────
# Validate


_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DATETIME_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _is_iso_date(value) -> bool:
    # Accepts the legacy date-only shape AND the current datetime shape.
    # Lexicographic order is preserved across both: "2026-05-10" sorts
    # before "2026-05-10T00:00:00Z" sorts before "2026-05-11".
    #
    # Shape alone is not enough: the consumers parse with the real calendar
    # (date.fromisoformat / strptime), so a calendar-impossible-but-ISO-shaped
    # value like "2026-13-45" or "2026-05-20T25:61:99Z" would pass a regex-only
    # check yet raise at read time. Match the predicate to the parser by
    # parsing with the SAME calendar the consumer uses — the full timestamp for
    # the datetime shape, not just the date prefix.
    if isinstance(value, date):
        return True
    if not isinstance(value, str):
        return False
    if not (_ISO_DATE_RE.match(value) or _ISO_DATETIME_UTC_RE.match(value)):
        return False
    try:
        if _ISO_DATETIME_UTC_RE.match(value):
            datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        else:
            date.fromisoformat(_date_part(value))
    except ValueError:
        return False
    return True


def _is_date_only(value) -> bool:
    """True when an ISO timestamp carries only day granularity.

    A bare `date` (not its `datetime` subclass) or a `YYYY-MM-DD` string
    names a calendar day, not an instant — callers that compare such a
    value against a full datetime must compare at day granularity rather
    than promoting it to midnight UTC. Returns False for datetimes,
    datetime-shaped strings, and non-ISO values.
    """
    if isinstance(value, datetime):
        return False
    if isinstance(value, date):
        return True
    return isinstance(value, str) and bool(_ISO_DATE_RE.match(value))


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_today() -> date:
    return datetime.now(tz=timezone.utc).date()


def _date_part(value) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    return str(value)


def _waiting_until_instant(value) -> datetime | None:
    """Parse an ISO date/datetime `waiting_until` into a UTC instant.

    A bare date `YYYY-MM-DD` becomes midnight UTC of that day, so a
    date-only deferral clears at the start of its named day exactly as
    before. A datetime `YYYY-MM-DDTHH:MM:SSZ` is honored at full
    precision — the read-time guard no longer rounds the time component
    away. Returns None for anything `_is_iso_date` rejects (the
    malformed-value backstop in `waiting_impedes`).

    `strptime` rather than `datetime.fromisoformat` because the latter
    only accepts the trailing `Z` on Python 3.11+, while this package
    supports 3.10.
    """
    if not _is_iso_date(value):
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    elif _ISO_DATETIME_UTC_RE.match(value):
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    else:
        d = date.fromisoformat(value)
        dt = datetime(d.year, d.month, d.day)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _now_instant(today: "date | datetime | None") -> datetime:
    """Resolve the comparison instant for the read-time wait guards.

    `None` → the live wall clock (`datetime.now(tz=utc)`), the production
    path. A `datetime` is used at full precision. A plain `date` (the
    legacy `today=` test hook) is interpreted as midnight UTC of that day,
    preserving the date-vs-date semantics every existing caller relies on.
    """
    if today is None:
        return datetime.now(tz=timezone.utc)
    if isinstance(today, datetime):
        return today if today.tzinfo is not None else today.replace(tzinfo=timezone.utc)
    return datetime(today.year, today.month, today.day, tzinfo=timezone.utc)


def _format_waiting_until_for_message(value) -> str:
    """Echo the stored `waiting_until` shape for operator-facing messages.

    Bare date (string `YYYY-MM-DD` or `date` instance) stays rendered as
    `YYYY-MM-DD`. Datetime (string `YYYY-MM-DDTHH:MM:SSZ` or `datetime`
    instance) is rendered as its stored UTC instant. The validator's
    rendered output thus agrees with the read guard's full-timestamp
    predicate, all the way through to what the operator reads.
    """
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and _ISO_DATETIME_UTC_RE.match(value):
        return value
    return _date_part(value)


def _format_elapsed(delta: timedelta) -> str:
    """Render an elapsed wait at the coarsest precision that does not lie.

    Under one hour → minutes (`Nm`). Under one day → hours (`Nh`).
    Otherwise → days (`Nd`). Floors to the chosen unit. Matches the
    granularity the docstring at `validate_waiting_overlay` promises the
    read guard preserves: a sub-day overrun is reported as such, not
    collapsed to `0d ago`.
    """
    total = int(delta.total_seconds())
    if total < 3600:
        return f"{total // 60}m"
    if total < 86400:
        return f"{total // 3600}h"
    return f"{total // 86400}d"


LIST_REL_FIELDS = ("advances", "advanced_by", "supersedes", "superseded_by")
ADVANCE_REL_FIELDS = frozenset({"advances", "advanced_by"})
SUPERSEDE_REL_FIELDS = frozenset({"supersedes", "superseded_by"})
INVERSE_REL = {
    "advances": "advanced_by",
    "advanced_by": "advances",
    "supersedes": "superseded_by",
    "superseded_by": "supersedes",
}


@dataclass(frozen=True)
class HalfEdge:
    src: str
    field: str
    ref: str
    inverse: str

    @property
    def message(self) -> str:
        return (
            f"{self.src}: {self.field} contains '{self.ref}' but "
            f"{self.ref}.{self.inverse} is missing '{self.src}' (half-edge)"
        )

    @property
    def repair_title(self) -> str:
        return self.ref

    @property
    def repair_field(self) -> str:
        return self.inverse

    @property
    def repair_value(self) -> str:
        return self.src

    @property
    def is_advance(self) -> bool:
        return self.field in ADVANCE_REL_FIELDS

    @property
    def child_title(self) -> str:
        return self.ref if self.field == "advances" else self.src

    @property
    def parent_title(self) -> str:
        return self.src if self.field == "advances" else self.ref


def validate_deck_directories() -> list[str]:
    """Reject stale deck subdirectories that are not real card directories."""

    if not DECK_DIR.exists():
        return []

    errors: list[str] = []
    for sub in sorted(DECK_DIR.iterdir()):
        if not sub.is_dir():
            continue
        readme = sub / "README.md"
        if not readme.exists():
            if (sub / "REDIRECT.md").exists():
                errors.append(f"{sub.name}: stale card directory contains REDIRECT.md but no README.md")
            else:
                errors.append(f"{sub.name}: card directory missing README.md")
            continue
        try:
            fm, _body = parse_frontmatter(readme.read_text())
        except FrontmatterError as exc:
            errors.append(f"{sub.name}: {exc}")
            continue
        if not fm:
            errors.append(
                f"{sub.name}: README.md has no frontmatter "
                f"(missing opening '---' at line 1)"
            )
    return errors


def validate_skill_dir_parity() -> list[str]:
    """Flag consumer skill dirs (.claude/skills, .codex/skills) missing skills the
    installed goc templates ship. A drift here means the consumer copies were
    written by an older goc version than the one currently resolving templates;
    the fix is `goc upgrade --keep-local-skills`. Extras (user-added skills) are
    allowed and not reported.

    Per-agent filter: skills with another agent's prefix (e.g. `claude-*` for
    the codex tree) are excluded — they are agent-specific complements that
    only ship under their own harness.

    Skipped entirely when the repo's effective `skills_source` is `plugin` —
    in plugin mode `.claude/skills/` is user territory (the user may keep
    non-GoC skills there), and GoC's own skills live under
    `${CLAUDE_PLUGIN_ROOT}/skills/` which this check does not own.
    """
    from goc.install import skill_for_agent

    if effective_skills_source() == "plugin":
        return []

    template_skills = PACKAGE_DIR / "templates" / "skills"
    if not template_skills.exists():
        return []
    all_template = {p.name for p in template_skills.iterdir() if (p / "SKILL.md").is_file()}
    errors: list[str] = []
    for relative, agent in ((".claude/skills", "claude"), (".codex/skills", "codex")):
        consumer_dir = REPO_ROOT / relative
        if not consumer_dir.exists():
            continue
        expected = {s for s in all_template if skill_for_agent(s, agent)}
        actual = {p.name for p in consumer_dir.iterdir() if (p / "SKILL.md").is_file()}
        missing = expected - actual
        if missing:
            errors.append(
                f"{relative}: missing skills {sorted(missing)} that goc templates ship; "
                "run `goc upgrade --keep-local-skills` to resync, or set "
                "`skills_source: plugin` in .game-of-cards/config.yaml to skip this check"
            )
    return errors


def validate_hook_registration() -> list[str]:
    """Check `templates/hooks/*.py` and `GOC_CLAUDE_HOOKS` are in sync.

    The hook copy list and parity pairs are derived from `templates/hooks/`,
    but the event-to-script mapping in `GOC_CLAUDE_HOOKS` stays explicit so
    `'what fires on Stop?'` is answerable from one source-readable file.
    This validator is the tripwire that the explicit mapping requires: it
    catches the silent-failure mode where a hook script lands in
    `templates/hooks/` without an event registration (file copied but never
    invoked), and the inverse where a registration points at a file that
    no longer exists.
    """
    from goc.install import GOC_CLAUDE_HOOKS, _HOOK_FILE_RE, deck_hook_scripts

    templates = PACKAGE_DIR / "templates"
    if not (templates / "hooks").exists():
        return []

    errors: list[str] = []
    scripts = set(deck_hook_scripts(templates))

    registered: set[str] = set()
    for event, command in GOC_CLAUDE_HOOKS.items():
        m = _HOOK_FILE_RE.search(command)
        if not m:
            errors.append(
                f"hook registration: GOC_CLAUDE_HOOKS[{event!r}] command has no "
                f"recognizable script path: {command!r}"
            )
            continue
        name = Path(m.group(1)).name
        registered.add(name)
        if name not in scripts:
            errors.append(
                f"hook registration: GOC_CLAUDE_HOOKS[{event!r}] points to "
                f"templates/hooks/{name} which does not exist"
            )

    for name in sorted(scripts - registered):
        errors.append(
            f"hook registration: templates/hooks/{name} has no event entry in "
            "GOC_CLAUDE_HOOKS — file would be copied to .claude/hooks/ but never "
            "invoked. Add a mapping in goc/install.py."
        )

    return errors


class _DeepDircmp(filecmp.dircmp):
    """`filecmp.dircmp` variant that compares file contents (`shallow=False`).

    The stdlib default declares two files identical when their size, mtime,
    and mode match; a same-length hand-edit to a plugin-mirror file then
    slips past the tripwire (a fresh `git checkout` stamps every working-tree
    file with the same mtime, so the false-same hit is routine on CI). The
    sibling `scripts/sync_plugin_assets.py` already passes `shallow=False`;
    this subclass aligns the engine's directory walk with that contract.
    Subdirectories propagate via `self.__class__` in `phase4`.
    """

    def phase3(self):
        same, diff, funny = filecmp.cmpfiles(
            self.left, self.right, self.common_files, shallow=False
        )
        self.same_files = same
        self.diff_files = diff
        self.funny_files = funny

    methodmap = dict(
        filecmp.dircmp.methodmap,
        same_files=phase3,
        diff_files=phase3,
        funny_files=phase3,
    )


def validate_plugin_mirror_parity() -> list[str]:
    """Check that plugin/ mirrors match their source-of-truth trees byte-for-byte.

    Covers `claude-plugin/`, `codex-plugin/`, and `openclaw-plugin/` when present. Only the
    pairs whose plugin root actually exists at REPO_ROOT are checked, so this
    works in both the goc source repo and downstream consumers.

    Drift means a source-of-truth file was edited without updating the plugin
    mirror; fix is to run `python scripts/sync_plugin_assets.py` and commit
    the result. CI runs the same script with `--check`.

    The flat hook mirrors (`<plugin>/hooks/` ↔ source `goc/templates/hooks/`)
    are compared as whole directories — not per-file pairs enumerated from the
    current template set — so adding a hook updates the parity check
    automatically AND a stale dst-only copy of a renamed/retired hook
    registers as drift. The hand-maintained `hooks.json` is excluded from
    that comparison. Skills are excluded from the deep `goc/` mirror because
    plugin install paths refuse `--local-skills`, so the bundled engine
    never reads `templates/skills/`.

    The OpenClaw plugin's bundled engine reimplements all three deck hooks
    in TypeScript inside `openclaw-plugin/index.ts`, so its deep mirror also
    omits `templates/hooks/*.py`.
    """
    from goc.install import (
        CODEX_GOC_COMMAND_RESOLVER,
        _frontmatter_value,
        deck_hook_scripts,
        skill_for_agent,
    )
    claude_plugin_root = REPO_ROOT / "claude-plugin"
    codex_plugin_root = REPO_ROOT / "codex-plugin"
    openclaw_plugin_root = REPO_ROOT / "openclaw-plugin"
    if (
        not claude_plugin_root.exists()
        and not codex_plugin_root.exists()
        and not openclaw_plugin_root.exists()
    ):
        return []

    def _is_inside_exclude(path: str, exclude: frozenset[str]) -> bool:
        """True if `path` is, or sits under, one of the excluded subpaths."""
        if path in exclude:
            return True
        return any(path.startswith(ex + "/") for ex in exclude)

    def _walk(
        cmp: filecmp.dircmp,
        src_rel: str,
        dst_rel: str,
        prefix: str = "",
        exclude: frozenset[str] = frozenset(),
    ) -> list[str]:
        out: list[str] = []
        out += [
            f"{prefix}{n} (only in {src_rel})"
            for n in cmp.left_only
            if not _is_inside_exclude(prefix + n, exclude)
        ]
        out += [
            f"{prefix}{n} (only in {dst_rel})"
            for n in cmp.right_only
            if not _is_inside_exclude(prefix + n, exclude)
        ]
        out += [
            f"{prefix}{n} (differs)"
            for n in cmp.diff_files
            if (prefix + n) not in exclude
        ]
        for sub_name, sub_cmp in cmp.subdirs.items():
            sub_prefix = prefix + sub_name + "/"
            if sub_prefix.rstrip("/") in exclude:
                continue
            out += _walk(sub_cmp, src_rel, dst_rel, prefix=sub_prefix, exclude=exclude)
        return out

    templates_root = REPO_ROOT / "goc" / "templates"
    hook_names = deck_hook_scripts(templates_root)

    # Skills live flat at `<plugin>/skills/`; the deep `goc/` copy never
    # reads them, so they are excluded from the `goc` ↔ `<plugin>/goc` mirror.
    claude_goc_excludes = frozenset({"templates/skills"})

    # OpenClaw reimplements every deck hook in TypeScript, so its deep mirror
    # also omits the Python hook scripts. Exclude both the directory itself
    # (when missing entirely from the mirror) and each hook file inside it
    # (so partial overlap still surfaces unexpected files as drift).
    openclaw_goc_excludes = claude_goc_excludes | {"templates/hooks"} | frozenset(
        f"templates/hooks/{name}" for name in hook_names
    )

    pairs: list[tuple[Path, Path, frozenset[str]]] = []

    if claude_plugin_root.exists():
        # Non-Claude host complements (e.g. `codex-kickoff`,
        # `openclaw-kickoff`) live in templates/skills/ as the source of truth
        # but must never ship in claude-plugin/skills/. Exclude them from the
        # parity walk so the intentional omission does not register as drift.
        skills_src = templates_root / "skills"
        non_claude_skills = frozenset(
            p.name
            for p in skills_src.iterdir()
            if p.is_dir() and not skill_for_agent(p.name, "claude")
        )
        pairs.append(
            (templates_root / "skills", claude_plugin_root / "skills", non_claude_skills)
        )
        # Whole-directory mirror (not per-file pairs from the current template
        # set) so a dst-only stale hook file registers as drift. `hooks.json`
        # is hand-maintained plugin config with no src counterpart — excluded.
        pairs.append(
            (
                templates_root / "hooks",
                claude_plugin_root / "hooks",
                frozenset({"hooks.json"}),
            )
        )
        pairs.append(
            (REPO_ROOT / "goc", claude_plugin_root / "goc", claude_goc_excludes)
        )

    if codex_plugin_root.exists():
        pairs.append(
            (
                templates_root / "hooks",
                codex_plugin_root / "hooks",
                frozenset({"hooks.json"}),
            )
        )
        pairs.append(
            (REPO_ROOT / "goc", codex_plugin_root / "goc", claude_goc_excludes)
        )

    if openclaw_plugin_root.exists():
        # Only the engine mirror is parity-tracked. Skills are hand-ported
        # (invocation-neutral edits) and hooks are TypeScript ports living
        # in openclaw-plugin/index.ts — neither is a byte-identical copy.
        pairs.append(
            (REPO_ROOT / "goc", openclaw_plugin_root / "goc", openclaw_goc_excludes)
        )

    errors: list[str] = []

    def _codex_skill_text(src: Path, *, skill_name: str) -> str:
        text = src.read_text()
        if not text.startswith("---\n"):
            return text
        try:
            _, frontmatter, body = text.split("---", 2)
        except ValueError:
            return text
        name = _frontmatter_value(frontmatter, "name") or skill_name
        description = _frontmatter_value(frontmatter, "description")
        codex_frontmatter = "\n".join(
            (
                "---",
                f"name: {name}",
                f"description: {json.dumps(description, ensure_ascii=False)}",
                "---",
            )
        )
        return codex_frontmatter + CODEX_GOC_COMMAND_RESOLVER + body

    def _validate_codex_skill_mirror(dst: Path) -> None:
        src = templates_root / "skills"
        eligible = {
            p.name for p in src.iterdir() if p.is_dir() and skill_for_agent(p.name, "codex")
        }
        src_rel = str(src.relative_to(REPO_ROOT))
        dst_rel = str(dst.relative_to(REPO_ROOT))
        if not dst.exists():
            errors.append(f"plugin mirror: {dst_rel} missing; copy from {src_rel}")
            return
        diffs: list[str] = []
        for src_item in sorted(src.rglob("*")):
            if "__pycache__" in src_item.parts or src_item.is_dir():
                continue
            rel = src_item.relative_to(src)
            if rel.parts[0] not in eligible:
                continue
            dst_item = dst / rel
            expected = (
                _codex_skill_text(src_item, skill_name=rel.parts[0])
                if src_item.name == "SKILL.md"
                else src_item.read_text()
            )
            if not dst_item.exists():
                diffs.append(f"{rel.as_posix()} (missing)")
            elif dst_item.read_text() != expected:
                diffs.append(f"{rel.as_posix()} (differs)")
        for dst_item in sorted(dst.rglob("*")):
            if "__pycache__" in dst_item.parts or dst_item.is_dir():
                continue
            rel = dst_item.relative_to(dst)
            if rel.as_posix() == "_goc-bootstrap.sh":
                bootstrap_src = templates_root / "bootstrap" / "_goc-bootstrap.sh"
                if not bootstrap_src.exists():
                    diffs.append(f"{rel.as_posix()} (only in {dst_rel})")
                elif dst_item.read_text() != bootstrap_src.read_text():
                    diffs.append(f"{rel.as_posix()} (differs)")
                continue
            if not rel.parts or rel.parts[0] not in eligible or not (src / rel).exists():
                diffs.append(f"{rel.as_posix()} (only in {dst_rel})")
        if diffs:
            errors.append(
                f"plugin mirror drift: {src_rel} vs {dst_rel}: " + ", ".join(diffs)
            )

    if codex_plugin_root.exists():
        _validate_codex_skill_mirror(codex_plugin_root / "skills")

    for src, dst, exclude in pairs:
        if not src.exists():
            continue
        src_rel = str(src.relative_to(REPO_ROOT))
        dst_rel = str(dst.relative_to(REPO_ROOT))
        if src.is_dir():
            if not dst.exists():
                errors.append(f"plugin mirror: {dst_rel} missing; copy from {src_rel}")
                continue
            diffs = _walk(_DeepDircmp(src, dst), src_rel, dst_rel, exclude=exclude)
            if diffs:
                errors.append(
                    f"plugin mirror drift: {src_rel} vs {dst_rel}: " + ", ".join(diffs)
                )
        else:
            if not dst.exists():
                errors.append(f"plugin mirror: {dst_rel} missing; copy from {src_rel}")
            elif not filecmp.cmp(src, dst, shallow=False):
                errors.append(
                    f"plugin mirror: {dst_rel} differs from {src_rel}; "
                    "re-sync the duplicated file"
                )
    return errors


def validate_card(t: Card, schema: Schema, all_titles: set[str]) -> list[str]:
    errors: list[str] = []
    fm = t.frontmatter

    for f in schema.required_fields:
        if f not in fm:
            errors.append(f"{t.title}: {f}: required field missing")

    if "title" in fm and fm["title"] != t.path.name:
        errors.append(f"{t.title}: title: '{fm['title']}' != dir name '{t.path.name}'")

    if "title" in fm and not re.match(schema.title_pattern, str(fm["title"])):
        errors.append(f"{t.title}: title: does not match {schema.title_pattern!r}")

    if "status" in fm and fm["status"] not in schema.status_values:
        errors.append(f"{t.title}: status: {fm['status']!r} not in {schema.status_values}")

    if "stage" in fm and fm["stage"] not in schema.stage_values:
        errors.append(f"{t.title}: stage: {fm['stage']!r} not in {schema.stage_values}")

    if "contribution" in fm and fm["contribution"] not in schema.contribution_values:
        errors.append(f"{t.title}: contribution: {fm['contribution']!r} not in {schema.contribution_values}")

    if "human_gate" in fm and fm["human_gate"] not in schema.human_gate_values:
        errors.append(f"{t.title}: human_gate: {fm['human_gate']!r} not in {schema.human_gate_values}")

    if "created" in fm and not _is_iso_date(fm["created"]):
        errors.append(f"{t.title}: created: {fm['created']!r} not a valid ISO YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ date")

    closed_at = fm.get("closed_at")
    if closed_at is not None and not _is_iso_date(closed_at):
        errors.append(f"{t.title}: closed_at: {closed_at!r} not null/ISO date/datetime")

    # Cross-field ordering: a card cannot enter a terminal status before it
    # was created. Compare instants (not lexically) so a date-only `created`
    # and a same-day datetime `closed_at` sort correctly. Both parses must
    # succeed — a value that already failed its shape check above is skipped
    # so the comparison never crashes. When either operand is a bare date,
    # only the calendar day is known: compare at day granularity so a
    # same-day close with a sub-day `created` datetime (whose bare-date
    # `closed_at` promotes to that day's midnight) isn't spuriously flagged.
    # Genuine inversions — an earlier `closed_at` day, or a both-datetime
    # intra-day reversal — still fire.
    created_value = fm.get("created")
    if created_value is not None and closed_at is not None:
        created_instant = _waiting_until_instant(created_value)
        closed_instant = _waiting_until_instant(closed_at)
        if created_instant is not None and closed_instant is not None:
            if _is_date_only(created_value) or _is_date_only(closed_at):
                predates = closed_instant.date() < created_instant.date()
            else:
                predates = closed_instant < created_instant
        else:
            predates = False
        if predates:
            errors.append(
                f"{t.title}: closed_at: {closed_at!r} predates created "
                f"{created_value!r} (a card cannot close before it was created)"
            )

    if "definition_of_done" in fm and not isinstance(fm["definition_of_done"], str):
        errors.append(f"{t.title}: definition_of_done: must be a string")

    tags = fm.get("tags") or []
    if not isinstance(tags, list):
        errors.append(f"{t.title}: tags: must be a list")
    else:
        for tag in tags:
            if tag not in schema.canonical_tags:
                errors.append(
                    f"{t.title}: tags: unknown tag '{tag}' — {_UNKNOWN_TAG_REMEDY}"
                )

    status_value = fm.get("status")
    if status_value in TERMINAL_STATUSES:
        if closed_at is None:
            errors.append(f"{t.title}: closed_at: must be set when status={status_value}")
        if status_value == "done" and t.dod_open > 0:
            errors.append(f"{t.title}: definition_of_done: status=done with {t.dod_open} unchecked boxes")
        gate_value = fm.get("human_gate")
        if gate_value not in (None, "none"):
            errors.append(
                f"{t.title}: human_gate: must be 'none' when status={status_value} "
                f"(got {gate_value!r}); run `goc decide` to resolve the gate before closing."
            )
    elif closed_at is not None:
        errors.append(
            f"{t.title}: closed_at: must be null when status is non-terminal"
            f" (status={status_value!r}, closed_at={closed_at!r})"
        )

    summary_value = fm.get("summary")
    if summary_value is not None:
        if not isinstance(summary_value, str):
            errors.append(f"{t.title}: summary: must be a string")
        elif not summary_value.strip():
            errors.append(f"{t.title}: summary: must not be empty or whitespace-only")

    worker = fm.get("worker")
    if worker is not None:
        if isinstance(worker, str):
            if not worker.strip():
                errors.append(f"{t.title}: worker: must not be empty or whitespace-only")
        elif isinstance(worker, dict):
            if "who" not in worker:
                errors.append(f"{t.title}: worker: mapping must have a 'who' key")
            elif not isinstance(worker.get("who"), str) or not worker["who"].strip():
                errors.append(f"{t.title}: worker: 'who' must be a non-empty, non-whitespace string")
            if "where" in worker and (
                not isinstance(worker.get("where"), str) or not worker["where"].strip()
            ):
                errors.append(
                    f"{t.title}: worker: 'where' must be a non-empty, non-whitespace string"
                )
        else:
            errors.append(f"{t.title}: worker: must be a string or mapping with 'who'")

    if "waiting_on" in fm and fm["waiting_on"] is not None:
        if fm["waiting_on"] not in schema.waiting_on_values:
            errors.append(
                f"{t.title}: waiting_on: {fm['waiting_on']!r} not in {schema.waiting_on_values}"
            )
    if "waiting_until" in fm and fm["waiting_until"] is not None:
        if not _is_iso_date(fm["waiting_until"]):
            errors.append(
                f"{t.title}: waiting_until: {fm['waiting_until']!r} not a valid ISO YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ date"
            )

    for field in LIST_REL_FIELDS:
        v = fm.get(field) or []
        if v and not isinstance(v, list):
            errors.append(f"{t.title}: {field}: must be a list")
            continue
        for ref in v:
            if ref == t.title:
                errors.append(f"{t.title}: {field}: self-reference '{ref}'")
            elif ref not in all_titles:
                errors.append(f"{t.title}: {field}: references unknown title '{ref}'")

    superseded_by = fm.get("superseded_by") or []
    if isinstance(superseded_by, list) and superseded_by and status_value != "superseded":
        errors.append(
            f"{t.title}: superseded_by: non-empty requires status: superseded "
            f"(status={status_value!r})"
        )
    if status_value == "superseded" and not superseded_by:
        errors.append(
            f"{t.title}: status: superseded requires non-empty superseded_by "
            f"(forward routing pointer; set via `goc status {t.title} superseded --by <new>`)"
        )

    return errors


def validate_bidirectional_edges(cards: list[Card]) -> list[str]:
    """Enforce that advances↔advanced_by and supersedes↔superseded_by
    edges are mutually consistent.

    A.advances=[B] requires B.advanced_by to contain A; the inverse must
    also hold. The same invariant applies to supersedes/superseded_by:
    A.superseded_by=[B] requires B.supersedes to contain A. Half-edges
    are an integrity bug — surface them so they can be repaired.
    """
    return [edge.message for edge in find_half_edges(cards)]


def validate_supersedes_targets(cards: list[Card]) -> list[str]:
    """Enforce that every card in `supersedes` is itself `status: superseded`.

    The record axis treats `supersedes` as the typed forward pointer that
    replaces a closed card. A card cannot supersede something that is not
    actually closed-as-replaced; otherwise the link is meaningless. This
    check runs in `goc validate` and fires once per dangling-status pair.
    """
    by_title = {t.title: t for t in cards}
    errors: list[str] = []
    for t in cards:
        refs = t.frontmatter.get("supersedes") or []
        if not isinstance(refs, list):
            errors.append(
                f"{t.title}: supersedes: must be a list, got "
                f"{type(refs).__name__} value={refs!r}; a bare-string "
                f"scalar is iterated character-by-character and silently "
                f"matches single-character titles"
            )
            continue
        for ref in refs:
            target = by_title.get(ref)
            if target is None:
                continue
            if target.status != "superseded":
                errors.append(
                    f"{t.title}: supersedes: '{ref}' is not status: superseded "
                    f"(target.status={target.status!r}); a typed supersession "
                    f"pointer requires the replaced card to be marked superseded"
                )
    return errors


def validate_superseded_by_targets(cards: list[Card]) -> list[str]:
    """Type-guard `superseded_by`: it must be a list, not a bare string.

    A bare-string scalar is iterated character-by-character and silently
    matches single-character titles, so it earns a distinct diagnostic
    rather than the generic "must be a list" message — symmetric with the
    same guard in `validate_supersedes_targets`.

    The forward routing target may carry ANY status. A supersession's
    successor is the live work that replaces the old card, and that work
    is *meant to be completed* — so a `superseded_by` pointer legitimately
    lands on a `done` card (the replacement finished: the walk has reached
    the resolution, not a dead end), a `superseded` card (the chain routes
    onward through that card's own `superseded_by`), or a live
    `open`/`active` card. Requiring a *live* target would make the
    successor of every supersession permanently un-closeable and would
    contradict the record-axis contract (AGENTS.md: edges are walked and
    integrity enforced "regardless of either endpoint's status").
    Referential integrity — the target must *exist* — is enforced
    generically for every relationship field in `validate_card`.
    """
    errors: list[str] = []
    for t in cards:
        refs = t.frontmatter.get("superseded_by") or []
        if not isinstance(refs, list):
            errors.append(
                f"{t.title}: superseded_by: must be a list, got "
                f"{type(refs).__name__} value={refs!r}; a bare-string "
                f"scalar is iterated character-by-character and silently "
                f"matches single-character titles"
            )
    return errors


def find_half_edges(cards: list[Card]) -> list[HalfEdge]:
    """Return structured bidirectional-edge asymmetries (advances↔advanced_by, supersedes↔superseded_by)."""
    half_edges: list[HalfEdge] = []
    by_title = {t.title: t for t in cards}
    for t in cards:
        for field, inverse in INVERSE_REL.items():
            v = t.frontmatter.get(field) or []
            if not isinstance(v, list):
                continue
            for ref in v:
                other = by_title.get(ref)
                if other is None:
                    continue
                inverse_list = other.frontmatter.get(inverse) or []
                if not isinstance(inverse_list, list):
                    inverse_list = []
                if t.title not in inverse_list:
                    half_edges.append(HalfEdge(t.title, field, ref, inverse))
    return half_edges


def detect_advance_cycles(cards: list[Card]) -> list[str]:
    by_title = {t.title: t for t in cards}
    errors: list[str] = []
    for start in cards:
        seen: set[str] = set()
        stack: list[str] = [start.title]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            t = by_title.get(cur)
            if t is None:
                continue
            advanced_by = t.frontmatter.get("advanced_by") or []
            if not isinstance(advanced_by, list):
                continue
            for b in advanced_by:
                if b == start.title and cur != start.title:
                    errors.append(f"{start.title}: advanced_by: cycle detected through {cur} → {b}")
                stack.append(b)
    return errors


def _would_create_advance_cycle(cards: list[Card], title: str, advancer: str) -> bool:
    """Return True if adding `title.advanced_by += advancer` would create a cycle.

    The proposed edge is advancer→title in the advances direction.  A cycle
    exists when title can already reach advancer by following existing advances
    edges — closing that path back to advancer would form a loop.
    """
    by_title = {c.title: c for c in cards}
    seen: set[str] = set()
    stack: list[str] = [title]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        card = by_title.get(cur)
        if card is None:
            continue
        advances = card.frontmatter.get("advances") or []
        if not isinstance(advances, list):
            continue
        for a in advances:
            if a == advancer:
                return True
            stack.append(a)
    return False


def detect_supersedes_cycles(cards: list[Card]) -> list[str]:
    """Return cycle errors in the supersession (superseded_by) routing graph.

    The forward routing pointer a cold reader follows is `superseded_by`
    (A.superseded_by=[B] means "A was replaced by B; go to B"). A cycle in
    that graph makes the forward walk non-terminating. Mirror of
    `detect_advance_cycles` over the supersession edge set.
    """
    by_title = {t.title: t for t in cards}
    errors: list[str] = []
    for start in cards:
        seen: set[str] = set()
        stack: list[str] = [start.title]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            t = by_title.get(cur)
            if t is None:
                continue
            superseded_by = t.frontmatter.get("superseded_by") or []
            if not isinstance(superseded_by, list):
                continue
            for b in superseded_by:
                if b == start.title and cur != start.title:
                    errors.append(f"{start.title}: superseded_by: cycle detected through {cur} → {b}")
                stack.append(b)
    return errors


def _would_create_supersedes_cycle(cards: list[Card], title: str, successor: str) -> bool:
    """Return True if adding `title.superseded_by += successor` would cycle.

    The proposed edge routes title→successor (title was replaced by
    successor). A cycle exists when successor can already reach title by
    following existing `superseded_by` edges — closing that path back to
    title would form a loop in the forward-routing graph. Analog of
    `_would_create_advance_cycle` for the supersession edge set.
    """
    by_title = {c.title: c for c in cards}
    seen: set[str] = set()
    stack: list[str] = [successor]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        card = by_title.get(cur)
        if card is None:
            continue
        succs = card.frontmatter.get("superseded_by") or []
        if not isinstance(succs, list):
            continue
        for s in succs:
            if s == title:
                return True
            stack.append(s)
    return False


@dataclass(frozen=True)
class BlockerWarning:
    klass: str
    card: str
    detail: str

    @property
    def message(self) -> str:
        return f"WARN {self.klass} {self.card}: {self.detail}"


def validate_waiting_overlay(cards: list[Card], *, today: "date | datetime | None" = None) -> list[BlockerWarning]:
    """Surface elapsed-wait impediments — the Kanban SLE escalation signal.

    A non-terminal card whose `waiting_until` is in the past has overrun
    its expected return; the wait is no longer plausibly self-clearing
    and should be re-triaged. Closed cards are exempt (the historical
    date is a record, not an SLE).

    The elapsed test uses the same full-timestamp comparison as
    `waiting_impedes`: a datetime-form wait is not reported as overdue
    until its named instant actually passes, so the read guard and this
    validator agree on when a deferral has elapsed.
    """
    now = _now_instant(today)
    warnings: list[BlockerWarning] = []
    for c in cards:
        if c.status in TERMINAL_STATUSES:
            continue
        until = c.waiting_until
        if until is None:
            continue
        # Skip values the frontmatter validator already rejects rather than
        # parsing them by prefix-truncation: a garbage value like
        # "2026-05-20xx" would otherwise turn into a valid past date and emit
        # a spurious WAITING_OVERDUE. The invalid shape is surfaced by the
        # main frontmatter validation, not here.
        until_dt = _waiting_until_instant(until)
        if until_dt is None:
            continue
        if until_dt > now:
            continue
        reason = c.waiting_on or "deferred"
        warnings.append(BlockerWarning(
            "WAITING_OVERDUE",
            c.title,
            f"waiting_on={reason} waiting_until={_format_waiting_until_for_message(until)} "
            f"elapsed {_format_elapsed(now - until_dt)} ago — re-triage or clear",
        ))
    return warnings


CASCADE_ROOT_THRESHOLD = 3
BACKWARDS_EPIC_MIN_TARGETS = 2


def validate_epic_edge_direction(cards: list[Card]) -> list[BlockerWarning]:
    """Advisory hint for the backwards-aggregation-epic signature.

    Canonical aggregation: a child has `child.advances: [epic]`, so the
    epic aggregates upward via `advanced_by`. The intuitive-but-wrong
    shape is `epic.advances: [children]`, which (1) defeats the value
    law (children don't inherit the epic's value) and (2) trips a
    spurious `advanced-by-closed` FAIL on every child at attest time.
    See `Skill(card-schema)` "Coordinating cards — aggregation epic vs
    governing cluster" for the three-way fork and the fix options.

    Heuristic: a non-terminal card with at least
    BACKWARDS_EPIC_MIN_TARGETS resolved `advances` targets where the
    *majority* are strictly lower contribution (higher
    CONTRIBUTION_ORDER number) than the card itself. Uses the
    contribution gradient — not a bare `advances ≥ N` count — so
    legitimate hubs that advance equal-or-higher contribution targets
    pass clean.

    Fix suggestion is shape-sensitive:

    - `human_gate == "decision"` (governing cluster — closes on its own
      deliverable) → drop the edge, group with a shared tag.
    - otherwise (aggregation epic — closes when its children close) →
      flip to `child.advances:[card]`.

    Advisory only: the message is emitted but does not contribute to
    `validate`'s exit code.
    """
    by_title = {c.title: c for c in cards}
    warnings: list[BlockerWarning] = []
    for c in cards:
        if c.status in TERMINAL_STATUSES:
            continue
        targets = c.frontmatter.get("advances") or []
        if not isinstance(targets, list):
            continue
        resolved = [by_title[t] for t in targets if t in by_title]
        if len(resolved) < BACKWARDS_EPIC_MIN_TARGETS:
            continue
        own_rank = CONTRIBUTION_ORDER.get(c.contribution)
        if own_rank is None:
            continue
        lower = [
            t for t in resolved
            if CONTRIBUTION_ORDER.get(t.contribution, own_rank) > own_rank
        ]
        if len(lower) * 2 <= len(resolved):
            continue
        sample = ", ".join(f"{t.title}({t.contribution})" for t in lower[:3])
        if c.human_gate == "decision":
            fix = (
                "card looks like a governing cluster (human_gate: decision) — "
                "drop the edge and group via a shared tag"
            )
        else:
            fix = (
                "if closure waits on the work, flip to `child.advances:[card]` "
                "(`goc unadvance <card> --by <child>` then `goc advance <child> "
                "--by <card>`); if card closes on its own deliverable, drop the "
                "edge and use a shared tag"
            )
        warnings.append(BlockerWarning(
            "BACKWARDS_EPIC_EDGE",
            c.title,
            f"contribution={c.contribution} but advances targets are "
            f"predominantly lower: [{sample}] — likely backwards aggregation "
            f"epic. Fix: {fix}. See Skill(card-schema) 'Coordinating cards'.",
        ))
    return warnings


def validate_blocker_coherence(cards: list[Card]) -> list[BlockerWarning]:
    """Return non-fatal warnings about cards whose `status` is inconsistent
    with their blocker graph.

    Three warning classes, all advisory — none contributes to `validate`'s
    exit code:

    - STALE_BLOCKED: `status: blocked` with `advanced_by` non-empty whose
      entries all sit in TERMINAL_STATUSES. No active prereq remains; the
      card should flip to `open` or its blocker list should be refreshed.
      With derived dependency-readiness (`card_is_ready` /
      `dependency_blocked`), the recommended pattern is to leave the card
      `open` and let the queue hide it via the derived predicate — so the
      card self-clears the moment its last prereq closes. This warning
      remains as a migration aid for cards still using the legacy
      `status: blocked` for a dependency wait.
    - ORPHAN_BLOCKED: `status: blocked` with empty `advanced_by` and
      `human_gate == "none"`. The real blocker is body-only and invisible
      to graph walkers. Suppressed for raised gates because the gate
      itself already names the bottleneck (Option B from the spec, extended
      from `decision` to any raised gate).
    - CASCADE_CHAIN_ROOT: a `human_gate != "none"` card whose `advances`
      transitively reach at least CASCADE_ROOT_THRESHOLD blocked cards.
      One human action at the root cascade-unblocks the whole subtree
      (Lean Andon — surface the cord, not the leaf).
    """
    by_title = {c.title: c for c in cards}
    warnings: list[BlockerWarning] = []

    # Reverse adjacency: title -> [cards that list title in their advanced_by].
    # A card is "downstream of X" when X advances it; equivalently, X.title
    # appears in card.advanced_by.
    unblocks: dict[str, list[str]] = {c.title: [] for c in cards}
    for c in cards:
        prereqs = c.frontmatter.get("advanced_by") or []
        if not isinstance(prereqs, list):
            continue
        for prereq in prereqs:
            if prereq in unblocks:
                unblocks[prereq].append(c.title)

    for c in cards:
        if c.status != "blocked":
            continue
        blockers = c.frontmatter.get("advanced_by") or []
        if not isinstance(blockers, list):
            blockers = []
        if not blockers:
            if c.human_gate == "none":
                warnings.append(BlockerWarning(
                    "ORPHAN_BLOCKED",
                    c.title,
                    "status: blocked with empty advanced_by and human_gate: none "
                    "(hoist blocker into advanced_by, raise the gate, or unblock)",
                ))
            continue
        blocker_statuses = [(b, by_title[b].status) for b in blockers if b in by_title]
        if blocker_statuses and all(s in TERMINAL_STATUSES for _, s in blocker_statuses):
            detail = ", ".join(f"{b}={s}" for b, s in blocker_statuses)
            warnings.append(BlockerWarning(
                "STALE_BLOCKED",
                c.title,
                f"all advanced_by entries inactive: [{detail}]",
            ))

    for root in cards:
        if root.human_gate == "none":
            continue
        cluster: set[str] = set()
        stack = list(unblocks.get(root.title, []))
        while stack:
            title = stack.pop()
            if title in cluster:
                continue
            descendant = by_title.get(title)
            if descendant is None or descendant.status != "blocked":
                continue
            cluster.add(title)
            stack.extend(unblocks.get(title, []))
        if len(cluster) >= CASCADE_ROOT_THRESHOLD:
            warnings.append(BlockerWarning(
                "CASCADE_CHAIN_ROOT",
                root.title,
                f"{len(cluster)} blocked cards rooted here (gate={root.human_gate})",
            ))

    return warnings


def validate_dod_method_tags(cards: list[Card]) -> list[BlockerWarning]:
    """Surface DoD checkboxes that lack a method-class tag prefix.

    Each DoD item should declare its closure semantic with a one-token
    colon-suffixed prefix — TDD / EMPIRICAL / MECHANICAL / PROCESS — so a
    cold reader can tell a must-pass assertion from a must-run-and-record
    experiment without parsing prose. Warning-only and migration-safe:
    legacy untagged cards stay valid; the warning only nudges new
    authorship. Closed cards are exempt (historical record, not live
    authoring). See Skill(card-schema) "DoD method tags".
    """
    warnings: list[BlockerWarning] = []
    for c in cards:
        if c.status in TERMINAL_STATUSES:
            continue
        untagged = untagged_dod_items(c.frontmatter.get("definition_of_done") or "")
        if not untagged:
            continue
        sample = "; ".join(item[:50] for item in untagged[:3])
        more = f" (+{len(untagged) - 3} more)" if len(untagged) > 3 else ""
        warnings.append(BlockerWarning(
            "UNTAGGED_DOD_ITEM",
            c.title,
            f"{len(untagged)} DoD item(s) lack a method tag "
            f"(TDD:/EMPIRICAL:/MECHANICAL:/PROCESS:): [{sample}]{more}",
        ))
    return warnings


def validate_decision_verdict_coherence(cards: list[Card]) -> list[BlockerWarning]:
    """Surface the self-contradiction `goc decide` leaves behind on an in-place
    re-scope: a resolved `## Decision` that re-scopes/reverses a prior verdict
    while the card's summary or a body banner still asserts that (negative)
    verdict.

    Advisory only — never contributes to `validate`'s exit code. The trigger is
    deliberately narrow to stay low-false-positive: the recorded decision must
    *literally* contain re-scope/reversal language (`RESCOPE_MARKERS_RE`), AND a
    strong negative-verdict token (`NEGATIVE_VERDICT_RE`) must survive in the
    summary or a `> …` banner. Terminal cards are exempt — a `disproved` card
    legitimately states a negative verdict. The decide-time reconciliation
    reminder is the point-of-action guard; this validator is the safety net for
    the record (a re-scope recorded before the reminder existed, or one whose
    operator skipped the reconciliation). See
    goc-decide-leaves-stale-verdict-content-when-recording-a-rescope.
    """
    warnings: list[BlockerWarning] = []
    for c in cards:
        if c.status in TERMINAL_STATUSES:
            continue
        decision_text = extract_resolved_decision_text(c.body)
        if not decision_text or not RESCOPE_MARKERS_RE.search(decision_text):
            continue
        surfaces = [c.summary or "", *_body_banner_lines(c.body)]
        hit = next((m for m in (NEGATIVE_VERDICT_RE.search(s) for s in surfaces) if m), None)
        if hit is None:
            continue
        warnings.append(BlockerWarning(
            "DECISION_CONTRADICTS_VERDICT",
            c.title,
            f"resolved ## Decision re-scopes/reverses a prior verdict, but the "
            f"summary/banner still asserts it (token: {hit.group(0)!r}) — "
            f"reconcile the summary/banner, or supersede+create instead",
        ))
    return warnings


# ────────────────────────────────────────────────────────────────────────────
# Filtering + sorting

# Enum membership/order constants derive from schema.yaml — the documented
# single source of truth — so a value added to (or reordered in) the schema
# flows here without a parallel literal edit. Hardcoding these is the drift
# family closed by `schema-enum-surfaces-keep-drifting-into-hardcoded-literals`;
# `tests/test_schema_enum_surface_parity.py` guards against re-introducing one.
# TERMINAL_STATUSES is NOT a schema enum: "terminal" is a semantic subset
# (closure-bearing statuses) the schema does not declare, so it stays a literal.
_ENUM_SCHEMA = load_schema()
STATUS_VALUES = tuple(_ENUM_SCHEMA.status_values)
STATUS_FILTER_VALUES = (*STATUS_VALUES, "all")
MUTABLE_STATUS_VALUES = tuple(status for status in STATUS_VALUES if status != "done")
TERMINAL_STATUSES = frozenset({"done", "disproved", "superseded"})
CONTRIBUTION_ORDER = {c: i for i, c in enumerate(_ENUM_SCHEMA.contribution_values)}
# schema stage_values carries a YAML `null` first entry (the "no stage" state);
# STAGE_ORDER renders it as the string "null" the CLI/filters compare against.
STAGE_ORDER = ["null" if v is None else v for v in _ENUM_SCHEMA.stage_values]


def dependency_blockers(card: Card, by_title: dict[str, Card]) -> list[str]:
    """Return the subset of `card.advanced_by` whose status is non-terminal.

    A non-empty list means the card is dependency-blocked: at least one
    upstream prereq has not reached a terminal status yet. Unknown titles
    are treated as non-terminal (a dangling reference is conservatively
    a blocker until the validator reconciles it).
    """
    blockers: list[str] = []
    prereqs = card.frontmatter.get("advanced_by") or []
    if not isinstance(prereqs, list):
        return []
    for prereq in prereqs:
        upstream = by_title.get(prereq)
        if upstream is None or upstream.status not in TERMINAL_STATUSES:
            blockers.append(prereq)
    return blockers


def dependency_blocked(card: Card, by_title: dict[str, Card]) -> bool:
    """True iff the card has at least one non-terminal `advanced_by` prereq.

    Derived from the advances graph at read time — no stored `blocked`
    status required. A card self-clears the moment its last prereq closes.
    """
    return bool(dependency_blockers(card, by_title))


def dependency_advisory(
    card: Card, by_title: dict[str, Card]
) -> tuple[list[str], bool]:
    """Liveness-gated dependency advisory for the renderers.

    The "awaiting: X — you may start" advisory is a *display* of
    `dependency_blockers` / `dependency_blocked` that is meaningless on
    a terminal card: a `done`/`disproved`/`superseded` card never
    "starts", so a leftover advisory is just stale noise (and shipped as
    a bug twice — once each in the table and JSON renderers). This helper
    applies the `status not in TERMINAL_STATUSES` gate once so every
    renderer consumes a pre-gated result instead of re-inlining it.

    Returns `([], False)` for terminal cards, else
    `(blockers, bool(blockers))`.
    """
    if card.status in TERMINAL_STATUSES:
        return [], False
    blockers = dependency_blockers(card, by_title)
    return blockers, bool(blockers)


def card_is_ready(card: Card, by_title: dict[str, Card]) -> bool:
    """Composite "ready-to-pull" predicate used by next-card / pull-card.

    Ready iff `status == open` AND `human_gate == none` AND no active
    impediment overlay (`waiting_on` unset, `waiting_until` absent or
    past).

    Non-terminal `advanced_by` prereqs do NOT block readiness — an
    `advances` edge is a "should be done first" (value-flow + closure
    gate + soft priority bias), not a "must wait to start". The hard
    "must wait to start" signal is the explicit impediment overlay
    (`waiting_on` / `waiting_until`). See `dependency_blockers` /
    `dependency_blocked`, which remain as advisory display only.

    Paired with `card_is_workable_for_scheduler` — the queue axis vs.
    the scheduler axis. A future axis added here must be added there in
    the same edit; `tests/test_scheduler_workable_predicate_coupling.py`
    fails loud on drift.
    """
    if card.status != "open":
        return False
    if card.human_gate != "none":
        return False
    if waiting_impedes(card):
        return False
    return True


def card_is_workable_for_scheduler(card: Card) -> bool:
    """True iff a descendant may amplify an ancestor's GRPW value.

    Mirrors `card_is_ready` for the scheduler axis: `card_is_ready`
    minus the `status == "open"` clause. `active` descendants stay
    workable because the scheduler walks live work, not just queueable
    work; a terminal, impediment-hidden, or human-gate-parked descendant
    contributes zero to a live ancestor's priority and is pruned.

    Consulted by both descendant-walk sites — `value_for` in
    `compute_values` and `live_direct` in `sort_default` — so the
    live-AND-workable rule is defined once. A future axis added to
    `card_is_ready` must be added here in the same edit;
    `tests/test_scheduler_workable_predicate_coupling.py` enforces this
    invariant.
    """
    if card.status in TERMINAL_STATUSES:
        return False
    if card.human_gate != "none":
        return False
    if waiting_impedes(card):
        return False
    return True


def waiting_impedes(card: Card, *, today: "date | datetime | None" = None) -> bool:
    """True iff the card carries an active impediment overlay.

    Two stored signals contribute:

    - A `waiting_on` reason without an elapsed `waiting_until` means the
      block is ongoing (no expected return date, or the date is in the
      future) and the card is hidden from queues.
    - A `waiting_until` in the future implies a `deferred` wait and
      hides the card until that instant passes.

    When `waiting_until` is in the past (elapsed), the card RE-ENTERS the
    queue with no manual action — the elapsed-wait is then surfaced
    separately by `validate_waiting_overlay` as an SLE escalation signal.

    `waiting_until` is compared at full timestamp precision: a datetime
    shape (`YYYY-MM-DDTHH:MM:SSZ`) clears at its named instant, not at
    the start of its civil day. A bare date `YYYY-MM-DD` is midnight UTC,
    so date-only deferrals clear exactly as before. The `today=` hook
    accepts a `date` (the legacy form, read as midnight UTC) or a
    `datetime` (a precise instant) for tests; default is the live clock.
    """
    now = _now_instant(today)
    reason = card.waiting_on
    until = card.waiting_until
    until_dt: datetime | None = None
    until_unparseable = False
    if until is not None:
        until_dt = _waiting_until_instant(until)
        if until_dt is None:
            # Malformed date: a present-but-unparseable waiting_until signals
            # deferral intent we cannot evaluate. Err on the side of impeding
            # so the card is not silently un-deferred — for a bare deferral
            # (no reason) as well as alongside a waiting_on. `goc validate`
            # is the upstream net (rejects calendar-impossible shapes); this
            # is the read-time backstop for pre-validate / hand-edited decks.
            # `_waiting_until_instant` gates on _is_iso_date — not a bare
            # parse try/except — so garbage whose first 10 chars happen to be
            # a valid date ("2026-05-20xx") does not slip past the backstop.
            until_unparseable = True
    if reason is None and until_dt is None:
        return until_unparseable
    if until_dt is None:
        # Reason set, no date — open-ended wait; hide from queue.
        return True
    # Future instant hides; elapsed instant resurfaces the card.
    return until_dt > now

# GRPW sort: per-card contribution composes through the `advances` graph
# into a `value` score with Bellman discount γ per hop. See
# deck/goc-rename-blocks-to-advances-and-design-value-sort/ for the
# RCPSP literature precedent (Hartmann 1999) and the May 3 design
# discussion. log-spaced ranks are RICE-derived (Intercom): a `high`
# dominates three `medium`s when both reach the same downstream sink.
# Log-spaced (base-3) ranks derived from contribution order: each level
# dominates three of the next (a `high` outscores three `medium`s reaching
# the same sink). Position 0 is the strongest, so rank = 3^(N-1-index) —
# {high: 9.0, medium: 3.0, low: 1.0} for the shipped three-level enum.
CONTRIBUTION_RANK: dict[str, float] = {
    c: 3.0 ** (len(CONTRIBUTION_ORDER) - 1 - i) for c, i in CONTRIBUTION_ORDER.items()
}
GAMMA = 0.7


_DANGLING_ADVANCES_WARNED: set[tuple[str, str]] = set()


def compute_values(cards: list[Card]) -> dict[str, tuple[float, list[str]]]:
    """Compute (value, top_path) for each card via memoized DFS.

    `value(c) = rank(c) + γ · max(value(d) for d in advances(c))`

    Additive Bellman: a card's value is its own contribution PLUS the
    geometrically-discounted strongest-descendant chain. Chain depth
    is a curation signal — wiring an edge requires anchoring two card
    bodies, so longer chains reflect more validated value-flow. With
    γ=0.7, value is bounded asymptotically by `max_rank / (1 - γ)`
    (≈ 30 for our rank table), so growth is geometric not unbounded.

    Live-and-workable descendants: a descendant is skipped from the
    value walk when it is either (a) terminal in status
    (`done`/`disproved`/`superseded`), (b) carrying an active impediment
    overlay (`waiting_impedes` — a `waiting_on` reason or a future
    `waiting_until`), or (c) parked behind a `human_gate` of `decision`
    or `session`. The prune mirrors every gate in `card_is_ready` (the
    pull-queue predicate) except its `status == "open"` clause —
    `active` descendants stay workable for the scheduler axis. The
    scheduler axis walks `advances` across *live, workable* cards only
    (AGENTS.md "deck as scheduler vs record"). Completed work can no
    longer be unblocked, an impeded descendant cannot be pulled for the
    duration of its wait, and a gate-parked descendant cannot be pulled
    until the human lowers the gate — so none may amplify a live card's
    scheduling priority. Terminal edges belong to the record axis
    instead; the impediment and human-gate prunes are self-clearing (an
    elapsed `waiting_until`, a cleared `waiting_on`, or a `decide-card`
    invocation re-admits the descendant on the next recompute, no manual
    action).

    Switched from saturating-max (`max(own, γ·best)`) on 2026-05-03
    after the formula was identified as making native-high cards lose
    chain-distance signal: `γ × 9 = 6.3 < 9` always meant downstream
    chain depth was invisible past the first high. Additive preserves
    chain influence at all ranks (CPM-like, leaf-favoring) which is
    the right kanban-pull semantic.

    `top_path` traces the argmax descendant chain — used by `-v`
    rendering as the WHY column. For a leaf with no descendants,
    `top_path` is `["self"]`.

    Cycles cannot occur in a deck that passes `goc validate`:
    `detect_advance_cycles` is a gating ERROR and `goc advance` refuses
    cycle-creating edges. The in-progress guard below
    (`if title in in_progress`) is therefore unreachable defensive code
    on any valid deck; it returns the re-entered node's bare rank purely
    to break the recursion. It does NOT compute an order-independent
    per-card-rank fallback — on a (validate-failing) cyclic deck the
    cycle members get values that depend on `cards`/`advances` list
    order — so it must not be relied on as one.
    The `isinstance(..., list)` guard before the descendant walk
    mirrors `find_half_edges` / `validate_card`: a hand-edited bare-string
    `advances` value is treated as an empty edge set, not iterated
    character-by-character (which would emit phantom dangling-edge
    warnings and reach the cycle branch via a chance self-match).
    Unknown advances targets are skipped for the priority math AND
    surfaced once per (card, target) pair as a stderr warning — silent
    skipping let edge rot degrade the value walk unnoticed. Run
    `goc validate` to get the authoritative report.
    """
    by_title = {t.title: t for t in cards}
    cache: dict[str, tuple[float, list[str]]] = {}

    def value_for(title: str, in_progress: set[str]) -> tuple[float, list[str]]:
        if title in cache:
            return cache[title]
        t = by_title.get(title)
        if t is None:
            return (0.0, [])
        own = CONTRIBUTION_RANK.get(t.contribution, 0.0)
        if title in in_progress:
            return (own, ["cycle"])
        in_progress.add(title)
        best = (0.0, [])
        advances = t.frontmatter.get("advances") or []
        if not isinstance(advances, list):
            advances = []
        for dest in advances:
            if dest not in by_title:
                key = (title, dest)
                if key not in _DANGLING_ADVANCES_WARNED:
                    _DANGLING_ADVANCES_WARNED.add(key)
                    print(
                        f"WARN dangling advances edge: {title} → {dest!r} "
                        f"(target card not found; priority math drops the edge). "
                        f"Run 'goc validate' for the authoritative report.",
                        file=sys.stderr,
                    )
                continue
            dest_card = by_title[dest]
            if not card_is_workable_for_scheduler(dest_card):
                # Scheduler axis is live-AND-workable only (AGENTS.md "deck
                # as scheduler vs record"): the prune mirrors every gate in
                # `card_is_ready` except the `status == "open"` clause
                # (`active` descendants stay workable for the scheduler).
                # A terminal descendant can no longer be unblocked; an
                # impeded descendant (active `waiting_on` overlay) cannot be
                # pulled for the duration of its wait; a `human_gate`-parked
                # descendant (decision/session) cannot be pulled until the
                # human lowers the gate. None of the three may amplify a live
                # card's priority — `card_is_ready` already hides them from
                # the queue, and the value walk follows. Both the
                # impediment and human-gate prunes are self-clearing: when
                # `waiting_until` elapses, `waiting_on` is cleared, or the
                # gate is lowered via `decide-card`, the descendant re-enters
                # the walk on the next recompute with no manual action.
                # Terminal edges live on the record axis, walked elsewhere.
                continue
            d_value, d_path = value_for(dest, in_progress)
            if d_value > best[0]:
                best = (d_value, [dest, *d_path])
        in_progress.discard(title)
        if best[0] > 0:
            result = (own + GAMMA * best[0], best[1])
        else:
            result = (own, ["self"])
        cache[title] = result
        return result

    for t in cards:
        value_for(t.title, set())
    return cache


def filter_cards(
    cards: list[Card],
    *,
    status: str | None,
    statuses: list[str] | None = None,
    stages: list[str] | None = None,
    contribution: str | None = None,
    human_gate: str | None = None,
    tags: list[str] | None = None,
    since: str | None = None,
    advances: str | None = None,
    advanced_by: str | None = None,
    worker: str | None = None,
    ready: bool = False,
    by_title: dict[str, Card] | None = None,
) -> list[Card]:
    out = list(cards)
    if statuses is not None:
        out = [t for t in out if t.status in statuses]
    elif status is not None and status != "all":
        out = [t for t in out if t.status == status]
    if stages:
        out = [t for t in out if (str(t.stage) if t.stage is not None else "null") in stages]
    if contribution:
        out = [t for t in out if t.contribution == contribution]
    if human_gate:
        out = [t for t in out if t.human_gate == human_gate]
    if tags:
        out = [t for t in out if all(tag in t.tags for tag in tags)]
    if since:
        out = [t for t in out if t.closed_at and str(t.closed_at) >= since]
    if advances:
        out = [
            t
            for t in out
            if isinstance(t.frontmatter.get("advances"), list)
            and advances in t.frontmatter["advances"]
        ]
    if advanced_by:
        out = [
            t
            for t in out
            if isinstance(t.frontmatter.get("advanced_by"), list)
            and advanced_by in t.frontmatter["advanced_by"]
        ]
    if worker:
        needle = worker.lower()
        out = [t for t in out if needle in _worker_who(t.frontmatter.get("worker")).lower()]
    if ready:
        lookup = by_title if by_title is not None else {t.title: t for t in cards}
        out = [t for t in out if card_is_ready(t, lookup)]
    return out


def parse_stage_filter(stage_flag: str | None) -> list[str] | None:
    if not stage_flag:
        return None
    valid = ", ".join(STAGE_ORDER)
    if "-" in stage_flag:
        a, b = stage_flag.split("-", 1)
        if a not in STAGE_ORDER or b not in STAGE_ORDER:
            print(f"goc: error: --stage: expected one of {valid}, or a range like alpha-stable", file=sys.stderr)
            sys.exit(2)
        ai, bi = STAGE_ORDER.index(a), STAGE_ORDER.index(b)
        return STAGE_ORDER[min(ai, bi) : max(ai, bi) + 1]
    if stage_flag not in STAGE_ORDER:
        print(f"goc: error: --stage: expected one of {valid}, or a range like alpha-stable", file=sys.stderr)
        sys.exit(2)
    return [stage_flag]


def parse_since_filter(value: str | None) -> str | None:
    if value is None:
        return None
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        print("goc: error: --since: expected YYYY-MM-DD", file=sys.stderr)
        sys.exit(2)
    try:
        date.fromisoformat(value)
    except ValueError:
        print("goc: error: --since: expected YYYY-MM-DD", file=sys.stderr)
        sys.exit(2)
    return value


_CLOSED_SINCE_WINDOW_RE = re.compile(r"^(\d+)([hdw])$")


def parse_closed_since(value: str | None, *, now: datetime | None = None) -> datetime | None:
    """Resolve --closed-since WINDOW to a UTC threshold datetime.

    Accepts `<N>h`, `<N>d`, `<N>w` relative windows, or an absolute
    `YYYY-MM-DD` ISO date (interpreted as midnight UTC). Returns the
    inclusive lower bound: cards whose `closed_at >= threshold` pass.
    """
    if value is None:
        return None
    base = now if now is not None else datetime.now(tz=timezone.utc)
    m = _CLOSED_SINCE_WINDOW_RE.match(value)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if n <= 0:
            print(
                "goc: error: --closed-since: window must be a positive integer "
                "(e.g. 24h, 7d, 2w)",
                file=sys.stderr,
            )
            sys.exit(2)
        hours = {"h": n, "d": n * 24, "w": n * 24 * 7}[unit]
        return base - timedelta(hours=hours)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        try:
            d = date.fromisoformat(value)
        except ValueError:
            print(
                "goc: error: --closed-since: expected <N>[h|d|w] or YYYY-MM-DD",
                file=sys.stderr,
            )
            sys.exit(2)
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    print(
        "goc: error: --closed-since: expected <N>[h|d|w] or YYYY-MM-DD",
        file=sys.stderr,
    )
    sys.exit(2)


def _closed_at_instant(value: object) -> datetime | None:
    """Parse a card's `closed_at` (date or datetime) into a UTC datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    s = str(value).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            d = date.fromisoformat(s[:10])
        except ValueError:
            return None
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def validate_tag_filters(tags: list[str]) -> list[str] | None:
    if not tags:
        return None
    schema = load_schema()
    unknown = [tag for tag in tags if tag not in schema.canonical_tags]
    if unknown:
        print(
            f"goc: error: --tag: unknown tag '{unknown[0]}' — {_UNKNOWN_TAG_REMEDY}",
            file=sys.stderr,
        )
        sys.exit(2)
    return list(tags)


def sort_default(
    cards: list[Card],
    values: dict[str, tuple[float, list[str]]] | None = None,
    by_title: dict[str, Card] | None = None,
) -> list[Card]:
    """Sort by GRPW-computed value, with ToC-style near-term-flow tiebreak.

    Key tuple: (-value, -live_direct_advances_count, age_days)
    - primary: highest computed value first (graph-amplified contribution)
    - tiebreak: more *live* direct downstream cards = unblock more flow now.
      Counts only `advances` targets the value walk would traverse — target
      exists in `by_title`, status not terminal, not impeded by an active
      `waiting_on` overlay, and not parked behind a non-`none` `human_gate`.
      A terminal, impeded, or gate-parked downstream unblocks zero flow now,
      so it contributes 0 — mirroring the prune `compute_values` applies in
      `value_for`. (Without this, a card whose downstream is fully un-pullable
      would out-rank an equal-value card that unblocks no less live flow,
      contradicting the tiebreak's own rationale.)
    - final: oldest-created first (kanban WIP-aging discipline)

    Both axes must see the FULL deck, not the filtered subset being sorted.
    `values` should be precomputed on the full deck so chains through
    filtered-out cards still amplify open cards; pass `by_title` (the full
    deck's title→Card lookup) for the same reason on the tiebreak axis — a
    downstream card the *display filter* hid (e.g. an `active` target while
    sorting the `open` column) is still live and still unblocks flow, so it
    must count. Only a genuinely dangling edge — target absent from the whole
    deck — counts 0, because `card_is_workable_for_scheduler` never sees it,
    matching the value walk's dangling-edge drop at engine.py:1739. When
    `by_title` is omitted it is built from `cards`, which is only correct
    when `cards` IS the full deck; callers that sort a subset must thread
    the full-deck lookup (every renderer already holds one as `full_by_title`).
    """
    if values is None:
        values = compute_values(cards)
    if by_title is None:
        by_title = {c.title: c for c in cards}

    def live_direct(t: Card) -> int:
        n = 0
        advances = t.frontmatter.get("advances") or []
        if not isinstance(advances, list):
            return 0
        for dest in advances:
            dc = by_title.get(dest)
            if dc is None:
                continue
            if not card_is_workable_for_scheduler(dc):
                continue
            n += 1
        return n

    def key(t: Card):
        v, _ = values.get(t.title, (0.0, []))
        return (-v, -live_direct(t), t.created)

    return sorted(cards, key=key)


# ────────────────────────────────────────────────────────────────────────────
# Rendering

COLOR = {
    "high": "\033[31m",  # red (contribution=high)
    "medium": "\033[33m",  # yellow
    "low": "\033[37m",  # white
    "open": "\033[36m",  # cyan
    "active": "\033[32m",  # green
    "blocked": "\033[35m",  # magenta
    "done": "\033[90m",  # grey
    "disproved": "\033[90m",
    "superseded": "\033[90m",
    "none": "\033[32m",
    "decision": "\033[33m",
    "session": "\033[31m",
    "reset": "\033[0m",
}


def _color_enabled(no_color: bool) -> bool:
    if no_color or os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _wrap(text: str, key: str, enabled: bool) -> str:
    if not enabled:
        return text
    code = COLOR.get(key)
    return f"{code}{text}{COLOR['reset']}" if code else text


def _format_value(v: float) -> str:
    return f"{v:.1f}"


def _format_why(path: list[str], by_title: dict[str, Card]) -> str:
    """Format the GRPW propagation trace: 'self' → '' (omit); chain → '→ A (high) → B (med)'."""
    if not path or path == ["self"]:
        return ""
    if path == ["cycle"]:
        return "(cycle)"
    suffix = ""
    if path[-1] == "self":
        path = path[:-1]
    elif path[-1] == "cycle":
        path = path[:-1]
        suffix = " (cycle)"
    if not path:
        return suffix.strip()
    parts = []
    for slug in path:
        c = by_title.get(slug)
        contrib = c.contribution if c else "?"
        parts.append(f"→ {slug} ({contrib})")
    return " ".join(parts) + suffix


def render_table(
    cards: list[Card],
    *,
    verbose: int,
    no_color: bool,
    values: dict[str, tuple[float, list[str]]] | None = None,
    by_title: dict[str, Card] | None = None,
) -> str:
    if not cards:
        return ""
    enabled = _color_enabled(no_color)
    if values is None:
        values = compute_values(cards)
    if by_title is None:
        by_title = {t.title: t for t in cards}
    if verbose >= 1:
        headers = ["TITLE", "STATUS", "STAGE", "CONTR.", "VALUE", "GATE", "CREATED", "TAGS", "DOD"]
    else:
        headers = ["TITLE", "STATUS", "CONTR.", "VALUE", "GATE", "TAGS", "DOD"]
    rows: list[tuple[str, ...]] = []
    for t in cards:
        tags = ",".join(str(x) for x in t.tags[:4])
        if len(t.tags) > 4:
            tags += "+"
        dod = "prose" if t.dod_freeform else f"{t.dod_done}/{t.dod_done + t.dod_open}"
        v_score, _ = values.get(t.title, (0.0, []))
        value_str = _format_value(v_score)
        if verbose >= 1:
            stage = str(t.stage) if t.stage is not None else "-"
            rows.append((t.title, t.status, stage, t.contribution, value_str, t.human_gate, t.created, tags, dod))
        else:
            rows.append((t.title, t.status, t.contribution, value_str, t.human_gate, tags, dod))
    widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(headers)]
    out_lines: list[str] = []
    out_lines.append("  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    out_lines.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for t, r in zip(cards, rows):
        if verbose >= 1:
            cells = [
                r[0].ljust(widths[0]),
                _wrap(r[1].ljust(widths[1]), t.status, enabled),
                r[2].ljust(widths[2]),
                _wrap(r[3].ljust(widths[3]), t.contribution, enabled),
                r[4].rjust(widths[4]),
                _wrap(r[5].ljust(widths[5]), t.human_gate, enabled),
                r[6].ljust(widths[6]),
                r[7].ljust(widths[7]),
                r[8].ljust(widths[8]),
            ]
        else:
            cells = [
                r[0].ljust(widths[0]),
                _wrap(r[1].ljust(widths[1]), t.status, enabled),
                _wrap(r[2].ljust(widths[2]), t.contribution, enabled),
                r[3].rjust(widths[3]),
                _wrap(r[4].ljust(widths[4]), t.human_gate, enabled),
                r[5].ljust(widths[5]),
                r[6].ljust(widths[6]),
            ]
        out_lines.append("  ".join(cells))
        if verbose >= 1:
            _, path = values.get(t.title, (0.0, []))
            why = _format_why(path, by_title)
            if why:
                out_lines.append(f"    why: {why}")
            if t.summary:
                out_lines.append(f"    summary: {t.summary}")
            # Liveness-gated dependency advisory (see `dependency_advisory`):
            # the "you may start" hint is meaningless on a terminal card, so
            # only live cards show it. The gate lives in the helper now.
            blockers, _ = dependency_advisory(t, by_title)
            if blockers:
                out_lines.append(f"    awaiting: {', '.join(blockers)} (you may start)")
            w = t.worker
            if w:
                who = w.get("who", "")
                where = w.get("where")
                worker_str = f"worker: {who}"
                if where:
                    worker_str += f" @ {where}"
                out_lines.append(f"    {worker_str}")
        if verbose >= 2:
            for field in LIST_REL_FIELDS:
                v = t.frontmatter.get(field) or []
                if v:
                    out_lines.append(f"    {field}: {list(v)}")
            dod = t.frontmatter.get("definition_of_done") or ""
            for line in dod.splitlines():
                out_lines.append(f"    {line.rstrip()}")
    return "\n".join(out_lines)


SLIM_JSON_KEYS = (
    "title",
    "status",
    "human_gate",
    "contribution",
    "value",
    "tags",
    "closed_at",
    "waiting_on",
    "waiting_until",
)


def render_json(
    cards: list[Card],
    values: dict[str, tuple[float, list[str]]] | None = None,
    by_title: dict[str, Card] | None = None,
    slim: bool = False,
) -> str:
    if values is None:
        values = compute_values(cards)
    if by_title is None:
        by_title = {t.title: t for t in cards}
    if slim:
        records = [
            {
                "title": t.title,
                "status": t.status,
                "human_gate": t.human_gate,
                "contribution": t.contribution,
                "value": values.get(t.title, (0.0, []))[0],
                "tags": t.tags,
                "closed_at": str(t.closed_at) if t.closed_at else None,
                "waiting_on": t.waiting_on,
                "waiting_until": t.waiting_until,
            }
            for t in cards
        ]
    else:
        records = [
            {
                "title": t.title,
                "summary": t.summary,
                "status": t.status,
                "stage": t.stage,
                "contribution": t.contribution,
                "value": values.get(t.title, (0.0, []))[0],
                "value_path": values.get(t.title, (0.0, []))[1],
                "human_gate": t.human_gate,
                "waiting_on": t.waiting_on,
                "waiting_until": t.waiting_until,
                "tags": t.tags,
                "created": t.created,
                "closed_at": str(t.closed_at) if t.closed_at else None,
                "advances": t.frontmatter.get("advances") or [],
                "advanced_by": t.frontmatter.get("advanced_by") or [],
                "supersedes": t.frontmatter.get("supersedes") or [],
                "superseded_by": t.frontmatter.get("superseded_by") or [],
                # Liveness-gated dependency advisory (see
                # `dependency_advisory`): the "you may start" hint is
                # meaningless on a terminal card. `ready` is already
                # status-gated by `card_is_ready` (open-only).
                "awaiting": advisory[0],
                "dependency_awaiting": advisory[1],
                "ready": card_is_ready(t, by_title),
                "worker": t.worker,
                "dod_open": t.dod_open,
                "dod_done": t.dod_done,
                "dod_freeform": t.dod_freeform,
            }
            for t in cards
            for advisory in (dependency_advisory(t, by_title),)
        ]
    return json.dumps(records, indent=2, default=str)


def _display_width(text: str) -> int:
    """Terminal column count: East-Asian Wide/Fullwidth glyphs (e.g. the
    `⏳` impediment marker) render across 2 columns though `len()` counts
    them as 1 codepoint."""
    return sum(
        2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text
    )


def _display_ljust(text: str, width: int) -> str:
    """Left-justify to a target display width (not codepoint count)."""
    pad = width - _display_width(text)
    return text + " " * pad if pad > 0 else text


def render_board(
    cards: list[Card],
    *,
    max_rows: int,
    no_color: bool,
    values: dict[str, tuple[float, list[str]]] | None = None,
    by_title: dict[str, Card] | None = None,
) -> str:
    if values is None:
        values = compute_values(cards)
    # Columns derive from the schema's status enum — the single source of
    # truth — not a hardcoded literal. This keeps the board in lockstep with
    # `status_values` (custom workflows, enum migrations) and never silently
    # drops a card whose status the renderer "forgot" to list.
    columns = list(load_schema().status_values)
    by_status: dict[str, list[Card]] = {c: [] for c in columns}
    if by_title is None:
        by_title = {t.title: t for t in cards}
    for t in cards:
        if t.status in by_status:
            by_status[t.status].append(t)
    hidden_by_status: dict[str, int] = {}
    for c in columns:
        sorted_col = sort_default(by_status[c], values=values, by_title=by_title)
        hidden_by_status[c] = max(0, len(sorted_col) - max_rows)
        by_status[c] = sorted_col[:max_rows]
    def card_cell(t: Card) -> str:
        c = t.contribution or ""
        marker = f" [{c[0] if c else '?'}]"
        live = t.status not in TERMINAL_STATUSES
        # Mark a card not-pullable on the board whenever any queue-hiding
        # axis fires. This mirrors `card_is_ready` /
        # `card_is_workable_for_scheduler`: a human_gate parks an open card
        # out of the pull queue just as hard as an impediment overlay, so it
        # must carry the same ⏳. `dependency_blocked` stays included as an
        # advisory "has an open prereq" hint (it does not hide the card from
        # the queue, but the board flags it). The `status == "open"` guard is
        # the board's own stricter slice — `dependency_advisory` gates out
        # terminal cards, the board additionally flags only open ones.
        not_ready = live and (
            t.human_gate != "none"
            or (t.status == "open" and dependency_advisory(t, by_title)[1])
            or waiting_impedes(t)
        )
        if not_ready:
            marker += " ⏳"
        who = _worker_who(t.frontmatter.get("worker"))
        if who:
            # Render the full worker identifier, not a fixed-width prefix.
            # Columns auto-size to their widest rendered cell (see
            # `col_widths` below), so a long `who` widens its column rather
            # than overflowing — the same contract the title already enjoys
            # (board-active-card-worker-label-not-truncated). A silent
            # `who[:8]` slice would mangle common values like `claude[bot]`
            # into `claude[b`, hiding coordination info the board exists to
            # surface.
            marker += f" @{who}"
        return f"{t.title}{marker}"

    rendered_by_status: dict[str, list[str]] = {
        c: [card_cell(t) for t in by_status[c]] for c in columns
    }
    # Surface the row cap rather than hiding it: every other capped list in
    # the tool (render_active_notice, the tag-sample renderer, the validate
    # report) advertises its overflow, so the board does too. The indicator
    # is appended before col_widths is computed below, so it participates in
    # width sizing and the grid stays aligned.
    for c in columns:
        if hidden_by_status[c] > 0:
            rendered_by_status[c].append(f"… +{hidden_by_status[c]} more")
    col_widths = [
        max(
            20,
            _display_width(c.upper()),
            max((_display_width(cell) for cell in rendered_by_status[c]), default=0),
        )
        for c in columns
    ]
    rows = max((len(rendered_by_status[c]) for c in columns), default=0)
    enabled = _color_enabled(no_color)
    out: list[str] = []
    header = " | ".join(
        _wrap(_display_ljust(c.upper(), col_widths[i]), c, enabled) for i, c in enumerate(columns)
    )
    out.append(header)
    out.append("-+-".join("-" * col_widths[i] for i in range(len(columns))))
    for i in range(rows):
        cells = []
        for col_index, c in enumerate(columns):
            if i < len(rendered_by_status[c]):
                cell = rendered_by_status[c][i]
            else:
                cell = ""
            cells.append(_display_ljust(cell, col_widths[col_index]))
        out.append(" | ".join(cells))
    return "\n".join(out)


def render_leverage_line(
    ready: list[Card],
    all_cards: list[Card],
    *,
    values: dict[str, tuple[float, list[str]]] | None = None,
) -> str:
    """One-line leverage comparison after a pull-card pick.

    Format: `Pulling <title> (value <N>). Highest gated card: <title>
    (value <M>, gate <kind>).` Returns the empty string when no open
    gated card exists outside the ready set (per the spec, the line is
    omitted when there's nothing to compare against) or when the ready
    set is itself empty (no pick to announce).
    """
    if not ready:
        return ""
    if values is None:
        values = compute_values(all_cards)
    open_gated = [
        t for t in all_cards
        if t.status == "open"
        and t.human_gate in ("decision", "session")
        and not waiting_impedes(t)
    ]
    if not open_gated:
        return ""
    gated_top = sort_default(
        open_gated, values=values, by_title={t.title: t for t in all_cards}
    )[0]
    pulled = ready[0]
    pulled_value = values.get(pulled.title, (0.0, []))[0]
    gated_value = values.get(gated_top.title, (0.0, []))[0]
    return (
        f"Pulling {pulled.title} (value {pulled_value:.1f}). "
        f"Highest gated card: {gated_top.title} "
        f"(value {gated_value:.1f}, gate {gated_top.human_gate})."
    )


def render_active_notice(
    cards: list[Card],
    *,
    values: dict[str, tuple[float, list[str]]] | None = None,
) -> str:
    """Warn open-queue readers about claimed cards outside the open filter."""

    if values is None:
        values = compute_values(cards)
    active = sort_default(
        [t for t in cards if t.status == "active"],
        values=values,
        by_title={t.title: t for t in cards},
    )
    if not active:
        return ""
    shown = ", ".join(t.title for t in active[:3])
    if len(active) > 3:
        shown += f", +{len(active) - 3} more"
    noun = "card" if len(active) == 1 else "cards"
    return (
        f"ACTIVE: {len(active)} claimed {noun} outside this open queue: {shown}. "
        "Check `goc --status active` or `goc --board` before claiming new work."
    )


# ────────────────────────────────────────────────────────────────────────────
# argparse app


def confirm(prompt: str, *, default: bool = False) -> bool:
    if sys.stdin.isatty():
        ans = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    else:
        try:
            ans = sys.stdin.readline().strip().lower()
        except (EOFError, OSError):
            return default
    if not ans:
        return default
    return ans.startswith("y")


def _non_negative_int(value: str) -> int:
    n = int(value)
    if n < 0:
        raise argparse.ArgumentTypeError(f"{value!r} is not a non-negative integer")
    return n


def _build_parser() -> argparse.ArgumentParser:
    schema = load_schema()
    parser = argparse.ArgumentParser(
        prog="goc",
        description="Game of Cards deck CLI",
    )

    # --version / -V: a first-class argparse action so it works at any
    # top-level position (e.g. `goc --no-color --version`) and is listed
    # in `goc --help`. argparse handles it during parse_args — before the
    # dual-tree/legacy-tree guards in cli() — printing and exiting 0.
    from goc import __version__
    parser.add_argument("--version", "-V", action="version",
                        version=f"goc, version {__version__}")

    # Global options (used when no subcommand is given)
    parser.add_argument("--tag", dest="tags", action="append", default=[], metavar="TAG",
                        help="Filter by tag (repeatable; AND).")
    parser.add_argument("--contribution", choices=schema.contribution_values,
                        help="Filter by contribution level.")
    parser.add_argument("--status", dest="status_flag", choices=list(STATUS_FILTER_VALUES), default=None,
                        help="One status, or 'all'. Default: open.")
    parser.add_argument("--stage", dest="stage_flag", default=None,
                        help="Stage filter; supports range like 'alpha-beta'.")
    parser.add_argument("--human-gate", choices=schema.human_gate_values,
                        help="Filter by human gate value.")
    parser.add_argument("--done", dest="done_flag", action="store_true",
                        help="Shortcut for --status done.")
    parser.add_argument("--since", default=None,
                        help="With --done: filter on closed_at >= YYYY-MM-DD.")
    parser.add_argument("--closed-since", dest="closed_since", default=None,
                        metavar="WINDOW",
                        help="Filter to cards whose closed_at falls within "
                        "WINDOW (e.g. 24h, 7d, 2w) or since YYYY-MM-DD. "
                        "Auto-extends --status to 'all' when set.")
    parser.add_argument("--waiting", action="store_true",
                        help="Filter to cards carrying a waiting_on overlay.")
    parser.add_argument("--slim", action="store_true",
                        help=f"With --json: emit only {', '.join(SLIM_JSON_KEYS)}.")
    parser.add_argument("--advances", default=None,
                        help="Filter to cards that advance this title.")
    parser.add_argument("--advanced-by", dest="advanced_by", default=None,
                        help="Filter to cards advanced by this title.")
    parser.add_argument("--worker", default=os.environ.get("GOC_WORKER"),
                        help="Filter by worker.who (substring match). Also read from GOC_WORKER env var.")
    parser.add_argument("--ready", action="store_true",
                        help="Filter to ready-to-pull cards (status open, human_gate none, "
                        "no active waiting_on impediment). Defaults --status to open.")
    parser.add_argument("-v", dest="verbose", action="count", default=0,
                        help="-v adds STAGE/CREATED columns + summary line; -vv inlines DoD checklist + cross-refs.")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="Machine-readable JSON.")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--board", action="store_true",
                        help="ASCII multi-column kanban board.")
    parser.add_argument("--max-rows", type=_non_negative_int, default=20,
                        help="Cap rows per column in --board.")

    subparsers = parser.add_subparsers(dest="command")

    # validate
    p_validate = subparsers.add_parser("validate", help="Walk all cards and check schema conformance.")
    p_validate.add_argument("--quiet", action="store_true",
                            help="Only print errors; suppress per-todo OK lines.")

    # quality-pass
    p_qp = subparsers.add_parser("quality-pass", help="Surface engineer-jargon titles + missing summaries.")
    p_qp.add_argument("--status", dest="status_flag", choices=list(STATUS_FILTER_VALUES),
                      default=argparse.SUPPRESS,
                      help="Filter by status (overrides global --status; default: open).")
    p_qp.add_argument("--llm", action="store_true", default=False,
                      help="Also run a Sonnet-batched summary+DoD audit.")
    p_qp.add_argument("--no-llm", dest="llm", action="store_false",
                      help="Disable LLM audit.")
    p_qp.add_argument("--limit", type=_non_negative_int, default=None,
                      help="With --llm: cap card count (testing/sampling).")
    p_qp.add_argument("--dry-run", action="store_true",
                      help="With --llm: print verdicts; skip the interactive accept/reject walk.")
    p_qp.add_argument("--yes", dest="auto_yes", action="store_true",
                      help="With --llm: auto-accept every proposed rewrite (use with care).")

    # done
    p_done = subparsers.add_parser("done", help="Flip status → done; set closed_at; enforce DoD-checkbox rule.")
    p_done.add_argument("titles", nargs="+",
                        help="One card title, or multiple titles with --bundle.")
    p_done.add_argument("--bundle", action="store_true",
                        help="Close multiple cards in one invocation: shared attestation "
                        "block + per-card Bundled-with cross-references. Preserves the "
                        "per-card unchecked-DoD refusal.")
    p_done.add_argument("--force", action="store_true",
                        help="Bypass DoD enforcement (free-form prose DoDs).")

    # attest
    p_attest = subparsers.add_parser("attest", help="Run layer-2 + layer-3 closure checks.")
    p_attest.add_argument("title")
    p_attest.add_argument("--skip", dest="skips", action="append", default=[],
                          help="Skip a check by name; recorded as SKIPPED in log.")
    p_attest.add_argument("--non-interactive", action="store_true",
                          help="Fail manual/agent checks instead of prompting.")

    # status
    p_status = subparsers.add_parser("status", help="Mutate any status except `done`.")
    p_status.add_argument("title")
    p_status.add_argument("new_status", choices=list(MUTABLE_STATUS_VALUES))
    p_status.add_argument("--by", dest="superseded_by", default=None,
                          help="Successor card title; only valid with new_status=superseded. "
                          "Sets bidirectional supersedes/superseded_by typed link.")
    p_status.add_argument("--commit", action="store_true",
                          help="Force auto-commit for this status flip.")
    p_status.add_argument("--no-commit", action="store_true",
                          help="Skip auto-commit for this status flip.")
    p_status.add_argument("--worker-who", default=None,
                          help="Override worker.who identity.")
    p_status.add_argument("--worker-where", default=None,
                          help="Override worker.where branch or path for this claim.")

    # new
    p_new = subparsers.add_parser(
        "new",
        help="Scaffold a new card dir with valid frontmatter and empty log.md.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  goc new child-card --advances parent-card
  goc new child-card --advanced-by parent-card
  goc new child-card --advances parent-card --commit""",
    )
    p_new.add_argument("title")
    p_new.add_argument("--contribution", choices=schema.contribution_values,
                       default=argparse.SUPPRESS,
                       help="Contribution level (overrides global --contribution; default: medium).")
    p_new.add_argument("--gate", choices=schema.human_gate_values, default=schema.human_gate_default)
    # --tag, --worker share `dest` with global filters; SUPPRESS lets the
    # parent value flow through when the subparser flag isn't passed.
    p_new.add_argument("--tag", dest="tags", action="append", default=argparse.SUPPRESS,
                       help="Card tag (repeatable; overrides global --tag).")
    # --advances and --advanced-by collide with global *filters* of the
    # same name but with incompatible types (global = single-value
    # filter; new = list of titles to wire). Use distinct dests so the
    # parent string can't silently coerce into the wiring list.
    p_new.add_argument("--advances", dest="advances_wire", action="append", default=[], metavar="TITLE",
                       help="Wire the new card as advancing TITLE (repeatable).")
    p_new.add_argument("--advanced-by", dest="advanced_by_wire", action="append", default=[], metavar="TITLE",
                       help="Wire TITLE as advancing the new card (repeatable).")
    p_new.add_argument("--worker", default=argparse.SUPPRESS,
                       help="Worker designation (overrides global --worker / $GOC_WORKER; "
                            "person, machine, or capability tag).")
    p_new.add_argument("--allow-jargon", action="store_true",
                       help="Bypass the title-antipattern check (rare; used by migration tools).")
    p_new.add_argument("--commit", action="store_true",
                       help="Commit the new card and any --advances/--advanced-by endpoints atomically "
                            "(recommended for wired filings; default is no-commit so the "
                            "scaffold-then-fill-in workflow is unchanged).")
    p_new.add_argument("--no-commit", action="store_true",
                       help="Skip auto-commit (the default for goc new).")

    # wait
    p_wait = subparsers.add_parser(
        "wait",
        help="Set or clear the impediment overlay (waiting_on + waiting_until).",
    )
    p_wait.add_argument("title")
    p_wait.add_argument("--reason", choices=schema.waiting_on_values, default=None,
                        help="Exogenous wait reason. Composes with --until.")
    p_wait.add_argument("--until", default=None,
                        help="ISO date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ) the wait is expected to clear. "
                        "Future date hides the card from next-card/pull-card; elapsed date is surfaced "
                        "as an SLE escalation by goc validate.")
    p_wait.add_argument("--clear", action="store_true",
                        help="Drop both waiting_on and waiting_until.")
    p_wait.add_argument("--commit", action="store_true",
                        help="Force auto-commit for this overlay change.")
    p_wait.add_argument("--no-commit", action="store_true",
                        help="Skip auto-commit for this overlay change.")

    # advance
    p_advance = subparsers.add_parser("advance", help="Add bidirectional value-flow edge.")
    p_advance.add_argument("title")
    p_advance.add_argument("--by", dest="advancer", required=True,
                           help="Slug of the card that advances <title>.")
    p_advance.add_argument("--commit", action="store_true",
                           help="Force auto-commit for this edge mutation.")
    p_advance.add_argument("--no-commit", action="store_true",
                           help="Skip auto-commit for this edge mutation.")

    # unadvance
    p_unadvance = subparsers.add_parser("unadvance", help="Remove bidirectional value-flow edge.")
    p_unadvance.add_argument("title")
    p_unadvance.add_argument("--by", dest="advancer", required=True)
    p_unadvance.add_argument("--commit", action="store_true",
                             help="Force auto-commit for this edge mutation.")
    p_unadvance.add_argument("--no-commit", action="store_true",
                             help="Skip auto-commit for this edge mutation.")

    # repair-edges
    p_repair_edges = subparsers.add_parser(
        "repair-edges",
        help="Preview or repair asymmetric advances/advanced_by and supersedes/superseded_by edges.",
    )
    p_repair_edges.add_argument(
        "--apply",
        action="store_true",
        help="Write missing reverse edges. Default is preview-only.",
    )

    # move
    p_move = subparsers.add_parser("move", help="Rename a title and rewrite known cross-references.")
    p_move.add_argument("old_title")
    p_move.add_argument("new_title")
    p_move.add_argument("--allow-jargon", action="store_true",
                        help="Bypass the title-antipattern check (rare; used by migration tools).")
    p_move.add_argument("--dry-run", action="store_true",
                        help="Print sites that would be rewritten without making changes.")

    # decide
    p_decide = subparsers.add_parser("decide", help="Record a decision in the body + log; lower the human gate to `none`.")
    p_decide.add_argument("title")
    p_decide.add_argument("--decision", required=True,
                          help="One-line decision (the WHAT).")
    p_decide.add_argument("--because", dest="reasoning", required=True,
                          help="One-line reasoning (the WHY).")
    p_decide.add_argument("--commit", action="store_true",
                          help="Force auto-commit for this decision record.")
    p_decide.add_argument("--no-commit", action="store_true",
                          help="Skip auto-commit for this decision record.")

    # triage
    p_triage = subparsers.add_parser("triage", help="List parked cards (gate ≠ none), grouped by gate, oldest-first.")
    p_triage.add_argument("--json", dest="as_json", action="store_true", default=argparse.SUPPRESS,
                          help="Emit JSON for Q&A consumers (overrides global --json).")
    p_triage.add_argument("--worker", default=argparse.SUPPRESS,
                          help="Filter parked cards by worker.who (substring match; "
                               "overrides global --worker / $GOC_WORKER).")

    # show
    p_show = subparsers.add_parser("show", help="Print full README.md to stdout.")
    p_show.add_argument("title")

    # migrate
    p_migrate = subparsers.add_parser("migrate", help="Merge legacy deck/ into .game-of-cards/deck/.")
    p_migrate.add_argument("--dry-run", action="store_true",
                           help="Show what would happen without making changes.")
    p_migrate.add_argument("--yes", dest="auto_yes", action="store_true",
                           help="Skip confirmation prompt.")

    # migrate-list-style
    p_mls = subparsers.add_parser("migrate-list-style",
                                  help="Re-emit every card to convert relation-edge lists (advances/advanced_by/supersedes/superseded_by) to block-style.")
    p_mls.add_argument("--dry-run", action="store_true",
                       help="Show which cards would change without writing files.")

    return parser


def cli(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    if _DUAL_TREE_CONFLICT and args.command != "migrate":
        _canonical = DECK_ROOT / ".game-of-cards" / "deck"
        _legacy = DECK_ROOT / "deck"
        print(
            f"ERROR: two deck trees found — cannot operate safely:\n"
            f"  canonical: {_canonical}\n"
            f"  legacy:    {_legacy}\n"
            f"\nRun `goc migrate` to merge legacy → canonical and remove the stale tree.",
            file=sys.stderr,
        )
        sys.exit(1)
    if _LEGACY_ONLY and args.command not in ("migrate", "install", "upgrade", None):
        print(
            "WARNING: using legacy deck/ location. Run `goc upgrade` to migrate to .game-of-cards/deck/.",
            file=sys.stderr,
        )

    if args.command is None:
        _cmd_default(args)
    elif args.command == "validate":
        _cmd_validate(args)
    elif args.command == "quality-pass":
        _cmd_quality_pass(args)
    elif args.command == "done":
        _cmd_done(args)
    elif args.command == "attest":
        _cmd_attest(args)
    elif args.command == "status":
        _cmd_status(args)
    elif args.command == "new":
        _cmd_new(args)
    elif args.command == "wait":
        _cmd_wait(args)
    elif args.command == "advance":
        _cmd_advance(args)
    elif args.command == "unadvance":
        _cmd_unadvance(args)
    elif args.command == "repair-edges":
        _cmd_repair_edges(args)
    elif args.command == "move":
        _cmd_move(args)
    elif args.command == "decide":
        _cmd_decide(args)
    elif args.command == "triage":
        _cmd_triage(args)
    elif args.command == "show":
        _cmd_show(args)
    elif args.command == "migrate":
        _cmd_migrate(args)
    elif args.command == "migrate-list-style":
        _cmd_migrate_list_style(args)
    else:
        parser.print_help()
        sys.exit(1)


def _cmd_default(args):
    cards = load_all_cards()
    if args.done_flag and args.status_flag is not None:
        print("goc: error: pass only one of --done / --status", file=sys.stderr)
        sys.exit(2)
    closed_since_threshold = parse_closed_since(getattr(args, "closed_since", None))
    if args.done_flag:
        status = "done"
    elif args.status_flag is None:
        # --waiting and --closed-since both surface cards beyond the open
        # queue (active-impeded cards, closed cards): auto-extend the default
        # status to "all" so the subsequent filter has something to narrow.
        status = (
            "all"
            if (closed_since_threshold is not None or getattr(args, "waiting", False))
            else "open"
        )
    else:
        status = args.status_flag
    status_filter_explicit = bool(args.done_flag or args.status_flag is not None)
    since = parse_since_filter(args.since)
    if since and status != "done":
        print("goc: error: --since requires --done (or --status done)", file=sys.stderr)
        sys.exit(2)
    stages = parse_stage_filter(args.stage_flag)
    tag_filters = validate_tag_filters(args.tags)
    full_by_title = {t.title: t for t in cards}
    filtered = filter_cards(
        cards,
        status=status,
        stages=stages,
        contribution=args.contribution,
        human_gate=args.human_gate,
        tags=tag_filters,
        since=since,
        advances=args.advances,
        advanced_by=args.advanced_by,
        worker=args.worker,
        ready=args.ready,
        by_title=full_by_title,
    )
    if closed_since_threshold is not None:
        filtered = [
            t for t in filtered
            if (dt := _closed_at_instant(t.closed_at)) is not None
            and dt >= closed_since_threshold
        ]
    if getattr(args, "waiting", False):
        filtered = [t for t in filtered if t.waiting_on is not None]
    full_values = compute_values(cards)
    filtered = sort_default(filtered, values=full_values, by_title=full_by_title)
    if args.board:
        board_cards = filtered if (status_filter_explicit or args.worker) else cards
        print(
            render_board(
                board_cards, max_rows=args.max_rows, no_color=args.no_color,
                values=full_values, by_title=full_by_title,
            )
        )
    elif args.as_json:
        print(render_json(
            filtered, values=full_values, by_title=full_by_title,
            slim=getattr(args, "slim", False),
        ))
    else:
        out = render_table(filtered, verbose=args.verbose, no_color=args.no_color, values=full_values, by_title=full_by_title)
        active_notice = render_active_notice(cards, values=full_values) if status == "open" else ""
        leverage = (
            render_leverage_line(filtered, cards, values=full_values)
            if args.ready else ""
        )
        lines = [part for part in (active_notice, out, leverage) if part]
        if lines:
            print("\n".join(lines))


def _cmd_validate(args):
    """Walk all cards, parse YAML, check schema conformance. Exit 1 on violations."""
    schema = load_schema()
    cards = load_all_cards()
    all_titles = {t.title for t in cards}
    errors: list[str] = []
    for e in validate_deck_directories():
        print(f"ERROR: {e}", file=sys.stderr)
        errors.append(e)
    for e in validate_skill_dir_parity():
        print(f"ERROR: {e}", file=sys.stderr)
        errors.append(e)
    for e in validate_plugin_mirror_parity():
        print(f"ERROR: {e}", file=sys.stderr)
        errors.append(e)
    for e in validate_hook_registration():
        print(f"ERROR: {e}", file=sys.stderr)
        errors.append(e)
    for t in cards:
        per = validate_card(t, schema, all_titles)
        errors.extend(per)
        if not per and not args.quiet:
            print(f"OK  {t.title}")
        else:
            for e in per:
                print(f"ERROR: {e}", file=sys.stderr)
    # Advisory warnings print first; the exit-gating errors and their
    # remediation hints come last so they stay the most prominent output.
    for w in validate_blocker_coherence(cards):
        print(w.message, file=sys.stderr)
    for w in validate_epic_edge_direction(cards):
        print(w.message, file=sys.stderr)
    for w in validate_waiting_overlay(cards):
        print(w.message, file=sys.stderr)
    for w in validate_dod_method_tags(cards):
        print(w.message, file=sys.stderr)
    for w in validate_decision_verdict_coherence(cards):
        print(w.message, file=sys.stderr)
    for e in detect_advance_cycles(cards):
        print(f"ERROR: {e}", file=sys.stderr)
        errors.append(e)
    for e in detect_supersedes_cycles(cards):
        print(f"ERROR: {e}", file=sys.stderr)
        errors.append(e)
    half_edge_errors = validate_bidirectional_edges(cards)
    for e in half_edge_errors:
        print(f"ERROR: {e}", file=sys.stderr)
        errors.append(e)
    if half_edge_errors:
        print("Run 'goc repair-edges --apply' to fix.", file=sys.stderr)
    for e in validate_supersedes_targets(cards):
        print(f"ERROR: {e}", file=sys.stderr)
        errors.append(e)
    for e in validate_superseded_by_targets(cards):
        print(f"ERROR: {e}", file=sys.stderr)
        errors.append(e)
    if errors:
        sys.exit(1)


_QUALITY_PROMPT_TEMPLATE = """You are auditing card metadata quality on a project's GoC kanban deck.
Each card has a TITLE, a SUMMARY, and a DEFINITION_OF_DONE checklist.
Evaluate three dimensions per card:

1. TITLE — Is it PO-readable? A non-engineer reading the kanban should
   understand what the card is about WITHOUT opening the body.
   - Bad: "pong-late-hr-stuck-below-50-after-bug-140-path-2"
     (engineer's-jargon: rN refs, path-N, bug-N, math symbols, _md_/_py_,
     camelCase tokens — same antipattern set as deck.py `new` rejects)
   - Good: "pong-cannot-recover-prior-task-performance"
   Verdict {{ok: true}} if PO-readable; {{ok: false, rewrite: "...", reason: "..."}} otherwise.

2. SUMMARY — Is it self-contained? Could a cold reader (human or AI agent
   walking into the project tomorrow) understand WHAT the card is and WHY
   it matters from the summary alone, without opening the body?
   - Bad: "Pong's late hit rate is too low" (just restates the title)
   - Good: "Pong's late hit rate ceilings at ~0.35 across every knob
     combination tried on R89 framework HEAD; R88 N=20 confirmed the
     original 10-seed measurement was a positive variance peak..."
   Verdict {{ok: true}} if self-contained; {{ok: false, rewrite: "...", reason: "..."}} otherwise.
   If summary is empty/missing entirely, output {{ok: false, rewrite: "<draft from title>", reason: "missing summary"}}.

3. DOD — Is each item verifiable (binary done/not-done) and concrete?
   - Bad: "- [ ] improve performance" (no metric)
   - Bad: "- [ ] investigate whether X" (hypothesis, not deliverable)
   - Good: "- [ ] reproduce R90's late_HR ≥ 0.50 mean with σ ≤ 0.20
     across 10 seeds × 1500s on current code path"
   For each item that's NOT verifiable, return {{idx: N (0-based), issue: "...", fix: "rewrite..."}}.
   Items that are fine are NOT listed.

Output a JSON ARRAY (one record per card, same order as input). Each record:
{{
  "title": "<card-title>",
  "title_verdict": {{"ok": true}}  OR  {{"ok": false, "rewrite": "...", "reason": "..."}},
  "summary_verdict": {{"ok": true}} OR {{"ok": false, "rewrite": "...", "reason": "..."}},
  "dod_issues": [{{"idx": N, "issue": "...", "fix": "..."}}, ...]   (empty array if all items fine)
}}

CRITICAL: respond with valid JSON ONLY. No prose before/after. No markdown fences.
You may wrap in ```json ... ``` if your tool requires fences; the parser strips them.

CARDS:

{cards_json}
"""


_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)


def _build_quality_prompt(cards: list[Card]) -> str:
    """Slim cards JSON dump (title, summary, definition_of_done) for the LLM."""
    slim = [
        {
            "title": c.title,
            "summary": c.summary,
            "definition_of_done": c.frontmatter.get("definition_of_done") or "",
        }
        for c in cards
    ]
    return _QUALITY_PROMPT_TEMPLATE.format(cards_json=json.dumps(slim, indent=2))


def _extract_json_payload(raw: str) -> str:
    """Strip optional ```json ... ``` fences; return the inner JSON text."""
    raw = raw.strip()
    m = _FENCED_JSON_RE.search(raw)
    return m.group(1).strip() if m else raw


def _run_sonnet_quality_pass(prompt: str) -> list[dict]:
    """Subprocess call to `claude --model sonnet -p ... --output-format json`.

    Returns the parsed list-of-verdicts. Raises subprocess.CalledProcessError on
    CLI failure; ValueError if the response cannot be parsed as JSON or if the
    `claude` CLI is unauthenticated (returns is_error with a /login message).
    """
    if shutil.which("claude") is None:
        raise RuntimeError("`claude` CLI not on PATH; cannot run --llm pass.")
    cmd = ["claude", "--model", "sonnet", "-p", prompt, "--output-format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    envelope = json.loads(result.stdout)
    if isinstance(envelope, dict) and envelope.get("is_error"):
        raise RuntimeError(f"claude CLI reported error: {envelope.get('result', '')!r}")
    inner_text = envelope.get("result", "") if isinstance(envelope, dict) else str(envelope)
    payload = _extract_json_payload(inner_text)
    verdicts = json.loads(payload)
    if not isinstance(verdicts, list):
        raise ValueError(f"expected JSON array, got {type(verdicts).__name__}")
    return verdicts


def _render_verdict(verdict: dict) -> bool:
    """Print one verdict block to terminal. Returns True if any rewrite proposed."""
    has_rewrite = False
    title = verdict.get("title", "<unknown>")
    print(f"\n=== {title} ===")
    tv = verdict.get("title_verdict") or {}
    if tv.get("ok"):
        print("title:   OK")
    elif tv.get("rewrite"):
        # Mirror _apply_verdict_interactive's guard: only a verdict carrying a
        # rewrite string is an applicable rewrite, so only it counts.
        has_rewrite = True
        print(f"title:   REWRITE — {tv.get('reason', '?')}")
        print(f"  proposed: {tv['rewrite']}")
    else:
        print(f"title:   flagged, no rewrite offered — {tv.get('reason', '?')}")
    sv = verdict.get("summary_verdict") or {}
    if sv.get("ok"):
        print("summary: OK")
    elif sv.get("rewrite"):
        has_rewrite = True
        print(f"summary: REWRITE — {sv.get('reason', '?')}")
        print(f"  proposed: {sv['rewrite']}")
    else:
        print(f"summary: flagged, no rewrite offered — {sv.get('reason', '?')}")
    dod_issues = verdict.get("dod_issues") or []
    # Mirror _apply_dod_rewrite's guard: only an issue carrying both `idx` and
    # `fix` is an applicable rewrite, so only those count. A flagged-but-fixless
    # issue prints for visibility but does NOT count toward has_rewrite.
    fixable = [issue for issue in dod_issues if "idx" in issue and "fix" in issue]
    fixless = [issue for issue in dod_issues if not ("idx" in issue and "fix" in issue)]
    if fixable:
        has_rewrite = True
        print(f"dod:     {len(fixable)} issue(s)")
        for issue in fixable:
            print(f"  [{issue['idx']}] {issue.get('issue', '?')}")
            print(f"      fix: {issue['fix']}")
    if fixless:
        print(f"dod:     {len(fixless)} flagged, no rewrite offered")
        for issue in fixless:
            print(f"  [{issue.get('idx', '?')}] {issue.get('issue', '?')}")
    if not dod_issues:
        print("dod:     OK")
    return has_rewrite


def _apply_summary_rewrite(card: Card, new_summary: str) -> None:
    """In-place YAML-safe rewrite of the `summary:` field on this card's README.md.

    Routes through `emit_frontmatter` (same pattern as `_apply_dod_rewrite`) so
    a multi-line LLM-authored summary emits as a `|-` block scalar instead of
    a bare unquoted value that would destroy every frontmatter field below it.
    """
    readme = card.path / "README.md"
    text = readme.read_text()
    fm, body = parse_frontmatter(text)
    fm["summary"] = new_summary
    readme.write_text(emit_frontmatter(fm, body=body))


def _apply_dod_rewrite(card: Card, issues: list[dict]) -> None:
    """Replace specific DoD items by 0-based index. Other items preserved verbatim."""
    readme = card.path / "README.md"
    text = readme.read_text()
    fm, body = parse_frontmatter(text)
    dod_text = fm.get("definition_of_done") or ""
    lines = dod_text.splitlines()
    box_indices = _dod_box_indices(lines)
    fix_by_idx = {issue["idx"]: issue["fix"] for issue in issues if "idx" in issue and "fix" in issue}
    for box_idx, line_idx in enumerate(box_indices):
        if box_idx in fix_by_idx:
            indent = re.match(r"[ \t]*", lines[line_idx]).group(0)
            new_text = fix_by_idx[box_idx]
            new_text = new_text.lstrip()
            if not new_text.startswith("- ["):
                new_text = f"- [ ] {new_text}"
            lines[line_idx] = indent + new_text
    fm["definition_of_done"] = "\n".join(lines) + ("\n" if not dod_text.endswith("\n") else "")
    readme.write_text(emit_frontmatter(fm, body=body))


def _apply_verdict_interactive(card: Card, verdict: dict, *, auto_yes: bool = False) -> dict:
    """Walk a verdict, prompting accept/reject per dimension. Returns counts of applied edits."""
    applied = {"title": False, "summary": False, "dod": 0}

    def ask(prompt: str) -> bool:
        if auto_yes:
            return True
        return confirm(prompt, default=False)

    tv = verdict.get("title_verdict") or {}
    if not tv.get("ok") and tv.get("rewrite"):
        if ask(f"  apply title rewrite → {tv['rewrite']!r}?"):
            move_cmd = [
                sys.executable,
                "-m",
                "goc.cli",
                "move",
                card.title,
                tv["rewrite"],
            ]
            r = subprocess.run(move_cmd, capture_output=True, text=True, check=False)
            if r.returncode == 0:
                applied["title"] = True
                print(f"    moved → {tv['rewrite']}")
            else:
                print(f"    move failed: {r.stderr.strip()}", file=sys.stderr)

    sv = verdict.get("summary_verdict") or {}
    if not sv.get("ok") and sv.get("rewrite"):
        if ask("  apply summary rewrite?"):
            target_card = card
            if applied["title"]:
                target_card = load_card(DECK_DIR / tv["rewrite"]) or card
            _apply_summary_rewrite(target_card, sv["rewrite"])
            applied["summary"] = True
            print("    summary rewritten")

    dod_issues = verdict.get("dod_issues") or []
    accepted_issues: list[dict] = []
    for issue in dod_issues:
        if ask(f"  apply DoD fix [{issue.get('idx')}] ({issue.get('issue', '?')})?"):
            accepted_issues.append(issue)
    if accepted_issues:
        target_card = card
        if applied["title"]:
            target_card = load_card(DECK_DIR / tv["rewrite"]) or card
        _apply_dod_rewrite(target_card, accepted_issues)
        applied["dod"] = len(accepted_issues)
        print(f"    DoD: {len(accepted_issues)} item(s) rewritten")

    return applied


def _cmd_quality_pass(args):
    """Surface engineer-jargon titles + missing summaries across the existing deck."""
    status_flag = getattr(args, "status_flag", None)
    if getattr(args, "done_flag", False) and status_flag is None:
        status_flag = "done"
    if status_flag is None:
        status_flag = "open"
    llm = args.llm
    limit = args.limit
    dry_run = args.dry_run
    auto_yes = args.auto_yes

    cards = load_all_cards()
    if status_flag != "all":
        cards = [c for c in cards if c.status == status_flag]

    title_hits: list[tuple[str, list[str]]] = []
    missing_summary: list[str] = []
    for c in cards:
        antis = _check_title_antipatterns(c.title)
        if antis:
            title_hits.append((c.title, antis))
        summary = (c.summary or "").strip() if hasattr(c, "summary") else ""
        if not summary:
            missing_summary.append(c.title)

    print(f"\nQuality pass over {len(cards)} cards (status={status_flag}):\n")

    if title_hits:
        print(f"Title antipatterns ({len(title_hits)} cards):")
        for title, reasons in title_hits:
            print(f"  - {title}")
            for r in reasons:
                print(f"      → {r}")
        print("")
    else:
        print("Title antipatterns: clean.\n")

    if missing_summary:
        print(f"Missing summary ({len(missing_summary)} cards):")
        for title in missing_summary[:20]:
            print(f"  - {title}")
        if len(missing_summary) > 20:
            print(f"  ... and {len(missing_summary) - 20} more")
        print("")
    else:
        print("Missing summary: clean.\n")

    if not llm:
        return

    sample = cards if limit is None else cards[:limit]
    print(f"Layer-2 (Sonnet pass): auditing {len(sample)} cards via `claude --model sonnet -p`…")
    prompt = _build_quality_prompt(sample)
    try:
        verdicts = _run_sonnet_quality_pass(prompt)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: claude CLI failed (exit {e.returncode}): {e.stderr[:500] or e.stdout[:500]}", file=sys.stderr)
        sys.exit(1)
    except (ValueError, json.JSONDecodeError, RuntimeError) as e:
        print(f"ERROR: could not parse Sonnet response: {e}", file=sys.stderr)
        sys.exit(1)

    by_title = {c.title: c for c in sample}
    rewrite_count = 0
    applied_count = {"title": 0, "summary": 0, "dod": 0}
    for verdict in verdicts:
        if _render_verdict(verdict):
            rewrite_count += 1
            if not dry_run:
                card = by_title.get(verdict.get("title", ""))
                if card is None:
                    print("    (card not found in sample; skipping apply)", file=sys.stderr)
                    continue
                applied = _apply_verdict_interactive(card, verdict, auto_yes=auto_yes)
                applied_count["title"] += int(applied["title"])
                applied_count["summary"] += int(applied["summary"])
                applied_count["dod"] += applied["dod"]

    print(f"\nSonnet pass: {len(verdicts)} cards audited, {rewrite_count} with proposed rewrites.")
    if not dry_run:
        print(
            f"Applied: {applied_count['title']} titles, {applied_count['summary']} summaries, {applied_count['dod']} DoD items."
        )


def _cmd_done(args):
    """Flip status → done; set closed_at; enforce DoD-checkbox rule."""
    titles = args.titles
    force = args.force
    if args.bundle:
        if len(titles) < 2:
            print("goc: error: --bundle requires at least 2 titles", file=sys.stderr)
            sys.exit(2)
        _cmd_done_bundle(titles, force)
        return
    if len(titles) != 1:
        print(
            "goc: error: pass one title (or use --bundle with multiple titles)",
            file=sys.stderr,
        )
        sys.exit(2)
    title = titles[0]
    card_dir = DECK_DIR / title
    t = load_card_or_exit(card_dir, title)
    prior = t.status
    if prior == "done":
        print(f"{title}: already done; closed_at unchanged")
        return
    if prior in TERMINAL_STATUSES:
        print(
            f"ERROR: {title}: status is {prior!r} (terminal); "
            f"use the supersede/disprove workflow — 'done' cannot overwrite terminal states",
            file=sys.stderr,
        )
        sys.exit(2)
    if t.dod_freeform and not force:
        print(f"ERROR: {title}: free-form DoD; use --force to bypass enforcement", file=sys.stderr)
        sys.exit(2)
    if t.dod_open > 0:
        print(f"ERROR: {title}: {t.dod_open} unchecked DoD boxes; will not mark done", file=sys.stderr)
        sys.exit(2)
    if t.human_gate != "none":
        print(
            f"ERROR: {title}: human_gate is {t.human_gate!r}; "
            f"run `goc decide {title} --decision <choice> --because <reason>` "
            f"to lower the gate before closing.",
            file=sys.stderr,
        )
        sys.exit(2)
    _enforce_closure_on_integration_or_exit(title)
    now = _utc_now_iso()
    text = (card_dir / "README.md").read_text()
    text = mutate_frontmatter_field(text, "status", "done")
    text = mutate_frontmatter_field(text, "closed_at", _yaml_inline(now))
    (card_dir / "README.md").write_text(text)
    print(f"{title}: {prior} → done")
    print("Next: goc to see what's open, or ask your agent to \"drain the queue\" (pull-card).")


def _format_bundle_attestation_block(timestamp: str, titles: list[str]) -> str:
    members = "\n".join(f"  - {t}" for t in titles)
    return (
        f"## Closure verification ({timestamp}) — bundled\n"
        f"\n"
        f"- Bundle members:\n{members}\n"
        f"- DoD enforcement: PASS — per-card unchecked-box count was 0 for every member.\n"
        f"- Closed via: `goc done --bundle`\n"
    )


def _format_bundle_closure_entry(timestamp: str, others: list[str]) -> str:
    siblings = ", ".join(others) if others else "(none)"
    return (
        f"## {timestamp} — Closure (bundled)\n"
        f"\n"
        f"- **Bundled with**: {siblings}\n"
    )


def _cmd_done_bundle(titles: list[str], force: bool) -> None:
    """Atomically close a set of cards with shared attestation + cross-refs.

    Preserves per-card DoD enforcement: any unchecked box on any card aborts
    the bundle before mutating disk.
    """
    seen: set[str] = set()
    deduped: list[str] = []
    for title in titles:
        if title in seen:
            print(f"goc: error: --bundle: duplicate title {title!r}", file=sys.stderr)
            sys.exit(2)
        seen.add(title)
        deduped.append(title)
    plan: list[tuple[str, Path, str, "Card"]] = []
    for title in deduped:
        card_dir = DECK_DIR / title
        t = load_card_or_exit(card_dir, title)
        if t.status == "done":
            print(
                f"ERROR: {title}: already done; --bundle refuses to re-close",
                file=sys.stderr,
            )
            sys.exit(2)
        if t.status in TERMINAL_STATUSES:
            print(
                f"ERROR: {title}: status is {t.status!r} (terminal); "
                f"use the supersede/disprove workflow — --bundle cannot overwrite terminal states",
                file=sys.stderr,
            )
            sys.exit(2)
        if t.dod_freeform and not force:
            print(
                f"ERROR: {title}: free-form DoD; use --force to bypass enforcement",
                file=sys.stderr,
            )
            sys.exit(2)
        if t.dod_open > 0:
            print(
                f"ERROR: {title}: {t.dod_open} unchecked DoD boxes; refusing bundled close",
                file=sys.stderr,
            )
            sys.exit(2)
        if t.human_gate != "none":
            print(
                f"ERROR: {title}: human_gate is {t.human_gate!r}; "
                f"run `goc decide {title} --decision <choice> --because <reason>` "
                f"to lower the gate before closing.",
                file=sys.stderr,
            )
            sys.exit(2)
        plan.append((title, card_dir, t.status, t))
    for title, _, _, _ in plan:
        _enforce_closure_on_integration_or_exit(title)
    now = _utc_now_iso()
    bundle_titles = [title for title, _, _, _ in plan]
    attestation_block = _format_bundle_attestation_block(now, bundle_titles)
    for title, card_dir, prior, _ in plan:
        log_path = card_dir / "log.md"
        others = [other for other in bundle_titles if other != title]
        closure_entry = _format_bundle_closure_entry(now, others)
        existing = log_path.read_text() if log_path.exists() else ""
        appendix = attestation_block + "\n" + closure_entry
        log_path.write_text(
            (existing.rstrip() + "\n\n" + appendix) if existing.strip() else appendix
        )
        text = (card_dir / "README.md").read_text()
        text = mutate_frontmatter_field(text, "status", "done")
        text = mutate_frontmatter_field(text, "closed_at", _yaml_inline(now))
        (card_dir / "README.md").write_text(text)
        print(f"{title}: {prior} → done")
    print(f"\nBundled close: {len(plan)} cards.")
    print("Next: commit the closures together.")


# ────────────────────────────────────────────────────────────────────────────
# Auto-commit policy — claim/decide/advance state changes can commit
# immediately so multi-branch deck work synchronizes via git rather than
# racing on uncommitted YAML. The default is configured in
# .game-of-cards/config.yaml; per-command flags override it.


def _git_auto_commit(card_dirs: list[Path], message: str) -> bool:  # noqa: PLR0911
    """Stage README.md + log.md across the given card dirs and commit.

    Returns True if a commit landed; False if skipped (not a git repo,
    mid-merge/rebase/cherry-pick, no diff to commit, or git missing).
    Skipping is silent and non-fatal — the state mutation already wrote
    to disk; an autocommit failure shouldn't roll that back.
    """
    if not card_dirs:
        return False
    # Deck files may live in the shared primary working tree (DECK_ROOT),
    # not the current worktree (REPO_ROOT). Git operations on deck files
    # must use DECK_ROOT so relative paths and staging work correctly.
    git_cwd = str(DECK_ROOT)
    try:
        repo_check = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            cwd=git_cwd,
            check=False,
        )
        if repo_check.returncode != 0:
            return False
        git_dir = Path(repo_check.stdout.strip())
        if not git_dir.is_absolute():
            git_dir = DECK_ROOT / git_dir
        # REBASE_HEAD alone is insufficient: it is absent at a paused
        # interactive-rebase stop (break/edit step). The rebase state
        # directory (rebase-merge for the merge backend, rebase-apply for
        # the apply backend) is present for the whole rebase, so check it too.
        if any(
            (git_dir / sf).exists()
            for sf in ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "rebase-merge", "rebase-apply")
        ):
            print("  (auto-commit skipped: merge/rebase/cherry-pick in progress)", file=sys.stderr)
            return False
        paths: list[str] = [
            str(p.relative_to(DECK_ROOT))
            for d in card_dirs
            for fname in ("README.md", "log.md")
            if (p := d / fname).exists()
        ]
        if not paths:
            return False
        subprocess.run(["git", "add", "--", *paths], check=True, cwd=git_cwd)
        diff_check = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--", *paths],
            cwd=git_cwd,
            check=False,
        )
        if diff_check.returncode == 0:
            return False
        subprocess.run(["git", "commit", "-m", message, "--", *paths], check=True, cwd=git_cwd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  (auto-commit failed: {e})", file=sys.stderr)
        return False
    except FileNotFoundError:
        return False


def _coerce_config_bool(value, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _validate_commit_flags(commit: bool, no_commit: bool) -> None:
    """Exit 2 on mutually-exclusive --commit / --no-commit BEFORE any disk
    write. Mutating verbs must call this at entry so a flag-conflict error
    can never leave a card half-mutated on disk without an auto-commit."""
    if commit and no_commit:
        print("ERROR: pass only one of --commit / --no-commit", file=sys.stderr)
        sys.exit(2)


def _commit_override(commit: bool, no_commit: bool) -> bool | None:
    if commit and no_commit:
        print("ERROR: pass only one of --commit / --no-commit", file=sys.stderr)
        sys.exit(2)
    if commit:
        return True
    if no_commit:
        return False
    return None


def _deck_is_git_tracked() -> bool:
    """Return True if DECK_DIR sits inside a git repo and is not gitignored."""
    try:
        repo_check = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            cwd=str(DECK_ROOT),
            check=False,
        )
        if repo_check.returncode != 0:
            return False
        # git check-ignore exits 0 if the path IS ignored, 1 if NOT ignored.
        ignore_check = subprocess.run(
            ["git", "check-ignore", "-q", str(DECK_DIR)],
            capture_output=True,
            cwd=str(DECK_ROOT),
            check=False,
        )
        return ignore_check.returncode != 0
    except FileNotFoundError:
        return False


_autocommit_warning_emitted: bool = False


def auto_commit_enabled(override: bool | None = None) -> bool:
    global _autocommit_warning_emitted
    if override is not None:
        return override
    if not _deck_is_git_tracked():
        return False
    config = load_deck_config()
    workflow = config.get("workflow") or {}
    enabled = _coerce_config_bool(workflow.get("auto_commit"), default=True)
    if not enabled and not _autocommit_warning_emitted:
        _autocommit_warning_emitted = True
        print(
            "  Warning: auto_commit is disabled but the deck is version-controlled."
            " Parallel agents will not see claim/progress state until you commit manually.",
            file=sys.stderr,
        )
    return enabled


def _enforce_closure_on_integration_or_exit(title: str) -> None:
    """When workflow.closure_on_integration is enabled, refuse closure unless
    HEAD is reachable from origin/main.

    Multi-team policy: a card cannot transition to `done` until its work is
    integrated to the canonical branch — `done` must mean "visible to every
    participant", not just "locally DoD-complete". Opt-in; default off.
    """
    config = load_deck_config()
    workflow = config.get("workflow") or {}
    if not _coerce_config_bool(workflow.get("closure_on_integration"), default=False):
        return
    if not _deck_is_git_tracked():
        return
    git_cwd = str(DECK_ROOT)
    fetch = subprocess.run(
        ["git", "fetch", "--quiet", "origin", "main"],
        capture_output=True,
        text=True,
        cwd=git_cwd,
        check=False,
    )
    if fetch.returncode != 0:
        print(
            "  Warning: closure_on_integration is enabled but `git fetch origin main` failed; skipping check",
            file=sys.stderr,
        )
        return
    check = subprocess.run(
        ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],
        capture_output=True,
        cwd=git_cwd,
        check=False,
    )
    if check.returncode != 0:
        print(
            f"ERROR: {title}: closure_on_integration is enabled and HEAD is not"
            " reachable from origin/main. Integrate the work (merge or push)"
            " before closing — `done` must be visible to every participant.",
            file=sys.stderr,
        )
        sys.exit(2)


def claim_push_enabled() -> bool:
    """Return True when workflow.claim_push is set; default off.

    When enabled, `goc status <title> active` pushes the claim commit to the
    remote tracking branch and retries once on non-fast-forward, aborting if a
    rebase conflict reveals a concurrent claim. Off by default to preserve the
    solo workflow where pushes are user-driven.
    """
    if not _deck_is_git_tracked():
        return False
    config = load_deck_config()
    workflow = config.get("workflow") or {}
    return _coerce_config_bool(workflow.get("claim_push"), default=False)


def _git_claim_push_with_retry(card_dir: Path, title: str) -> bool:
    """Push the just-committed claim and retry once on non-fast-forward.

    Conflict semantics (per the design-claim-protocol decision): re-fetch and
    rebase on top of the remote. If the rebase fails — meaning another worker
    modified the same card concurrently — abort cleanly with the racing
    worker's identity so the caller knows the claim did not stick.

    Returns True on a clean push; False when the claim could not be published
    (the local commit is preserved either way; the caller decides what to do).
    """
    git_cwd = str(DECK_ROOT)
    branch_proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        cwd=git_cwd,
        check=False,
    )
    branch = branch_proc.stdout.strip()
    if not branch or branch == "HEAD":
        print("  Warning: detached HEAD; claim was committed locally but not pushed", file=sys.stderr)
        return False

    push = subprocess.run(
        ["git", "push", "origin", branch],
        capture_output=True,
        text=True,
        cwd=git_cwd,
        check=False,
    )
    if push.returncode == 0:
        print("  pushed")
        return True

    fetch = subprocess.run(
        ["git", "fetch", "--quiet", "origin", branch],
        capture_output=True,
        text=True,
        cwd=git_cwd,
        check=False,
    )
    if fetch.returncode != 0:
        print(
            f"  push failed and fetch failed: {(push.stderr or push.stdout).strip()}",
            file=sys.stderr,
        )
        return False

    rebase = subprocess.run(
        ["git", "rebase", f"origin/{branch}"],
        capture_output=True,
        text=True,
        cwd=git_cwd,
        check=False,
    )
    if rebase.returncode != 0:
        subprocess.run(["git", "rebase", "--abort"], cwd=git_cwd, check=False, capture_output=True)
        other = "<unknown>"
        try:
            rel = card_dir.relative_to(DECK_ROOT)
            remote_readme = subprocess.run(
                ["git", "show", f"origin/{branch}:{rel.as_posix()}/README.md"],
                capture_output=True,
                text=True,
                cwd=git_cwd,
                check=False,
            )
            if remote_readme.returncode == 0:
                fm, _body = parse_frontmatter(remote_readme.stdout)
                worker = fm.get("worker")
                if isinstance(worker, dict):
                    other = str(worker.get("who") or "<unknown>")
                elif isinstance(worker, str) and worker:
                    other = worker
        except Exception:
            pass
        print(
            f"ERROR: {title}: claim race — already claimed by {other!r} on origin/{branch}."
            f" Your local claim commit is unpushed; reset to origin/{branch} and pull a different card.",
            file=sys.stderr,
        )
        return False

    push2 = subprocess.run(
        ["git", "push", "origin", branch],
        capture_output=True,
        text=True,
        cwd=git_cwd,
        check=False,
    )
    if push2.returncode == 0:
        print("  pushed (after rebase)")
        return True
    print(
        f"  push failed after rebase: {(push2.stderr or push2.stdout).strip()}",
        file=sys.stderr,
    )
    return False


# ────────────────────────────────────────────────────────────────────────────
# Closure attestation — runs layer-2 (project) + layer-3 (GoC) DoD checks
# defined in .game-of-cards/config.yaml and records the result in log.md.


def load_deck_config() -> dict:
    if GAME_OF_CARDS_CONFIG_FILE.exists():
        return yaml.safe_load(GAME_OF_CARDS_CONFIG_FILE.read_text()) or {}
    if LEGACY_DECK_CONFIG_FILE.exists():
        return yaml.safe_load(LEGACY_DECK_CONFIG_FILE.read_text()) or {}
    return {"layer_2_project_dod": [], "layer_3_goc_dod": []}


SKILLS_SOURCE_VALUES = ("plugin", "vendored", "auto")
DEFAULT_SKILLS_SOURCE = "auto"


def get_skills_source() -> str:
    """Return the configured `skills_source` value, or 'auto' if absent/invalid.

    Reads `.game-of-cards/config.yaml` (or the legacy `.claude/config.yaml`).
    Invalid values fall back to 'auto' silently — the config is meant to be
    forward-compatible.
    """
    value = load_deck_config().get("skills_source")
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in SKILLS_SOURCE_VALUES:
            return normalized
    return DEFAULT_SKILLS_SOURCE


def _claude_plugin_present() -> bool:
    """True if the Claude Code GoC plugin appears installed on this host.

    Looks under `$CLAUDE_PLUGIN_ROOT` (if set) and the default Claude Code
    plugin directory (`~/.claude/plugins`) for a `game-of-cards*` plugin
    payload with a `skills/` subtree. Used only to resolve `skills_source: auto`.

    Accepted layouts (verified against live Claude Code installs):
      <root>/skills/                                          (root is the payload, e.g. CLAUDE_PLUGIN_ROOT)
      <root>/game-of-cards*/skills/                           (legacy direct)
      <root>/<marketplace>/game-of-cards*/skills/             (legacy 2-level)
      <root>/cache-or-data/<mkt>/game-of-cards*/<ver>/skills/ (modern versioned)

    The walk uses `rglob` to find any `game-of-cards*` directory and then
    accepts the payload if `skills/` is a direct child OR a grandchild
    (covering the `<plugin>/<version>/skills/` layout). `Path.rglob` does
    not follow symlinks in CPython 3.10+, so symlink loops can't hang it.
    """
    candidates: list[Path] = []
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        candidates.append(Path(env_root))
    candidates.append(Path.home() / ".claude" / "plugins")
    for root in candidates:
        try:
            if not root.exists() or not root.is_dir():
                continue
        except OSError:
            continue
        if (root / "skills").is_dir() and root.name.startswith("game-of-cards"):
            return True
        try:
            for plugin_dir in root.rglob("game-of-cards*"):
                if not plugin_dir.is_dir():
                    continue
                if (plugin_dir / "skills").is_dir():
                    return True
                try:
                    for version_dir in plugin_dir.iterdir():
                        if version_dir.is_dir() and (version_dir / "skills").is_dir():
                            return True
                except OSError:
                    continue
        except OSError:
            continue
    return False


def effective_skills_source() -> str:
    """Resolve the configured `skills_source` to a concrete 'plugin' or 'vendored'.

    'plugin' or 'vendored' configured → return as-is.
    'auto' (or unset/invalid) → detect Claude Code GoC plugin presence;
    return 'plugin' if found, else 'vendored'. The vendored fallback
    preserves the historical default for installs that predate this key.
    """
    configured = get_skills_source()
    if configured != "auto":
        return configured
    return "plugin" if _claude_plugin_present() else "vendored"


def _run_automated_check(check: dict) -> tuple[bool, str]:
    cmd = check["cmd"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(REPO_ROOT), check=False)
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT (>300s)"
    except FileNotFoundError:
        return False, f"command not found: {cmd[0]}"
    if result.returncode == 0:
        stdout_tail = (result.stdout or "").strip().split("\n")[-1]
        return True, (stdout_tail[:120] if stdout_tail else "OK")
    err_tail = ((result.stderr or result.stdout or "").strip().split("\n") or [""])[-1]
    return False, f"exit {result.returncode}: {err_tail[:120]}"


def _run_derived_check(check: dict, card: Card, all_cards: list, today: str) -> tuple[bool, str]:  # noqa: PLR0911
    name = check["name"]
    if name == "advanced-by-closed":
        advanced_by = card.frontmatter.get("advanced_by") or []
        if not isinstance(advanced_by, list):
            advanced_by = []
        if not advanced_by:
            return True, "no advanced_by edges"
        by_title = {c.title: c for c in all_cards}
        unclosed = [t for t in advanced_by if t in by_title and by_title[t].status not in TERMINAL_STATUSES]
        if unclosed:
            sample = ", ".join(unclosed[:3])
            hint = (
                f"wait for them to close, or if an edge is false, "
                f"retract it: `goc unadvance {card.title} --by <upstream>` "
                f"(prefer over `--skip`)"
            )
            return False, f"{len(unclosed)} not done: {sample} — {hint}"
        return True, f"all {len(advanced_by)} closed"
    if name == "dod-100-percent":
        if card.dod_freeform:
            return True, "freeform DoD"
        if card.dod_open > 0:
            return False, f"{card.dod_open} unchecked boxes"
        return True, f"{card.dod_done}/{card.dod_done} ticked"
    if name == "log-md-closure-entry":
        log_path = DECK_DIR / card.title / "log.md"
        if not log_path.exists():
            return False, "log.md missing"
        date_prefix = _date_part(today)
        # Match either legacy date-only (`## YYYY-MM-DD — Closure`) or the
        # current datetime form (`## YYYY-MM-DDTHH:MM:SSZ — Closure`).
        pattern = re.compile(
            rf"^## {re.escape(date_prefix)}(?:T\d{{2}}:\d{{2}}:\d{{2}}Z)? — Closure",
            re.MULTILINE,
        )
        if pattern.search(log_path.read_text()):
            return True, f"'## {date_prefix} — Closure' present"
        return False, f"no '## {date_prefix} — Closure' section"
    return False, f"unknown derived check '{name}'"


def _prompt_yes_no(prompt: str) -> str:
    return input(f"  {prompt} ").strip().lower()


def _prompt_manual(check: dict) -> tuple[bool, str]:
    answer = _prompt_yes_no(check.get("prompt", f"Did {check['name']} pass? (y/n)"))
    passed = answer in ("y", "yes")
    rationale_prompt = check.get("rationale_prompt", "")
    rationale = input(f"    {rationale_prompt} ").strip() if rationale_prompt else ""
    return passed, rationale or ("OK" if passed else "(declined)")


def _prompt_agent(check: dict) -> tuple[bool, str]:
    answer = _prompt_yes_no(check.get("prompt", f"Did {check['name']} report PASS? (y/n/n-a)"))
    if answer in ("n-a", "n/a", "na", "skip"):
        rationale = input(f"    {check.get('rationale_prompt', 'Reason:')} ").strip()
        return True, f"N/A — {rationale or 'no doc changes'}"
    passed = answer in ("y", "yes")
    rationale = input(f"    {check.get('rationale_prompt', '')} ").strip() if check.get("rationale_prompt") else ""
    return passed, rationale or ("OK" if passed else "(declined)")


def _format_attestation_block(today: str, results: list[dict]) -> str:
    lines = [f"## Closure verification ({today})", ""]
    for layer_num, label in [(2, "Layer-2 (project DoD)"), (3, "Layer-3 (GoC DoD)")]:
        layer_results = [r for r in results if r["layer"] == layer_num]
        if not layer_results:
            continue
        lines.append(f"### {label}")
        lines.append("")
        for r in layer_results:
            mark = "[~]" if r.get("skipped") else ("[x]" if r["passed"] else "[ ]")
            status = " SKIPPED —" if r.get("skipped") else (" FAIL —" if not r["passed"] else " —")
            lines.append(f"- {mark} {r['name']}{status} {r['summary']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _cmd_attest(args):
    """Run layer-2 + layer-3 closure checks; append "Closure verification" block to log.md.

    Empty-config contract: when both ``layer_2_project_dod`` and ``layer_3_goc_dod``
    are empty/unset, refuse the call (non-zero exit, no log.md mutation). Writing
    a bare ``## Closure verification`` header would satisfy the bundled
    ``log-md-closure-entry`` derived check on content that proves nothing.

    All-skipped contract: the same refusal applies when checks ARE configured
    but every one of them is covered by ``--skip`` — no check actually runs, so
    the all-``[~] SKIPPED`` block proves exactly as little as the bare header.
    "No check ran" is refused regardless of why none ran.
    """
    title = args.title
    skips = args.skips
    non_interactive = args.non_interactive
    card_dir = DECK_DIR / title
    card = load_card_or_exit(card_dir, title)
    config = load_deck_config()
    all_cards = load_all_cards()
    today = _utc_now_iso()
    skips_set = set(skips)
    results: list[dict] = []
    any_failed = False

    layer_2_checks = config.get("layer_2_project_dod") or []
    layer_3_checks = config.get("layer_3_goc_dod") or []
    if not layer_2_checks and not layer_3_checks:
        print(
            "ERROR: no closure checks configured (both layer_2_project_dod and "
            "layer_3_goc_dod are empty in .game-of-cards/config.yaml). "
            "goc attest refuses to run; configure at least one check or skip attestation.",
            file=sys.stderr,
        )
        sys.exit(2)

    all_check_names = {c["name"] for c in layer_2_checks} | {c["name"] for c in layer_3_checks}
    if all_check_names and all_check_names <= skips_set:
        print(
            "ERROR: every configured closure check was skipped via --skip "
            f"({', '.join(sorted(all_check_names))}). goc attest refuses to write a "
            "Closure verification block when no check actually runs; un-skip at "
            "least one check.",
            file=sys.stderr,
        )
        sys.exit(2)

    for layer_key, layer_num in [("layer_2_project_dod", 2), ("layer_3_goc_dod", 3)]:
        layer_checks = config.get(layer_key) or []
        if not layer_checks:
            continue
        print(f"\nLayer-{layer_num} ({'project' if layer_num == 2 else 'GoC'}) checks:")
        for check in layer_checks:
            name = check["name"]
            if name in skips_set:
                results.append(
                    {
                        "layer": layer_num,
                        "name": name,
                        "passed": True,
                        "skipped": True,
                        "summary": f"SKIPPED ({(check.get('description') or '')[:60]})",
                    }
                )
                print(f"  [~] {name} — SKIPPED")
                continue
            kind = check["kind"]
            try:
                if kind == "automated":
                    print(f"  ... running {name}")
                    passed, summary = _run_automated_check(check)
                elif kind == "derived":
                    passed, summary = _run_derived_check(check, card, all_cards, today)
                elif kind == "manual":
                    if non_interactive:
                        passed, summary = False, "non-interactive: manual check declined"
                    else:
                        passed, summary = _prompt_manual(check)
                elif kind == "agent":
                    if non_interactive:
                        passed, summary = False, "non-interactive: agent check declined"
                    else:
                        passed, summary = _prompt_agent(check)
                else:
                    passed, summary = False, f"unknown check kind '{kind}'"
            except KeyboardInterrupt:
                print(f"\nABORTED on {name}", file=sys.stderr)
                sys.exit(130)
            results.append({"layer": layer_num, "name": name, "passed": passed, "summary": summary})
            mark = "[x]" if passed else "[ ]"
            print(f"  {mark} {name} — {summary}")
            if not passed:
                any_failed = True

    log_path = card_dir / "log.md"
    block = _format_attestation_block(today, results)
    existing = log_path.read_text() if log_path.exists() else ""
    log_path.write_text((existing.rstrip() + "\n\n" + block) if existing.strip() else block)
    print(f"\nWrote attestation to {log_path}")

    if any_failed:
        print("\nERROR: attestation has failures; finish-card will block closure.", file=sys.stderr)
        sys.exit(2)
    print("\nAttestation OK.")
    print(f"Next: goc done {title} to close once all DoD items are ticked.")


def _auto_populate_worker(text: str, card: "Card", worker_who: str | None, worker_where: str | None) -> str:
    """Populate the `worker` field on a card being claimed as active.

    If the card already has a worker.who (designation), preserve it and only
    add/update `where`. If no prior worker, auto-detect `who` from git config
    and `where` from the current branch. Explicit --worker-who / --worker-where
    flags override auto-detection for either sub-field.
    """
    existing = card.frontmatter.get("worker")
    if isinstance(existing, str):
        existing_dict: dict = {"who": existing}
    elif isinstance(existing, dict):
        existing_dict = dict(existing)
    else:
        existing_dict = {}

    if worker_who is not None:
        who = worker_who
    elif "who" in existing_dict:
        who = existing_dict["who"]
    else:
        r = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=5)
        who = r.stdout.strip() if r.returncode == 0 else ""

    if worker_where is not None:
        where: str | None = worker_where
    else:
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=5)
        where = r.stdout.strip() if r.returncode == 0 else None
        if where in ("", "HEAD"):
            where = None
        if where is None:
            # No detectable branch (detached HEAD / fresh checkout): preserve any
            # stored branch context rather than dropping it. A detectable branch
            # still updates `where` (the documented "add/update where" intent).
            where = existing_dict.get("where")

    # A worker mapping requires a non-empty `who`; a `where`-only worker is
    # rejected by validate_card. So if `who` is unknown (e.g. git user.name is
    # unset on a CI/container checkout) there is no valid worker to stamp — even
    # when a branch is known — and we leave the card untouched rather than write
    # an invalid `{who: "", where: <branch>}` that self-corrupts the card.
    if not who:
        return text

    # Build the YAML inline value and mutate the frontmatter line-anchored.
    who_yaml = _yaml_inline(who)
    if where:
        where_yaml = _yaml_inline(where)
        worker_yaml = f"{{who: {who_yaml}, where: {where_yaml}}}"
    else:
        worker_yaml = who_yaml
    return mutate_frontmatter_field(text, "worker", worker_yaml)


def _cmd_status(args):
    """Mutate any status except `done` (which has its own enforcement gate)."""
    title = args.title
    new_status = args.new_status
    commit = args.commit
    no_commit = args.no_commit
    _validate_commit_flags(commit, no_commit)
    worker_who = args.worker_who
    worker_where = args.worker_where
    successor = args.superseded_by
    if successor is not None and new_status != "superseded":
        print(
            f"ERROR: --by is only valid with new_status=superseded "
            f"(got new_status={new_status!r})",
            file=sys.stderr,
        )
        sys.exit(2)
    if new_status == "superseded" and successor is None:
        print(
            f"ERROR: status superseded requires --by <successor> "
            f"(the typed forward routing pointer; without it a cold reader "
            f"landing on {title!r} has nowhere to go)",
            file=sys.stderr,
        )
        sys.exit(2)
    if successor is not None and successor == title:
        print(f"ERROR: --by {successor!r} cannot equal the card being superseded", file=sys.stderr)
        sys.exit(2)
    if successor is not None:
        successor_dir = DECK_DIR / successor
        # Existence/loadability check only — the successor may carry any
        # status. A supersession's successor is the work that replaces the
        # old card and is meant to be completed, so the typed forward
        # pointer may legitimately land on a terminal card (a `done`
        # resolution, or a `superseded` card that routes onward). See
        # `validate_superseded_by_targets` for the full rationale.
        load_card_or_exit(successor_dir, successor)
    card_dir = DECK_DIR / title
    t = load_card_or_exit(card_dir, title)
    prior = t.status
    if prior == new_status:
        if new_status == "active":
            print(
                f"WARNING: {title}: already active — possible racing claim;"
                f" check `goc --status active` before proceeding",
                file=sys.stderr,
            )
        else:
            print(f"{title}: already {new_status}; nothing to do")
        return
    if prior in TERMINAL_STATUSES:
        print(
            f"ERROR: {title}: status is {prior!r} (terminal);"
            f" terminal cards cannot be moved backward through `goc status`",
            file=sys.stderr,
        )
        sys.exit(2)
    if new_status in TERMINAL_STATUSES and t.human_gate != "none":
        print(
            f"ERROR: {title}: human_gate is {t.human_gate!r}; "
            f"run `goc decide {title} --decision <choice> --because <reason>` "
            f"to lower the gate before closing into {new_status!r}.",
            file=sys.stderr,
        )
        sys.exit(2)
    if successor is not None and _would_create_supersedes_cycle(load_all_cards(), title, successor):
        print(
            f"ERROR: superseding {title} by {successor} would create a cycle in "
            f"the supersession graph ({successor} already reaches {title} through "
            f"superseded_by); a forward walk would never terminate",
            file=sys.stderr,
        )
        sys.exit(2)
    text = (card_dir / "README.md").read_text()
    text = mutate_frontmatter_field(text, "status", new_status)
    if new_status in TERMINAL_STATUSES:
        text = mutate_frontmatter_field(text, "closed_at", _yaml_inline(_utc_now_iso()))
    if new_status == "active":
        text = _auto_populate_worker(text, t, worker_who, worker_where)
    (card_dir / "README.md").write_text(text)
    if successor is not None:
        # Maintain typed bidirectional supersession link on both endpoints.
        _mutate_pair(title, successor, "superseded_by", "supersedes", add=True)
    print(f"{title}: {prior} → {new_status}")
    if successor is not None:
        print(f"  superseded_by: {successor}; {successor}.supersedes += {title}")
    if new_status == "active":
        print(f"Next: implement the card; tick DoD items as you go; then goc done {title}.")
    commit_policy = _commit_override(commit, no_commit)
    if auto_commit_enabled(commit_policy):
        commit_targets = [card_dir]
        if successor is not None:
            commit_targets.append(DECK_DIR / successor)
        if _git_auto_commit(commit_targets, f"deck: {title} {prior} → {new_status}"):
            print("  committed")
            if new_status == "active" and claim_push_enabled():
                if not _git_claim_push_with_retry(card_dir, title):
                    sys.exit(2)


TITLE_ANTIPATTERNS = [
    (re.compile(r"\br\d+\b"), "internal investigation-round reference (rN); describe the *observable problem* instead"),
    (re.compile(r"\bpath-\d+\b"), "sub-investigation step number; promote to a noun-phrase deliverable"),
    (re.compile(r"\bphase-\d+\b"), "internal sequence reference; name the deliverable instead"),
    (re.compile(r"\bbug-\d+\b"), "bug-tracker numbering; use the defect-shape clause"),
    (re.compile(r"_md_|_py_"), "source-file infix; describe the *concept*, not the file"),
    (re.compile(r"[a-z][A-Z]"), "camelCase token; lower-kebab the intent"),
    (re.compile(r"[^a-zA-Z0-9\s_-]"), "math/symbol or non-ASCII character; use words (gte, at-least) — the slug allows [a-z0-9-] only"),
    (re.compile(r"_"), "underscore in slug; lower-kebab the intent — underscores aren't allowed"),
]


def _check_title_antipatterns(title: str) -> list[str]:
    """Return list of (matched_substring, reason) tuples; empty if title is clean."""
    return [reason for pat, reason in TITLE_ANTIPATTERNS if pat.search(title)]


def _unique_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _validate_new_edge_flags(
    title: str,
    card_dir: Path,
    advances: list[str],
    advanced_by: list[str],
) -> None:
    """Validate all requested `goc new` edge wiring before touching disk."""
    if not advances and not advanced_by:
        return

    cards = load_all_cards()
    by_title = {card.title: card for card in cards}
    missing = [ref for ref in [*advances, *advanced_by] if ref not in by_title]
    if missing:
        refs = ", ".join(_unique_preserving_order(missing))
        print(f"ERROR: cannot create {title}: referenced card(s) not found: {refs}", file=sys.stderr)
        sys.exit(2)

    # Outgoing edges from the new card are enough to check whether any
    # incoming edge would close an existing advances path back to its parent.
    simulated_new_card = Card(
        title=title,
        path=card_dir,
        frontmatter={"title": title, "advances": list(advances), "advanced_by": []},
        body="",
        dod_open=0,
        dod_done=0,
    )
    simulated_cards = [*cards, simulated_new_card]
    for advancer in advanced_by:
        if _would_create_advance_cycle(simulated_cards, title, advancer):
            print(
                f"ERROR: adding {advancer} → {title} would create a cycle in the advances graph",
                file=sys.stderr,
            )
            sys.exit(2)


def _cmd_new(args):
    """Scaffold a new card dir with valid frontmatter and empty log.md."""
    title = args.title
    schema = load_schema()
    contribution = args.contribution or (
        "medium" if "medium" in schema.contribution_values else schema.contribution_values[0]
    )
    gate = args.gate
    tags = args.tags
    worker = args.worker
    allow_jargon = args.allow_jargon
    commit = args.commit
    no_commit = args.no_commit
    _validate_commit_flags(commit, no_commit)
    advances = _unique_preserving_order(args.advances_wire or [])
    advanced_by = _unique_preserving_order(args.advanced_by_wire or [])
    if not allow_jargon:
        antipatterns_hit = _check_title_antipatterns(title)
        if antipatterns_hit:
            print(f"ERROR: title {title!r} contains engineer-jargon antipattern(s):", file=sys.stderr)
            for reason in antipatterns_hit:
                print(f"  - {reason}", file=sys.stderr)
            print(
                "\n  Titles are kanban labels; a non-engineer must understand the card from the title alone.", file=sys.stderr
            )
            print("  Rephrase to describe the *observable problem* (e.g.", file=sys.stderr)
            print("    `r88-csubstrate-replication` → `pong-cannot-recover-prior-task-performance`).", file=sys.stderr)
            print("  Pass --allow-jargon to bypass (rare; for migration tools).", file=sys.stderr)
            sys.exit(2)
    if not re.match(schema.title_pattern, title):
        print(f"ERROR: title {title!r} does not match {schema.title_pattern!r}", file=sys.stderr)
        sys.exit(2)
    card_dir = DECK_DIR / title
    if card_dir.exists():
        print(f"ERROR: {card_dir} already exists", file=sys.stderr)
        sys.exit(2)
    for tag in tags:
        if tag not in schema.canonical_tags:
            print(
                f"ERROR: unknown tag '{tag}' — {_UNKNOWN_TAG_REMEDY}",
                file=sys.stderr,
            )
            sys.exit(2)
    _validate_new_edge_flags(title, card_dir, advances, advanced_by)
    card_dir.mkdir(parents=True)
    now = _utc_now_iso()
    fm = {
        "title": title,
        "status": "open",
        "stage": None,
        "contribution": contribution,
        "created": now,
        "closed_at": None,
        "human_gate": gate,
        "advances": [],
        "advanced_by": [],
        "tags": list(tags),
        "definition_of_done": "- [ ] (replace with real criteria)",
    }
    if worker:
        fm["worker"] = worker
    body = f"\n# {title}\n\n(write the design doc here)\n"
    (card_dir / "README.md").write_text(emit_frontmatter(fm, body=body))
    (card_dir / "log.md").write_text("")
    for target in advances:
        _mutate_pair(target, title, "advanced_by", "advances", add=True)
    for advancer in advanced_by:
        _mutate_pair(title, advancer, "advanced_by", "advances", add=True)
    print(f"created {card_dir.relative_to(REPO_ROOT)}/")
    print(f"Next: edit {card_dir.relative_to(REPO_ROOT)}/README.md to fill the body and DoD; then ask your agent to implement the card.")
    # Default for `goc new` is NO commit so the scaffold-then-fill-in
    # workflow is unchanged; --commit is the opt-in for wired filings so
    # the new card's edge writes to existing endpoints don't linger as
    # ambient ` M` in the worktree (the half-edge defect).
    if _commit_override(commit, no_commit) is True:
        commit_targets = [card_dir, *(DECK_DIR / t for t in advances + advanced_by)]
        if _git_auto_commit(commit_targets, f"deck: new {title}"):
            print("  committed")


def _add_to_list_field(text: str, field: str, title_to_add: str) -> str:
    """Add title_to_add to a frontmatter list field, idempotent."""
    fm, body = parse_frontmatter(text)
    cur = fm.get(field) or []
    if not isinstance(cur, list):
        raise ValueError(f"{field}: not a list")
    if title_to_add in cur:
        return text
    cur.append(title_to_add)
    fm[field] = cur
    return emit_frontmatter(fm, body=body)


def _remove_from_list_field(text: str, field: str, title_to_remove: str) -> str:
    fm, body = parse_frontmatter(text)
    cur = fm.get(field) or []
    if title_to_remove not in cur:
        return text
    fm[field] = [s for s in cur if s != title_to_remove]
    return emit_frontmatter(fm, body=body)


def _mutate_pair(child_title: str, parent_title: str, field_on_child: str, field_on_parent: str, *, add: bool) -> None:
    """Add or remove a bidirectional edge between two cards."""
    child_dir = DECK_DIR / child_title
    parent_dir = DECK_DIR / parent_title
    # load_card_or_exit gates on parseable frontmatter so the subsequent
    # parse_frontmatter calls inside _add_to_list_field / _remove_from_list_field
    # never see malformed input.
    load_card_or_exit(child_dir, child_title)
    load_card_or_exit(parent_dir, parent_title)
    op = _add_to_list_field if add else _remove_from_list_field
    child_text = (child_dir / "README.md").read_text()
    parent_text = (parent_dir / "README.md").read_text()
    (child_dir / "README.md").write_text(op(child_text, field_on_child, parent_title))
    (parent_dir / "README.md").write_text(op(parent_text, field_on_parent, child_title))


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _repair_edge_diff(edge: HalfEdge) -> list[str]:
    readme = DECK_DIR / edge.repair_title / "README.md"
    original = readme.read_text()
    repaired = _add_to_list_field(original, edge.repair_field, edge.repair_value)
    if repaired == original:
        return []
    rel = _display_path(readme)
    return list(
        difflib.unified_diff(
            original.splitlines(),
            repaired.splitlines(),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            lineterm="",
        )
    )


def _repair_edge_cycle_problem(edge: HalfEdge, cards: list[Card]) -> str | None:
    # Both edge sets can cycle: advances directly, and supersession because
    # `goc status … superseded` only makes the *holder* terminal, leaving the
    # successor free to be superseded back (see detect_supersedes_cycles).
    if edge.is_advance:
        if _would_create_advance_cycle(cards, edge.child_title, edge.parent_title):
            return (
                f"{edge.parent_title} → {edge.child_title} would create a cycle "
                "in the advances graph"
            )
        return None
    # Supersession half-edge: identify the `superseded_by` direction (holder→successor).
    if edge.field == "superseded_by":
        holder, successor = edge.src, edge.ref
    else:  # supersedes
        holder, successor = edge.ref, edge.src
    if _would_create_supersedes_cycle(cards, holder, successor):
        return (
            f"{holder} → {successor} would create a cycle in the supersession graph"
        )
    return None


def _print_structural_edge_problems(problems: list[tuple[HalfEdge, str]]) -> None:
    if not problems:
        return
    print("Structural problems requiring human review:", file=sys.stderr)
    for edge, problem in problems:
        print(f"  {edge.message}: {problem}", file=sys.stderr)


def _simulate_repair(by_title: dict[str, "Card"], edge: HalfEdge) -> None:
    """Mirror `_mutate_pair`'s on-disk effect in memory.

    A repair adds the missing reverse half (`edge.src` → `edge.ref.inverse`);
    the forward half already exists by construction, so it is a no-op. Applying
    just the reverse half to the shared in-memory `Card` objects lets later
    cycle checks in the same classification pass observe this repair — exactly
    as `--apply` would by re-loading from disk before each edge.
    """
    target = by_title.get(edge.ref)
    if target is None:
        return
    cur = target.frontmatter.get(edge.inverse) or []
    if not isinstance(cur, list):
        cur = []
    if edge.src not in cur:
        target.frontmatter[edge.inverse] = [*cur, edge.src]


def _classify_half_edges(
    half_edges: list[HalfEdge], cards: list["Card"]
) -> tuple[list[HalfEdge], list[tuple[HalfEdge, str]]]:
    """Split half-edges into (fixable, structural) against an evolving graph.

    Single source of truth for both the dry-run preview and `--apply`: each
    edge is classified, then — if fixable — its repair is simulated in memory
    so subsequent cycle checks see the forward edges earlier repairs add. This
    is what keeps the preview honest: when repairing one half-edge closes a
    cycle for a later one, both passes classify the later edge as structural.
    """
    by_title = {c.title: c for c in cards}
    fixable: list[HalfEdge] = []
    structural: list[tuple[HalfEdge, str]] = []
    for edge in half_edges:
        problem = _repair_edge_cycle_problem(edge, cards)
        if problem:
            structural.append((edge, problem))
            continue
        fixable.append(edge)
        _simulate_repair(by_title, edge)
    return fixable, structural


def _cmd_repair_edges(args):
    """Preview or repair asymmetric bidirectional half-edges (advances/advanced_by, supersedes/superseded_by)."""
    cards = load_all_cards()
    half_edges = find_half_edges(cards)
    if not half_edges:
        print("No half-edges found.")
        return

    fixable, structural = _classify_half_edges(half_edges, cards)

    if not args.apply:
        if fixable:
            print(f"Half-edges that would be repaired ({len(fixable)}):")
            for edge in fixable:
                print(f"\n# {edge.message}")
                diff = _repair_edge_diff(edge)
                if diff:
                    print("\n".join(diff))
                else:
                    print("(already repaired on disk)")
        _print_structural_edge_problems(structural)
        print("\nDry run — no changes made. Run 'goc repair-edges --apply' to write fixes.")
        return

    repaired = 0
    # `fixable` was classified against the same evolving graph `--apply` would
    # observe by reloading before each edge (see `_classify_half_edges`), so it
    # already excludes edges made structural by an earlier same-run repair.
    # Applying the missing reverse half is idempotent for any LIST_REL_FIELDS
    # pair, since the forward edge exists by construction.
    for edge in fixable:
        _mutate_pair(edge.ref, edge.src, edge.inverse, edge.field, add=True)
        print(f"repaired: {edge.message}")
        repaired += 1

    if repaired:
        print(f"Repaired {repaired} half-edge(s).")
    else:
        print("No half-edges repaired.")
    _print_structural_edge_problems(structural)
    if structural:
        sys.exit(1)


def _cmd_wait(args):
    """Set or clear the impediment overlay (`waiting_on` + `waiting_until`).

    The overlay is orthogonal to `status` — a card may be active AND
    impeded. `--clear` drops both fields; otherwise `--reason` and/or
    `--until` set the overlay.
    """
    _validate_commit_flags(args.commit, args.no_commit)
    title = args.title
    card_dir = DECK_DIR / title
    t = load_card_or_exit(card_dir, title)
    schema = load_schema()
    text = (card_dir / "README.md").read_text()
    fm, body = parse_frontmatter(text)
    prior_reason = fm.get("waiting_on")
    prior_until = fm.get("waiting_until")
    if args.clear:
        if prior_reason is None and prior_until is None:
            print(f"{title}: no waiting overlay to clear; nothing to do")
            return
        fm.pop("waiting_on", None)
        fm.pop("waiting_until", None)
        new_reason: str | None = None
        new_until: str | None = None
    else:
        if not args.reason and not args.until:
            print(
                "ERROR: pass --reason and/or --until (or --clear to drop the overlay)",
                file=sys.stderr,
            )
            sys.exit(2)
        new_reason = args.reason
        new_until = args.until
        if new_reason is not None and new_reason not in schema.waiting_on_values:
            print(
                f"ERROR: --reason: {new_reason!r} not in {schema.waiting_on_values}",
                file=sys.stderr,
            )
            sys.exit(2)
        if new_until is not None and not _is_iso_date(new_until):
            print(
                f"ERROR: --until: {new_until!r} not a valid ISO YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ date",
                file=sys.stderr,
            )
            sys.exit(2)
        if new_reason is not None:
            fm["waiting_on"] = new_reason
        if new_until is not None:
            fm["waiting_until"] = new_until
    (card_dir / "README.md").write_text(emit_frontmatter(fm, body=body))
    effective_reason = fm.get("waiting_on") or ("deferred" if fm.get("waiting_until") else None)
    if args.clear:
        print(
            f"{title}: waiting overlay cleared "
            f"(was waiting_on={prior_reason!r}, waiting_until={prior_until!r})"
        )
    else:
        print(
            f"{title}: waiting_on={fm.get('waiting_on')!r} "
            f"waiting_until={fm.get('waiting_until')!r}"
            + (f" (no reason set; implied {effective_reason!r})"
               if fm.get("waiting_on") is None and effective_reason else "")
        )
    commit_policy = _commit_override(args.commit, args.no_commit)
    if auto_commit_enabled(commit_policy):
        msg = (
            f"deck: {title} clear waiting overlay"
            if args.clear
            else f"deck: {title} waiting_on {fm.get('waiting_on') or 'deferred'}"
        )
        if _git_auto_commit([card_dir], msg):
            print("  committed")


def _cmd_advance(args):
    """Add bidirectional value-flow edge: title.advanced_by += advancer, advancer.advances += title."""
    title = args.title
    advancer = args.advancer
    commit = args.commit
    no_commit = args.no_commit
    _validate_commit_flags(commit, no_commit)
    if title == advancer:
        print("ERROR: cannot advance a card with itself", file=sys.stderr)
        sys.exit(2)
    cards = load_all_cards()
    if _would_create_advance_cycle(cards, title, advancer):
        print(f"ERROR: adding {advancer} → {title} would create a cycle in the advances graph", file=sys.stderr)
        sys.exit(2)
    _mutate_pair(title, advancer, "advanced_by", "advances", add=True)
    print(f"advance: {title}.advanced_by += {advancer}; {advancer}.advances += {title}")
    commit_policy = _commit_override(commit, no_commit)
    if auto_commit_enabled(commit_policy):
        if _git_auto_commit([DECK_DIR / title, DECK_DIR / advancer], f"deck: {advancer} advances {title}"):
            print("  committed")


def _cmd_unadvance(args):
    """Remove bidirectional value-flow edge."""
    title = args.title
    advancer = args.advancer
    commit = args.commit
    no_commit = args.no_commit
    _validate_commit_flags(commit, no_commit)
    _mutate_pair(title, advancer, "advanced_by", "advances", add=False)
    print(f"unadvance: {title}.advanced_by -= {advancer}; {advancer}.advances -= {title}")
    commit_policy = _commit_override(commit, no_commit)
    if auto_commit_enabled(commit_policy):
        if _git_auto_commit([DECK_DIR / title, DECK_DIR / advancer], f"deck: {advancer} no longer advances {title}"):
            print("  committed")


def _move_text_rewrite(text: str, old: str, new: str) -> str:
    """Rewrite old slug to new in the four canonical text forms."""
    esc = re.escape(old)
    # H1 heading at line start
    text = re.sub(rf"^(# ){esc}$", rf"\g<1>{new}", text, flags=re.MULTILINE)
    # Markdown cross-link: [old](../old/)
    text = text.replace(f"[{old}](../{old}/)", f"[{new}](../{new}/)")
    # Path forms
    text = text.replace(f".game-of-cards/deck/{old}/", f".game-of-cards/deck/{new}/")
    text = text.replace(f"deck/{old}/", f"deck/{new}/")
    # Bare slug: not preceded/followed by [-\w] (slug-boundary anchoring)
    text = re.sub(rf"(?<![-\w]){esc}(?![-\w])", new, text)
    return text


def _move_iter_tracked_text_files():
    """Yield (Path, str) for in-repo text files; falls back to rglob outside git.

    Enumerates tracked AND untracked-but-not-ignored files (`--cached --others
    --exclude-standard`), not tracked files alone. A card filed with `goc new`
    is untracked until its first commit, so the routine file-then-rename flow
    (`goc new <slug>` → `goc move <slug> <better-slug>` before committing) would
    otherwise have the moved card's own README.md/log.md skipped by the rewrite
    — the directory gets renamed (via the `shutil.move` fallback, since `git mv`
    also refuses an untracked source) while the in-file `title:` field stays
    stale, leaving a card that fails `goc validate`. Ignored files (venv, build
    artifacts) stay excluded, matching the `.git`-pruning rglob fallback's intent.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=str(REPO_ROOT), capture_output=True, check=True, timeout=30,
        )
        seen: set[str] = set()
        paths = []
        for entry in result.stdout.split(b"\x00"):
            if not entry:
                continue
            rel = entry.decode("utf-8", errors="replace")
            # --cached and --others are disjoint, but dedupe defensively so a
            # path is never rewritten twice.
            if rel in seen:
                continue
            seen.add(rel)
            paths.append(REPO_ROOT / rel)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        paths = [p for p in REPO_ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]
    for path in paths:
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()
            if b"\x00" in raw:
                continue
            yield path, raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue


def _move_rewrite_tracked_files(old: str, new: str) -> list[Path]:
    """Rewrite all tracked text files; return modified paths."""
    modified = []
    for path, original in _move_iter_tracked_text_files():
        rewritten = _move_text_rewrite(original, old, new)
        if rewritten != original:
            path.write_text(rewritten, encoding="utf-8")
            modified.append(path)
    return modified


def _move_preview_sites(old: str, new: str) -> list[str]:
    """Return 'file:line: ...' preview strings for --dry-run."""
    sites = []
    for path, original in _move_iter_tracked_text_files():
        rewritten = _move_text_rewrite(original, old, new)
        if rewritten == original:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        orig_lines = original.splitlines()
        new_lines = rewritten.splitlines()
        for i, (ol, nl) in enumerate(zip(orig_lines, new_lines), 1):
            if ol != nl:
                sites.append(f"{rel}:{i}: {ol.strip()!r} → {nl.strip()!r}")
        if len(orig_lines) != len(new_lines):
            sites.append(f"{rel}: (line count changed {len(orig_lines)} → {len(new_lines)})")
    return sites


def _cmd_move(args):
    """Rename a title and rewrite known cross-references."""
    old_title = args.old_title
    new_title = args.new_title
    allow_jargon = args.allow_jargon
    dry_run = args.dry_run
    schema = load_schema()
    if not allow_jargon:
        antipatterns_hit = _check_title_antipatterns(new_title)
        if antipatterns_hit:
            print(f"ERROR: title {new_title!r} contains engineer-jargon antipattern(s):", file=sys.stderr)
            for reason in antipatterns_hit:
                print(f"  - {reason}", file=sys.stderr)
            print(
                "\n  Titles are kanban labels; a non-engineer must understand the card from the title alone.", file=sys.stderr
            )
            print("  Rephrase to describe the *observable problem* (e.g.", file=sys.stderr)
            print("    `r88-csubstrate-replication` → `pong-cannot-recover-prior-task-performance`).", file=sys.stderr)
            print("  Pass --allow-jargon to bypass (rare; for migration tools).", file=sys.stderr)
            sys.exit(2)
    if not re.match(schema.title_pattern, new_title):
        print(f"ERROR: title {new_title!r} does not match {schema.title_pattern!r}", file=sys.stderr)
        sys.exit(2)
    src = DECK_DIR / old_title
    dst = DECK_DIR / new_title
    if not src.exists():
        print(f"ERROR: {src} does not exist", file=sys.stderr)
        sys.exit(2)
    if dst.exists():
        print(f"ERROR: {dst} already exists", file=sys.stderr)
        sys.exit(2)

    if dry_run:
        sites = _move_preview_sites(old_title, new_title)
        if sites:
            for site in sites:
                print(site)
        else:
            print("(no tracked text files would be modified)")
        print(f"(directory move: {src} → {dst})")
        return

    try:
        subprocess.run(["git", "mv", str(src), str(dst)], cwd=REPO_ROOT, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        shutil.move(str(src), str(dst))

    # Repo-wide text rewrite: H1s, markdown links, path forms, bare slugs,
    # frontmatter title/advances/advanced_by fields.
    _move_rewrite_tracked_files(old_title, new_title)

    now = _utc_now_iso()
    log_path = dst / "log.md"
    existing = log_path.read_text() if log_path.exists() else ""
    sep = "\n\n" if existing.strip() else ""
    log_path.write_text(existing.rstrip("\n") + sep + f"## {now}: renamed from {old_title}\n")

    print(f"{old_title} → {new_title}")


def _rescope_reconciliation_notice(t: Card, persisted_body: str) -> str:
    """Build the post-`goc decide` reminder shown when a decision re-scopes or
    reverses a prior verdict.

    `goc decide` updates only the `## Decision` block and the gate. A re-scope
    leaves the card's *other* verdict-bearing surfaces — its `summary`, a body
    `> ⚠` banner, DoD wording — and any reference to the card in its
    `advances`/`advanced_by` neighbors asserting the *old* verdict. Those are
    not auto-updated; this notice names them so the operator reconciles by hand
    (or, for a true re-scope, supersedes + creates instead). See
    `Skill(decide-card)` "Reconcile a re-scope".
    """
    lines = [
        "⚠ This decision reads like a re-scope/reversal of a prior verdict.",
        "  goc decide updated only the ## Decision block and the gate. These "
        "verdict-bearing surfaces are NOT auto-updated — reconcile them so the "
        "card stops contradicting itself:",
    ]
    summary = (t.summary or "").strip()
    if summary:
        flag = " ← still asserts a negative verdict" if NEGATIVE_VERDICT_RE.search(summary) else ""
        snippet = summary if len(summary) <= 100 else summary[:99] + "…"
        lines.append(f"  • summary: {snippet!r}{flag}")
    else:
        lines.append("  • summary: (empty — add one stating the current verdict)")
    if _body_banner_lines(persisted_body):
        lines.append("  • a ⚠/verdict banner in the body still asserts the old verdict")
    lines.append("  • DoD wording that encodes the old verdict")
    neighbors: list[str] = []
    for field in ("advances", "advanced_by"):
        vals = t.frontmatter.get(field) or []
        if isinstance(vals, list):
            neighbors.extend(str(v) for v in vals)
    if neighbors:
        lines.append(
            "  • references to this card in its neighbors are NOT auto-updated: "
            + ", ".join(neighbors)
        )
    lines.append(
        f"  For a true re-scope, prefer: goc status {t.title} superseded --by <new-card> "
        "(records a typed forward link a reader can follow)."
    )
    return "\n".join(lines)


def _cmd_decide(args):
    """Record a decision in the body + log; lower the human gate to `none`.

    On a non-terminal card this is the normal Andon-cord lowering — a
    parked card becomes pullable. On a *terminal* card with a still-raised
    gate it is the **repair** path for the `status: terminal` +
    `human_gate != none` contradiction the validator flags. A cleanly
    closed card always carries `gate: none` (the close-time verbs enforce
    it), so the only terminal cards that get past the "gate already none"
    guard below are the broken ones — older closures that predate the
    gate guard, hand-edits, or `goc migrate` imports — whose dangling gate
    must be cleared for `goc validate` to pass. The card stays closed; the
    decision block documents the resolution for the record axis.
    """
    title = args.title
    decision = args.decision
    reasoning = args.reasoning
    commit = args.commit
    no_commit = args.no_commit
    _validate_commit_flags(commit, no_commit)
    card_dir = DECK_DIR / title
    t = load_card_or_exit(card_dir, title)
    if t.human_gate == "none":
        print(
            f"ERROR: {title}: gate already 'none' (no decision pending)",
            file=sys.stderr,
        )
        sys.exit(2)
    is_terminal = t.status in TERMINAL_STATUSES
    prior_gate = t.human_gate
    now = _utc_now_iso()
    text = (card_dir / "README.md").read_text()
    fm, body = parse_frontmatter(text)
    archived = extract_decision_required_section(body)
    body = replace_or_append_decision(body, decision, reasoning, now)
    text = emit_frontmatter(fm, body=body)
    text = mutate_frontmatter_field(text, "human_gate", "none")
    (card_dir / "README.md").write_text(text)
    log_path = card_dir / "log.md"
    existing = log_path.read_text() if log_path.exists() else ""
    entries = []
    if archived:
        filed = t.created or now
        entries.append(
            f"## {filed}: decision deliberation archived\n\n"
            "Archived from the README's `## Decision required` section by "
            "`goc decide` before it was replaced with the resolved `## Decision` "
            "block — README is the dashboard, log.md is the journal. This "
            "preserves the options and recommendation that produced the "
            "decision below.\n\n"
            f"{archived}\n"
        )
    recorded_note = f"{decision} — {reasoning}. Gate {prior_gate} → none."
    if is_terminal:
        recorded_note += (
            f" (Post-closure gate repair on a {t.status} card — the card "
            f"stays closed; this clears the dangling gate so `goc validate` "
            f"passes.)"
        )
    entries.append(f"## {now}: decision recorded\n\n{recorded_note}\n")
    sep = "\n\n" if existing.strip() else ""
    log_path.write_text(existing.rstrip("\n") + sep + "\n\n".join(entries))
    print(f"{title}: decision recorded; gate {prior_gate} → none")
    if is_terminal:
        print(
            f"Next: gate cleared on a {t.status} card — record-axis repair; "
            f"the card stays closed and `goc validate` now passes."
        )
    else:
        print("Next: gate lowered to none — any agent can now claim this card. goc to see the queue.")
    if RESCOPE_MARKERS_RE.search(decision):
        print(_rescope_reconciliation_notice(t, body), file=sys.stderr)
    commit_policy = _commit_override(commit, no_commit)
    if auto_commit_enabled(commit_policy):
        decision_short = decision[:60] + ("…" if len(decision) > 60 else "")
        if _git_auto_commit([card_dir], f"decide: {title} — {decision_short}"):
            print("  committed")


def _cmd_triage(args):
    """List parked cards (gate ≠ none), grouped by gate, oldest-first."""
    as_json = args.as_json
    worker = args.worker
    all_cards = [t for t in load_all_cards() if t.status == "open" and t.human_gate != "none"]
    if worker:
        needle = worker.lower()
        cards = [t for t in all_cards if needle in _worker_who(t.frontmatter.get("worker")).lower()]
    else:
        cards = all_cards
    today = _utc_today()

    def aged_days(t: Card) -> int:
        try:
            return (today - date.fromisoformat(_date_part(t.created))).days
        except (TypeError, ValueError):
            return 0

    payload = []
    for t in sorted(cards, key=lambda c: c.created or ""):
        section = extract_decision_required_section(t.body)
        payload.append(
            {
                "title": t.title,
                "gate": t.human_gate,
                "contribution": t.contribution,
                "aged_days": aged_days(t),
                "decision_required": section,
                "summary": t.summary,
            }
        )

    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if not payload:
        print("No parked cards (gate ≠ none).")
        return

    by_gate: dict[str, list[dict]] = {}
    for entry in payload:
        by_gate.setdefault(entry["gate"], []).append(entry)

    lines = [f"## Waiting on you (gate ≠ none) — {len(payload)} cards", ""]
    for gate in sorted(by_gate.keys()):
        items = by_gate.get(gate, [])
        if not items:
            continue
        lines.append(f"### {gate} ({len(items)})")
        lines.append("")
        for entry in items:
            lines.append(f"- {entry['title']} · aged {entry['aged_days']}d · contribution:{entry['contribution']}")
            preview = entry["decision_required"]
            if preview:
                for ln in preview.splitlines()[:6]:
                    lines.append(f"  > {ln}" if ln else "  >")
            elif entry["summary"]:
                first = entry["summary"].splitlines()[0][:140]
                lines.append(f"  > {first}")
            lines.append("")
    lines.append("Next: ask your agent \"decisions to make\" (Skill(scan-deck)) to walk each card and record decisions via Skill(decide-card).")
    print("\n".join(lines))


def _cmd_show(args):
    """Print full README.md to stdout, followed by sibling artifact filenames."""
    title = args.title
    card_dir = DECK_DIR / title
    p = card_dir / "README.md"
    if not p.exists():
        print(f"ERROR: {p} not found", file=sys.stderr)
        sys.exit(2)
    text = p.read_text()
    print(text)
    artifacts = sorted(
        f.name for f in card_dir.iterdir()
        if f.is_file() and f.name not in ("README.md", "log.md")
    )
    if artifacts:
        print("## Artifacts")
        print()
        for a in artifacts:
            print(f"- {a}")
    # `show` stays read-everything (the broken card is the one you most want
    # to inspect), but surface parse problems via stderr so the inconsistency
    # with `validate` / `done` becomes visible at the same call site.
    try:
        parse_frontmatter(text)
    except FrontmatterError as exc:
        print(f"WARNING: {title}: {exc}", file=sys.stderr)


def _cmd_migrate(args):
    """Merge legacy deck/ into .game-of-cards/deck/ and remove the stale tree."""
    dry_run = args.dry_run
    auto_yes = args.auto_yes
    canonical = REPO_ROOT / ".game-of-cards" / "deck"
    legacy = REPO_ROOT / "deck"

    if not legacy.exists():
        print("No legacy deck/ found; nothing to migrate.")
        return

    if not canonical.exists():
        print(
            f"ERROR: canonical deck location {canonical} does not exist.\n"
            "Run `goc install` first to set up the canonical deck location.",
            file=sys.stderr,
        )
        sys.exit(1)

    legacy_dirs = {d.name: d for d in legacy.iterdir() if d.is_dir()}
    canonical_dirs = {d.name: d for d in canonical.iterdir() if d.is_dir()}

    conflicts: list[str] = []
    to_copy: list[str] = []
    identical: list[str] = []

    for name in sorted(legacy_dirs):
        if name not in canonical_dirs:
            to_copy.append(name)
            continue
        drifted = False
        for fname in ["README.md", "log.md"]:
            lf = legacy_dirs[name] / fname
            cf = canonical_dirs[name] / fname
            if lf.exists() and cf.exists() and lf.read_text() != cf.read_text():
                conflicts.append(f"  {name}/{fname}: content differs between trees")
                drifted = True
            elif lf.exists() and not cf.exists():
                conflicts.append(f"  {name}/{fname}: exists in legacy but missing in canonical")
                drifted = True
        if not drifted:
            identical.append(name)

    if conflicts:
        print(
            "ERROR: cards with content drift — cannot merge safely:",
            file=sys.stderr,
        )
        for c in conflicts:
            print(c, file=sys.stderr)
        print(
            "\nResolve the drifted cards manually (pick the authoritative version),\n"
            "then re-run `goc migrate`.",
            file=sys.stderr,
        )
        sys.exit(1)

    if to_copy:
        print("Cards to migrate (legacy-only):")
        for name in to_copy:
            print(f"  deck/{name}/  →  .game-of-cards/deck/{name}/")
    if identical:
        print(f"Cards already in canonical tree (identical, will skip): {len(identical)}")

    if not to_copy and not identical:
        print("Legacy deck/ contains no card directories; nothing to migrate.")
        if not dry_run and not _DUAL_TREE_CONFLICT:
            return

    if dry_run:
        # Mirror the real run: it reaches `rmtree(legacy)` whenever
        # `to_copy or identical` passes the confirm gate (or when the
        # legacy tree is empty and falls through). Announce the removal
        # in all of those cases so --dry-run never understates the
        # deletion — in particular the identical-only case.
        if to_copy or identical or not legacy_dirs:
            print(f"Would remove legacy tree: {legacy}")
        print("Dry run — no changes made.")
        return

    if to_copy or identical:
        if not auto_yes:
            if not confirm(f"\nMigrate {len(to_copy)} card(s) and remove legacy deck/?"):
                sys.exit(1)

    for name in to_copy:
        shutil.copytree(str(legacy_dirs[name]), str(canonical / name))
        print(f"  migrated: {name}")

    shutil.rmtree(legacy)
    print(f"\nRemoved legacy tree: {legacy}")
    print("Migration complete. Run `goc validate` to confirm.")
    print("Next: `goc validate` to verify card integrity after migration.")


def _cmd_migrate_list_style(args):
    """Re-emit every card to convert relation-edge lists (advances/advanced_by/supersedes/superseded_by) to block-style."""
    dry_run = args.dry_run
    if not DECK_DIR.exists():
        print(f"ERROR: {DECK_DIR} does not exist", file=sys.stderr)
        sys.exit(1)

    changed: list[str] = []
    for card_dir in sorted(DECK_DIR.iterdir()):
        readme = card_dir / "README.md"
        if not readme.exists():
            continue
        original = readme.read_text()
        try:
            fm, body = parse_frontmatter(original)
        except FrontmatterError as exc:
            print(f"WARNING: {card_dir.name}: {exc}", file=sys.stderr)
            continue
        if not fm:
            continue
        rewritten = emit_frontmatter(fm, body=body)
        if rewritten != original:
            changed.append(card_dir.name)
            if not dry_run:
                readme.write_text(rewritten)

    if not changed:
        print("All cards already use block-style for advances/advanced_by/supersedes/superseded_by — nothing to do.")
        return

    if dry_run:
        print(f"Would rewrite {len(changed)} card(s):")
        for name in changed:
            print(f"  {name}")
        print("Dry run — no changes made.")
    else:
        print(f"Rewrote {len(changed)} card(s):")
        for name in changed:
            print(f"  {name}")
        print("Done. Run `goc validate` to confirm.")


if __name__ == "__main__":
    cli()
