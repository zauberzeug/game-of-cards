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
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import click
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


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML between leading `---` markers; return (data, body).

    Returns ({}, text) if no frontmatter delimiters are present.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    data = yaml.safe_load(m.group(1)) or {}
    return data, m.group(2)


_YAML_RESERVED = {"null", "true", "false", "yes", "no"}
_YAML_NEEDS_QUOTE = re.compile(r"[:#'\"\\\[\]\{\}\,`@]")


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
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if _YAML_NEEDS_QUOTE.search(s) or s in _YAML_RESERVED:
        # Escape \ and " for safe inclusion in "..." YAML scalar.
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


def _emit_block_field(key: str, value: str, *, indicator: str) -> list[str]:
    """Render a multi-line string field with literal-block style (`|` or `|-`)."""
    text = (value or "").rstrip("\n")
    out = [f"{key}: {indicator}"]
    for ln in text.splitlines():
        out.append(f"  {ln}" if ln else "")
    return out


_BLOCK_LIST_FIELDS = frozenset({"advances", "advanced_by"})


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

    `definition_of_done` always uses `|` block style. `advances` and
    `advanced_by` use block-style lists (one `- item` per line) when non-empty;
    empty lists still render as `[]`. `worker` emits as a flat string when only
    `who` is set, or an inline mapping when `where` is also set. Other multi-line
    strings use `|-` block style. Single-line strings are rendered inline.
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
        if isinstance(value, str) and "\n" in value:
            lines.extend(_emit_block_field(key, value, indicator="|-"))
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
    # Match the field header and any subsequent indented block lines.
    pattern = re.compile(
        rf"^{re.escape(field_name)}:[ \t]*[^\n]*(?:\n[ \t]+[^\n]*)*",
        re.MULTILINE,
    )
    if not pattern.search(fm_text):
        # Field absent — append at the end of the frontmatter block.
        fm_text = fm_text.rstrip() + f"\n{field_name}: {new_value}"
    else:
        fm_text = pattern.sub(f"{field_name}: {new_value}", fm_text, count=1)
    return f"---\n{fm_text}\n---\n{body}"


DECISION_REQUIRED_RE = re.compile(
    r"^## Decision required[^\n]*\n(.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)


def extract_decision_required_section(body: str) -> str | None:
    """Return the body of the `## Decision required` section, or None if absent."""
    m = DECISION_REQUIRED_RE.search(body)
    return m.group(1).strip() if m else None


def replace_or_append_decision(body: str, decision: str, reasoning: str, today: str) -> str:
    """Replace `## Decision required` with `## Decision`, or append a new section."""
    block = f"## Decision\n\n*Resolved {today}:* {decision}\n\n*Reasoning:* {reasoning}\n"
    if DECISION_REQUIRED_RE.search(body):
        return DECISION_REQUIRED_RE.sub(block, body, count=1)
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
    canonical_tags: set[str]


def load_schema() -> Schema:
    if not SCHEMA_FILE.exists():
        click.echo(f"FATAL: {SCHEMA_FILE} missing", err=True)
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
            canonical_tags=canonical_tags,
        )
    except KeyError as e:
        click.echo(f"FATAL: schema.yaml missing field {e}", err=True)
        sys.exit(3)


_FENCED_YAML = re.compile(r"```ya?ml\n(.*?)```", re.DOTALL)


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
        out.update(block.get("canonical_tags") or [])
    return out


# ────────────────────────────────────────────────────────────────────────────
# Card model

DOD_OPEN_BOX = re.compile(r"^[ \t]*- \[ \]", re.MULTILINE)
DOD_DONE_BOX = re.compile(r"^[ \t]*- \[x\]", re.MULTILINE | re.IGNORECASE)


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
        return self.frontmatter.get("contribution", "")

    @property
    def human_gate(self) -> str:
        return self.frontmatter.get("human_gate", "")

    @property
    def tags(self) -> list[str]:
        return self.frontmatter.get("tags") or []

    @property
    def created(self) -> str:
        v = self.frontmatter.get("created", "")
        return str(v)

    @property
    def closed_at(self):
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
    return len(DOD_OPEN_BOX.findall(dod_field)), len(DOD_DONE_BOX.findall(dod_field))


def load_card(card_dir: Path) -> Card | None:
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
        t = load_card(sub)
        if t is not None:
            cards.append(t)
    return cards


# ────────────────────────────────────────────────────────────────────────────
# Validate


def _is_iso_date(value) -> bool:
    if not isinstance(value, (str, date)):
        return False
    if isinstance(value, date):
        return True
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", value))


LIST_REL_FIELDS = ("advances", "advanced_by")
INVERSE_REL = {"advances": "advanced_by", "advanced_by": "advances"}


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
        fm, _body = parse_frontmatter(readme.read_text())
        if not fm:
            errors.append(f"{sub.name}: README.md missing frontmatter")
    return errors


def validate_skill_dir_parity() -> list[str]:
    """Flag consumer skill dirs (.claude/skills, .codex/skills) missing skills the
    installed goc templates ship. A drift here means the consumer copies were
    written by an older goc version than the one currently resolving templates;
    the fix is `goc upgrade --keep-local-skills`. Extras (user-added skills) are
    allowed and not reported.
    """
    template_skills = PACKAGE_DIR / "templates" / "skills"
    if not template_skills.exists():
        return []
    expected = {p.name for p in template_skills.iterdir() if (p / "SKILL.md").is_file()}
    errors: list[str] = []
    for relative in (".claude/skills", ".codex/skills"):
        consumer_dir = REPO_ROOT / relative
        if not consumer_dir.exists():
            continue
        actual = {p.name for p in consumer_dir.iterdir() if (p / "SKILL.md").is_file()}
        missing = expected - actual
        if missing:
            errors.append(
                f"{relative}: missing skills {sorted(missing)} that goc templates ship; "
                "run `goc upgrade --keep-local-skills` to resync"
            )
    return errors


def validate_plugin_mirror_parity() -> list[str]:
    """Check that claude-plugin/ mirrors match their source-of-truth trees byte-for-byte.

    Only runs when claude-plugin/ exists at REPO_ROOT (i.e., inside the goc source repo).
    Drift means a source-of-truth file was edited without updating the plugin mirror;
    fix is to copy the changed file(s) into claude-plugin/ and re-run `goc validate`.

    Mirrors the CI step "Verify plugin assets match templates byte-for-byte" so
    contributors catch drift locally before push.
    """
    plugin_root = REPO_ROOT / "claude-plugin"
    if not plugin_root.exists():
        return []

    def _walk(cmp: filecmp.dircmp, src_rel: str, dst_rel: str, prefix: str = "") -> list[str]:
        out: list[str] = []
        out += [f"{prefix}{n} (only in {src_rel})" for n in cmp.left_only]
        out += [f"{prefix}{n} (only in {dst_rel})" for n in cmp.right_only]
        out += [f"{prefix}{n} (differs)" for n in cmp.diff_files]
        for sub_name, sub_cmp in cmp.subdirs.items():
            out += _walk(sub_cmp, src_rel, dst_rel, prefix=prefix + sub_name + "/")
        return out

    pairs = [
        (REPO_ROOT / "goc" / "templates" / "skills", plugin_root / "skills"),
        (
            REPO_ROOT / "goc" / "templates" / "hooks" / "deck_prompt_router.py",
            plugin_root / "hooks" / "deck_prompt_router.py",
        ),
        (
            REPO_ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py",
            plugin_root / "hooks" / "deck_session_start.py",
        ),
        (REPO_ROOT / "goc", plugin_root / "goc"),
    ]
    errors: list[str] = []
    for src, dst in pairs:
        if not src.exists():
            continue
        src_rel = str(src.relative_to(REPO_ROOT))
        dst_rel = str(dst.relative_to(REPO_ROOT))
        if src.is_dir():
            if not dst.exists():
                errors.append(f"plugin mirror: {dst_rel} missing; copy from {src_rel}")
                continue
            diffs = _walk(filecmp.dircmp(src, dst), src_rel, dst_rel)
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
        errors.append(f"{t.title}: created: {fm['created']!r} not ISO YYYY-MM-DD")

    closed_at = fm.get("closed_at")
    if closed_at is not None and not _is_iso_date(closed_at):
        errors.append(f"{t.title}: closed_at: {closed_at!r} not null/ISO date")

    tags = fm.get("tags") or []
    if not isinstance(tags, list):
        errors.append(f"{t.title}: tags: must be a list")
    else:
        for tag in tags:
            if tag not in schema.canonical_tags:
                errors.append(f"{t.title}: tags: unknown tag '{tag}' (not in SCHEMA.md canonical_tags)")

    if fm.get("status") == "done":
        if closed_at is None:
            errors.append(f"{t.title}: closed_at: must be set when status=done")
        if t.dod_open > 0:
            errors.append(f"{t.title}: definition_of_done: status=done with {t.dod_open} unchecked boxes")
    elif closed_at is not None:
        errors.append(
            f"{t.title}: closed_at: must be null when status is not done"
            f" (status={fm.get('status')!r}, closed_at={closed_at!r})"
        )

    worker = fm.get("worker")
    if worker is not None:
        if isinstance(worker, str):
            if not worker:
                errors.append(f"{t.title}: worker: must not be an empty string")
        elif isinstance(worker, dict):
            if "who" not in worker:
                errors.append(f"{t.title}: worker: mapping must have a 'who' key")
            elif not isinstance(worker.get("who"), str) or not worker["who"]:
                errors.append(f"{t.title}: worker: 'who' must be a non-empty string")
            if "where" in worker and not isinstance(worker.get("where"), str):
                errors.append(f"{t.title}: worker: 'where' must be a string")
        else:
            errors.append(f"{t.title}: worker: must be a string or mapping with 'who'")

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

    return errors


def validate_bidirectional_edges(cards: list[Card]) -> list[str]:
    """Enforce that advances↔advanced_by edges are mutually consistent.

    A.advances=[B] requires B.advanced_by to contain A; the inverse must also hold.
    Half-edges are an integrity bug — surface them so they can be repaired.
    """
    errors: list[str] = []
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
                if t.title not in inverse_list:
                    errors.append(
                        f"{t.title}: {field} contains '{ref}' but {ref}.{inverse} is missing '{t.title}' (half-edge)"
                    )
    return errors


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
        for a in card.frontmatter.get("advances") or []:
            if a == advancer:
                return True
            stack.append(a)
    return False


# ────────────────────────────────────────────────────────────────────────────
# Filtering + sorting

STATUS_VALUES = ("open", "active", "blocked", "done", "disproved", "superseded")
STATUS_FILTER_VALUES = (*STATUS_VALUES, "all")
MUTABLE_STATUS_VALUES = tuple(status for status in STATUS_VALUES if status != "done")
CONTRIBUTION_ORDER = {"high": 0, "medium": 1, "low": 2}
STAGE_ORDER = ["null", "alpha", "beta", "stable"]

# GRPW sort: per-card contribution composes through the `advances` graph
# into a `value` score with Bellman discount γ per hop. See
# deck/goc-rename-blocks-to-advances-and-design-value-sort/ for the
# RCPSP literature precedent (Hartmann 1999) and the May 3 design
# discussion. log-spaced ranks are RICE-derived (Intercom): a `high`
# dominates three `medium`s when both reach the same downstream sink.
CONTRIBUTION_RANK: dict[str, float] = {"high": 9.0, "medium": 3.0, "low": 1.0}
GAMMA = 0.7


def compute_values(cards: list[Card]) -> dict[str, tuple[float, list[str]]]:
    """Compute (value, top_path) for each card via memoized DFS.

    `value(c) = rank(c) + γ · max(value(d) for d in advances(c))`

    Additive Bellman: a card's value is its own contribution PLUS the
    geometrically-discounted strongest-descendant chain. Chain depth
    is a curation signal — wiring an edge requires anchoring two card
    bodies, so longer chains reflect more validated value-flow. With
    γ=0.7, value is bounded asymptotically by `max_rank / (1 - γ)`
    (≈ 30 for our rank table), so growth is geometric not unbounded.

    Switched from saturating-max (`max(own, γ·best)`) on 2026-05-03
    after the formula was identified as making native-high cards lose
    chain-distance signal: `γ × 9 = 6.3 < 9` always meant downstream
    chain depth was invisible past the first high. Additive preserves
    chain influence at all ranks (CPM-like, leaf-favoring) which is
    the right kanban-pull semantic.

    `top_path` traces the argmax descendant chain — used by `-v`
    rendering as the WHY column. For a leaf with no descendants,
    `top_path` is `["self"]`.

    Cycles fall back to per-card rank (defense; validator should reject
    cycles via `detect_advance_cycles` but cheap to handle here too).
    Unknown advances targets are silently skipped.
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
        for dest in t.frontmatter.get("advances") or []:
            if dest not in by_title:
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
        out = [t for t in out if advances in (t.frontmatter.get("advances") or [])]
    if advanced_by:
        out = [t for t in out if advanced_by in (t.frontmatter.get("advanced_by") or [])]
    if worker:
        needle = worker.lower()
        out = [t for t in out if needle in _worker_who(t.frontmatter.get("worker")).lower()]
    return out


def parse_stage_filter(stage_flag: str | None) -> list[str] | None:
    if not stage_flag:
        return None
    valid = ", ".join(STAGE_ORDER)
    if "-" in stage_flag:
        a, b = stage_flag.split("-", 1)
        if a not in STAGE_ORDER or b not in STAGE_ORDER:
            raise click.BadParameter(
                f"expected one of {valid}, or a range like alpha-stable",
                param_hint="--stage",
            )
        ai, bi = STAGE_ORDER.index(a), STAGE_ORDER.index(b)
        return STAGE_ORDER[min(ai, bi) : max(ai, bi) + 1]
    if stage_flag not in STAGE_ORDER:
        raise click.BadParameter(
            f"expected one of {valid}, or a range like alpha-stable",
            param_hint="--stage",
        )
    return [stage_flag]


def parse_since_filter(_ctx, _param, value: str | None) -> str | None:
    if value is None:
        return None
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        raise click.BadParameter("expected YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as e:
        raise click.BadParameter("expected YYYY-MM-DD") from e
    return value


def validate_tag_filters(tags: tuple[str, ...]) -> list[str] | None:
    if not tags:
        return None
    schema = load_schema()
    unknown = [tag for tag in tags if tag not in schema.canonical_tags]
    if unknown:
        raise click.BadParameter(f"unknown tag '{unknown[0]}'", param_hint="--tag")
    return list(tags)


def sort_default(cards: list[Card], values: dict[str, tuple[float, list[str]]] | None = None) -> list[Card]:
    """Sort by GRPW-computed value, with ToC-style near-term-flow tiebreak.

    Key tuple: (-value, -direct_advances_count, age_days)
    - primary: highest computed value first (graph-amplified contribution)
    - tiebreak: more direct downstream cards = unblock more flow now
    - final: oldest-created first (kanban WIP-aging discipline)

    `values` should be precomputed on the FULL deck (not the filtered
    subset) so chains through filtered-out cards (e.g. status=blocked
    quality gates) still amplify open cards. If omitted, computed
    locally over `cards` — only correct when `cards` IS the full deck.
    """
    if values is None:
        values = compute_values(cards)

    def key(t: Card):
        v, _ = values.get(t.title, (0.0, []))
        n_direct = len(t.frontmatter.get("advances") or [])
        return (-v, -n_direct, t.created)

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
    parts = []
    for slug in path:
        c = by_title.get(slug)
        contrib = c.contribution if c else "?"
        parts.append(f"→ {slug} ({contrib})")
    return " ".join(parts)


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
        tags = ",".join(t.tags[:4])
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
            w = t.worker
            if w:
                who = w.get("who", "")
                where = w.get("where")
                worker_str = f"worker: {who}"
                if where:
                    worker_str += f" @ {where}"
                out_lines.append(f"    {worker_str}")
        if verbose >= 2:
            for field in ("advances", "advanced_by"):
                v = t.frontmatter.get(field) or []
                if v:
                    out_lines.append(f"    {field}: {list(v)}")
            dod = t.frontmatter.get("definition_of_done", "")
            for line in dod.splitlines():
                out_lines.append(f"    {line.rstrip()}")
    return "\n".join(out_lines)


def render_json(cards: list[Card], values: dict[str, tuple[float, list[str]]] | None = None) -> str:
    if values is None:
        values = compute_values(cards)
    return json.dumps(
        [
            {
                "title": t.title,
                "summary": t.summary,
                "status": t.status,
                "stage": t.stage,
                "contribution": t.contribution,
                "value": values.get(t.title, (0.0, []))[0],
                "value_path": values.get(t.title, (0.0, []))[1],
                "human_gate": t.human_gate,
                "tags": t.tags,
                "created": t.created,
                "closed_at": str(t.closed_at) if t.closed_at else None,
                "advances": t.frontmatter.get("advances") or [],
                "advanced_by": t.frontmatter.get("advanced_by") or [],
                "worker": t.worker,
                "dod_open": t.dod_open,
                "dod_done": t.dod_done,
                "dod_freeform": t.dod_freeform,
            }
            for t in cards
        ],
        indent=2,
        default=str,
    )


def render_board(
    cards: list[Card],
    *,
    max_rows: int,
    no_color: bool,
    values: dict[str, tuple[float, list[str]]] | None = None,
) -> str:
    if values is None:
        values = compute_values(cards)
    columns = ["open", "active", "blocked", "done", "disproved", "superseded"]
    by_status: dict[str, list[Card]] = {c: [] for c in columns}
    for t in cards:
        if t.status in by_status:
            by_status[t.status].append(t)
    for c in columns:
        by_status[c] = sort_default(by_status[c], values=values)[:max_rows]
    col_w = max(20, (120 - 4 * (len(columns) - 1)) // len(columns))
    rows = max((len(by_status[c]) for c in columns), default=0)
    enabled = _color_enabled(no_color)
    out: list[str] = []
    header = " | ".join(_wrap(c.upper().ljust(col_w), c, enabled) for c in columns)
    out.append(header)
    out.append("-+-".join("-" * col_w for _ in columns))
    for i in range(rows):
        cells = []
        for c in columns:
            if i < len(by_status[c]):
                t = by_status[c][i]
                who = _worker_who(t.frontmatter.get("worker"))
                if who:
                    suffix = f" [{t.contribution[0]}] @{who[:8]}"
                    cell = f"{t.title[: col_w - len(suffix)].rstrip()}{suffix}"
                else:
                    cell = f"{t.title[: col_w - 3]} [{t.contribution[0]}]"
            else:
                cell = ""
            cells.append(cell.ljust(col_w))
        out.append(" | ".join(cells))
    return "\n".join(out)


def render_active_notice(
    cards: list[Card],
    *,
    values: dict[str, tuple[float, list[str]]] | None = None,
) -> str:
    """Warn open-queue readers about claimed cards outside the open filter."""

    if values is None:
        values = compute_values(cards)
    active = sort_default([t for t in cards if t.status == "active"], values=values)
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
# Click app


@click.group(invoke_without_command=True)
@click.option("--tag", "tags", multiple=True, help="Filter by tag (repeatable; AND).")
@click.option("--contribution", type=click.Choice(["high", "medium", "low"]))
@click.option(
    "--status",
    "status_flag",
    type=click.Choice(STATUS_FILTER_VALUES),
    default=None,
    help="One status, or 'all'. Default: open.",
)
@click.option("--stage", "stage_flag", default=None, help="Stage filter; supports range like 'alpha-beta'.")
@click.option("--human-gate", type=click.Choice(["none", "decision", "session"]))
@click.option("--done", "done_flag", is_flag=True, help="Shortcut for --status done.")
@click.option("--since", default=None, callback=parse_since_filter, help="With --done: filter on closed_at >= YYYY-MM-DD.")
@click.option("--advances", default=None, help="Filter to cards that advance this title.")
@click.option("--advanced-by", default=None, help="Filter to cards advanced by this title.")
@click.option(
    "--worker",
    default=None,
    envvar="GOC_WORKER",
    help="Filter by worker.who (substring match). Also read from GOC_WORKER env var.",
)
@click.option(
    "-v",
    "verbose",
    count=True,
    help="-v adds STAGE/CREATED columns + summary line; -vv inlines DoD checklist + cross-refs.",
)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON.")
@click.option("--no-color", is_flag=True)
@click.option("--board", is_flag=True, help="ASCII multi-column kanban board.")
@click.option("--max-rows", type=click.IntRange(min=0), default=20, help="Cap rows per column in --board.")
@click.pass_context
def cli(
    ctx,
    tags,
    contribution,
    status_flag,
    stage_flag,
    human_gate,
    done_flag,
    since,
    advances,
    advanced_by,
    worker,
    verbose,
    as_json,
    no_color,
    board,
    max_rows,
):
    if _DUAL_TREE_CONFLICT and ctx.invoked_subcommand != "migrate":
        _canonical = DECK_ROOT / ".game-of-cards" / "deck"
        _legacy = DECK_ROOT / "deck"
        click.echo(
            f"ERROR: two deck trees found — cannot operate safely:\n"
            f"  canonical: {_canonical}\n"
            f"  legacy:    {_legacy}\n"
            f"\nRun `goc migrate` to merge legacy → canonical and remove the stale tree.",
            err=True,
        )
        sys.exit(1)
    if _LEGACY_ONLY and ctx.invoked_subcommand not in ("migrate", "install", "upgrade"):
        click.echo(
            "WARNING: using legacy deck/ location. Run `goc upgrade` to migrate to .game-of-cards/deck/.",
            err=True,
        )
    if ctx.invoked_subcommand is not None:
        return
    cards = load_all_cards()
    if done_flag and status_flag is not None:
        raise click.UsageError("pass only one of --done / --status")
    if done_flag:
        status = "done"
    elif status_flag is None:
        status = "open"
    else:
        status = status_flag
    status_filter_explicit = bool(done_flag or status_flag is not None)
    if since and status != "done":
        raise click.UsageError("--since requires --done (or --status done)")
    stages = parse_stage_filter(stage_flag)
    tag_filters = validate_tag_filters(tags)
    filtered = filter_cards(
        cards,
        status=status,
        stages=stages,
        contribution=contribution,
        human_gate=human_gate,
        tags=tag_filters,
        since=since,
        advances=advances,
        advanced_by=advanced_by,
        worker=worker,
    )
    full_values = compute_values(cards)
    full_by_title = {t.title: t for t in cards}
    filtered = sort_default(filtered, values=full_values)
    if board:
        board_cards = filtered if (status_filter_explicit or worker) else cards
        click.echo(
            render_board(
                board_cards, max_rows=max_rows, no_color=no_color, values=full_values
            )
        )
    elif as_json:
        click.echo(render_json(filtered, values=full_values))
    else:
        out = render_table(filtered, verbose=verbose, no_color=no_color, values=full_values, by_title=full_by_title)
        active_notice = render_active_notice(cards, values=full_values) if status == "open" else ""
        lines = [part for part in (active_notice, out) if part]
        if lines:
            click.echo("\n".join(lines))


@cli.command()
@click.option("--quiet", is_flag=True, help="Only print errors; suppress per-todo OK lines.")
def validate(quiet):
    """Walk all cards, parse YAML, check schema conformance. Exit 1 on violations."""
    schema = load_schema()
    cards = load_all_cards()
    all_titles = {t.title for t in cards}
    errors: list[str] = []
    for e in validate_deck_directories():
        click.echo(f"ERROR: {e}", err=True)
        errors.append(e)
    for e in validate_skill_dir_parity():
        click.echo(f"ERROR: {e}", err=True)
        errors.append(e)
    for e in validate_plugin_mirror_parity():
        click.echo(f"ERROR: {e}", err=True)
        errors.append(e)
    for t in cards:
        per = validate_card(t, schema, all_titles)
        errors.extend(per)
        if not per and not quiet:
            click.echo(f"OK  {t.title}")
        else:
            for e in per:
                click.echo(f"ERROR: {e}", err=True)
    for checker in (detect_advance_cycles, validate_bidirectional_edges):
        for e in checker(cards):
            click.echo(f"ERROR: {e}", err=True)
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
    click.echo(f"\n=== {title} ===")
    tv = verdict.get("title_verdict") or {}
    if tv.get("ok"):
        click.echo("title:   OK")
    else:
        has_rewrite = True
        click.echo(f"title:   REWRITE — {tv.get('reason', '?')}")
        click.echo(f"  proposed: {tv.get('rewrite', '?')}")
    sv = verdict.get("summary_verdict") or {}
    if sv.get("ok"):
        click.echo("summary: OK")
    else:
        has_rewrite = True
        click.echo(f"summary: REWRITE — {sv.get('reason', '?')}")
        click.echo(f"  proposed: {sv.get('rewrite', '?')}")
    dod_issues = verdict.get("dod_issues") or []
    if dod_issues:
        has_rewrite = True
        click.echo(f"dod:     {len(dod_issues)} issue(s)")
        for issue in dod_issues:
            click.echo(f"  [{issue.get('idx', '?')}] {issue.get('issue', '?')}")
            click.echo(f"      fix: {issue.get('fix', '?')}")
    else:
        click.echo("dod:     OK")
    return has_rewrite


def _apply_summary_rewrite(card: Card, new_summary: str) -> None:
    """In-place YAML-safe rewrite of the `summary:` field on this card's README.md."""
    readme = card.path / "README.md"
    text = readme.read_text()
    rewritten = mutate_frontmatter_field(text, "summary", _yaml_inline(new_summary))
    readme.write_text(rewritten)


def _apply_dod_rewrite(card: Card, issues: list[dict]) -> None:
    """Replace specific DoD items by 0-based index. Other items preserved verbatim."""
    readme = card.path / "README.md"
    text = readme.read_text()
    fm, body = parse_frontmatter(text)
    dod_text = fm.get("definition_of_done") or ""
    lines = dod_text.splitlines()
    box_indices = [i for i, ln in enumerate(lines) if re.match(r"^\s*- \[[ x]\]", ln)]
    fix_by_idx = {issue["idx"]: issue["fix"] for issue in issues if "idx" in issue and "fix" in issue}
    for box_idx, line_idx in enumerate(box_indices):
        if box_idx in fix_by_idx:
            new_text = fix_by_idx[box_idx]
            new_text = new_text.lstrip()
            if not new_text.startswith("- ["):
                new_text = f"- [ ] {new_text}"
            lines[line_idx] = new_text
    fm["definition_of_done"] = "\n".join(lines) + ("\n" if not dod_text.endswith("\n") else "")
    readme.write_text(emit_frontmatter(fm, body=body))


def _apply_verdict_interactive(card: Card, verdict: dict, *, auto_yes: bool = False) -> dict:
    """Walk a verdict, prompting accept/reject per dimension. Returns counts of applied edits."""
    applied = {"title": False, "summary": False, "dod": 0}

    def ask(prompt: str) -> bool:
        if auto_yes:
            return True
        return click.confirm(prompt, default=False)

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
                click.echo(f"    moved → {tv['rewrite']}")
            else:
                click.echo(f"    move failed: {r.stderr.strip()}", err=True)

    sv = verdict.get("summary_verdict") or {}
    if not sv.get("ok") and sv.get("rewrite"):
        if ask("  apply summary rewrite?"):
            target_card = card
            if applied["title"]:
                target_card = load_card(DECK_DIR / tv["rewrite"]) or card
            _apply_summary_rewrite(target_card, sv["rewrite"])
            applied["summary"] = True
            click.echo("    summary rewritten")

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
        click.echo(f"    DoD: {len(accepted_issues)} item(s) rewritten")

    return applied


@cli.command("quality-pass")
@click.option(
    "--status",
    "status_flag",
    type=click.Choice(STATUS_FILTER_VALUES),
    default="open",
    help="Filter by status (default: open).",
)
@click.option("--llm/--no-llm", default=False, help="Also run a Sonnet-batched summary+DoD audit (cost ~$0.40/pass).")
@click.option("--limit", type=int, default=None, help="With --llm: cap card count (testing/sampling).")
@click.option("--dry-run", is_flag=True, help="With --llm: print verdicts; skip the interactive accept/reject walk.")
@click.option("--yes", "auto_yes", is_flag=True, help="With --llm: auto-accept every proposed rewrite (use with care).")
def quality_pass(status_flag, llm, limit, dry_run, auto_yes):
    """Surface engineer-jargon titles + missing summaries across the existing deck.

    Layer 1 (always-on): regex check against TITLE_ANTIPATTERNS — same predicates
    that `deck.py new` rejects at filing time. Catches legacy cards filed before
    the antipattern guard was wired.

    Layer 2 (--llm): batched call to `claude --bare --model sonnet -p ...` over a
    slim cards JSON dump (title + summary + definition_of_done). The LLM returns
    per-card verdicts on all three dimensions; a triage walk prompts accept/reject
    per dimension and applies via `deck.py move` (titles) or in-place YAML edits
    (summary, DoD items). Cost: ~$0.40 per ~120-card pass.
    """
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

    click.echo(f"\nQuality pass over {len(cards)} cards (status={status_flag}):\n")

    if title_hits:
        click.echo(f"Title antipatterns ({len(title_hits)} cards):")
        for title, reasons in title_hits:
            click.echo(f"  - {title}")
            for r in reasons:
                click.echo(f"      → {r}")
        click.echo("")
    else:
        click.echo("Title antipatterns: clean.\n")

    if missing_summary:
        click.echo(f"Missing summary ({len(missing_summary)} cards):")
        for title in missing_summary[:20]:
            click.echo(f"  - {title}")
        if len(missing_summary) > 20:
            click.echo(f"  ... and {len(missing_summary) - 20} more")
        click.echo("")
    else:
        click.echo("Missing summary: clean.\n")

    if not llm:
        return

    sample = cards if limit is None else cards[:limit]
    click.echo(f"Layer-2 (Sonnet pass): auditing {len(sample)} cards via `claude --model sonnet -p`…")
    prompt = _build_quality_prompt(sample)
    try:
        verdicts = _run_sonnet_quality_pass(prompt)
    except subprocess.CalledProcessError as e:
        click.echo(f"ERROR: claude CLI failed (exit {e.returncode}): {e.stderr[:500] or e.stdout[:500]}", err=True)
        sys.exit(1)
    except (ValueError, json.JSONDecodeError, RuntimeError) as e:
        click.echo(f"ERROR: could not parse Sonnet response: {e}", err=True)
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
                    click.echo("    (card not found in sample; skipping apply)", err=True)
                    continue
                applied = _apply_verdict_interactive(card, verdict, auto_yes=auto_yes)
                applied_count["title"] += int(applied["title"])
                applied_count["summary"] += int(applied["summary"])
                applied_count["dod"] += applied["dod"]

    click.echo(f"\nSonnet pass: {len(verdicts)} cards audited, {rewrite_count} with proposed rewrites.")
    if not dry_run:
        click.echo(
            f"Applied: {applied_count['title']} titles, {applied_count['summary']} summaries, {applied_count['dod']} DoD items."
        )


@cli.command()
@click.argument("title")
@click.option("--force", is_flag=True, help="Bypass DoD enforcement (free-form prose DoDs).")
def done(title, force):
    """Flip status → done; set closed_at; enforce DoD-checkbox rule."""
    card_dir = DECK_DIR / title
    t = load_card(card_dir)
    if t is None:
        click.echo(f"ERROR: {title}: not found at {card_dir}", err=True)
        sys.exit(2)
    if t.dod_freeform and not force:
        click.echo(f"ERROR: {title}: free-form DoD; use --force to bypass enforcement", err=True)
        sys.exit(2)
    if t.dod_open > 0:
        click.echo(f"ERROR: {title}: {t.dod_open} unchecked DoD boxes; will not mark done", err=True)
        sys.exit(2)
    prior = t.status
    if prior == "done":
        click.echo(f"{title}: already done; closed_at unchanged")
        return
    _TERMINAL_NON_DONE = frozenset({"disproved", "superseded"})
    if prior in _TERMINAL_NON_DONE:
        click.echo(
            f"ERROR: {title}: status is {prior!r} (terminal); "
            f"use the supersede/disprove workflow — 'done' cannot overwrite terminal states",
            err=True,
        )
        sys.exit(2)
    today = date.today().isoformat()
    text = (card_dir / "README.md").read_text()
    text = mutate_frontmatter_field(text, "status", "done")
    text = mutate_frontmatter_field(text, "closed_at", today)
    (card_dir / "README.md").write_text(text)
    click.echo(f"{title}: {prior} → done")
    click.echo("Next: goc to see what's open, or ask your agent to \"drain the queue\" (pull-card).")


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
        if any((git_dir / sf).exists() for sf in ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD")):
            click.echo("  (auto-commit skipped: merge/rebase/cherry-pick in progress)", err=True)
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
        subprocess.run(["git", "commit", "-m", message], check=True, cwd=git_cwd)
        return True
    except subprocess.CalledProcessError as e:
        click.echo(f"  (auto-commit failed: {e})", err=True)
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


def _commit_override(commit: bool, no_commit: bool) -> bool | None:
    if commit and no_commit:
        click.echo("ERROR: pass only one of --commit / --no-commit", err=True)
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
        click.echo(
            "  Warning: auto_commit is disabled but the deck is version-controlled."
            " Parallel agents will not see claim/progress state until you commit manually.",
            err=True,
        )
    return enabled


# ────────────────────────────────────────────────────────────────────────────
# Closure attestation — runs layer-2 (project) + layer-3 (GoC) DoD checks
# defined in .game-of-cards/config.yaml and records the result in log.md.


def load_deck_config() -> dict:
    if GAME_OF_CARDS_CONFIG_FILE.exists():
        return yaml.safe_load(GAME_OF_CARDS_CONFIG_FILE.read_text()) or {}
    if LEGACY_DECK_CONFIG_FILE.exists():
        return yaml.safe_load(LEGACY_DECK_CONFIG_FILE.read_text()) or {}
    return {"layer_2_project_dod": [], "layer_3_goc_dod": []}


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
        if not advanced_by:
            return True, "no advanced_by edges"
        by_title = {c.title: c for c in all_cards}
        unclosed = [t for t in advanced_by if t in by_title and by_title[t].status != "done"]
        if unclosed:
            return False, f"{len(unclosed)} not done: {', '.join(unclosed[:3])}"
        return True, f"all {len(advanced_by)} done"
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
        marker = f"## {today} — Closure"
        if marker in log_path.read_text():
            return True, f"'{marker}' present"
        return False, f"no '{marker}' section"
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


@cli.command()
@click.argument("title")
@click.option("--skip", "skips", multiple=True, help="Skip a check by name; recorded as SKIPPED in log.")
@click.option("--non-interactive", is_flag=True, help="Fail manual/agent checks instead of prompting.")
def attest(title, skips, non_interactive):
    """Run layer-2 + layer-3 closure checks; append "Closure verification" block to log.md."""
    card_dir = DECK_DIR / title
    card = load_card(card_dir)
    if card is None:
        click.echo(f"ERROR: {title}: not found at {card_dir}", err=True)
        sys.exit(2)
    config = load_deck_config()
    all_cards = load_all_cards()
    today = date.today().isoformat()
    skips_set = set(skips)
    results: list[dict] = []
    any_failed = False

    for layer_key, layer_num in [("layer_2_project_dod", 2), ("layer_3_goc_dod", 3)]:
        layer_checks = config.get(layer_key) or []
        if not layer_checks:
            continue
        click.echo(f"\nLayer-{layer_num} ({'project' if layer_num == 2 else 'GoC'}) checks:")
        for check in layer_checks:
            name = check["name"]
            if name in skips_set:
                results.append(
                    {
                        "layer": layer_num,
                        "name": name,
                        "passed": True,
                        "skipped": True,
                        "summary": f"SKIPPED ({check.get('description', '')[:60]})",
                    }
                )
                click.echo(f"  [~] {name} — SKIPPED")
                continue
            kind = check["kind"]
            try:
                if kind == "automated":
                    click.echo(f"  ... running {name}")
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
                click.echo(f"\nABORTED on {name}", err=True)
                sys.exit(130)
            results.append({"layer": layer_num, "name": name, "passed": passed, "summary": summary})
            mark = "[x]" if passed else "[ ]"
            click.echo(f"  {mark} {name} — {summary}")
            if not passed:
                any_failed = True

    log_path = card_dir / "log.md"
    block = _format_attestation_block(today, results)
    existing = log_path.read_text() if log_path.exists() else ""
    log_path.write_text((existing.rstrip() + "\n\n" + block) if existing.strip() else block)
    click.echo(f"\nWrote attestation to {log_path}")

    if any_failed:
        click.echo("\nERROR: attestation has failures; finish-card will block closure.", err=True)
        sys.exit(2)
    click.echo("\nAttestation OK.")
    click.echo(f"Next: goc done {title} to close once all DoD items are ticked.")


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

    if not who and not where:
        return text

    # Build the YAML inline value and mutate the frontmatter line-anchored.
    who_yaml = _yaml_inline(who) if who else '""'
    if where:
        where_yaml = _yaml_inline(where)
        worker_yaml = f"{{who: {who_yaml}, where: {where_yaml}}}"
    else:
        worker_yaml = who_yaml
    return mutate_frontmatter_field(text, "worker", worker_yaml)


@cli.command()
@click.argument("title")
@click.argument("new_status", type=click.Choice(MUTABLE_STATUS_VALUES))
@click.option("--commit", is_flag=True, help="Force auto-commit for this status flip.")
@click.option("--no-commit", is_flag=True, help="Skip auto-commit for this status flip.")
@click.option("--worker-who", default=None, help="Override worker.who identity (person, machine, or capability tag).")
@click.option("--worker-where", default=None, help="Override worker.where branch or path for this claim.")
def status(title, new_status, commit, no_commit, worker_who, worker_where):
    """Mutate any status except `done` (which has its own enforcement gate).

    The state flip follows `.game-of-cards/config.yaml` `workflow.auto_commit`.
    `--commit` and `--no-commit` override that policy for one invocation.
    When flipping to `active`, auto-populates `worker.who` from `git config
    user.name` and `worker.where` from the current branch unless already set.
    """
    card_dir = DECK_DIR / title
    t = load_card(card_dir)
    if t is None:
        click.echo(f"ERROR: {title}: not found", err=True)
        sys.exit(2)
    prior = t.status
    if prior == new_status:
        if new_status == "active":
            click.echo(
                f"WARNING: {title}: already active — possible racing claim;"
                f" check `goc --status active` before proceeding",
                err=True,
            )
        else:
            click.echo(f"{title}: already {new_status}; nothing to do")
        return
    _TERMINAL = frozenset({"done", "disproved", "superseded"})
    if prior in _TERMINAL:
        click.echo(
            f"ERROR: {title}: status is {prior!r} (terminal);"
            f" terminal cards cannot be moved backward through `goc status`",
            err=True,
        )
        sys.exit(2)
    text = (card_dir / "README.md").read_text()
    text = mutate_frontmatter_field(text, "status", new_status)
    if new_status == "active":
        text = _auto_populate_worker(text, t, worker_who, worker_where)
    (card_dir / "README.md").write_text(text)
    click.echo(f"{title}: {prior} → {new_status}")
    if new_status == "active":
        click.echo(f"Next: implement the card; tick DoD items as you go; then goc done {title}.")
    commit_policy = _commit_override(commit, no_commit)
    if auto_commit_enabled(commit_policy):
        if _git_auto_commit([card_dir], f"deck: {title} {prior} → {new_status}"):
            click.echo("  committed")


TITLE_ANTIPATTERNS = [
    (re.compile(r"\br\d+\b"), "internal investigation-round reference (rN); describe the *observable problem* instead"),
    (re.compile(r"\bpath-\d+\b"), "sub-investigation step number; promote to a noun-phrase deliverable"),
    (re.compile(r"\bphase-\d+\b"), "internal sequence reference; name the deliverable instead"),
    (re.compile(r"\bbug-\d+\b"), "bug-tracker numbering; use the defect-shape clause"),
    (re.compile(r"_md_|_py_"), "source-file infix; describe the *concept*, not the file"),
    (re.compile(r"[a-z][A-Z]"), "camelCase token; lower-kebab the intent"),
]


def _check_title_antipatterns(title: str) -> list[str]:
    """Return list of (matched_substring, reason) tuples; empty if title is clean."""
    return [reason for pat, reason in TITLE_ANTIPATTERNS if pat.search(title)]


@cli.command()
@click.argument("title")
@click.option("--contribution", type=click.Choice(["high", "medium", "low"]), default="medium")
@click.option("--gate", type=click.Choice(["none", "decision", "session"]), default="decision")
@click.option("--tag", "tags", multiple=True)
@click.option("--worker", default=None, help="Worker designation — person, machine, or capability tag.")
@click.option(
    "--allow-jargon", is_flag=True, help="Bypass the title-antipattern check (rare; used by migration tools)."
)
def new(title, contribution, gate, tags, worker, allow_jargon):
    """Scaffold a new card dir with valid frontmatter and empty log.md."""
    schema = load_schema()
    if not allow_jargon:
        antipatterns_hit = _check_title_antipatterns(title)
        if antipatterns_hit:
            click.echo(f"ERROR: title {title!r} contains engineer-jargon antipattern(s):", err=True)
            for reason in antipatterns_hit:
                click.echo(f"  - {reason}", err=True)
            click.echo(
                "\n  Titles are kanban labels; a non-engineer must understand the card from the title alone.", err=True
            )
            click.echo("  Rephrase to describe the *observable problem* (e.g.", err=True)
            click.echo("    `r88-csubstrate-replication` → `pong-cannot-recover-prior-task-performance`).", err=True)
            click.echo("  Pass --allow-jargon to bypass (rare; for migration tools).", err=True)
            sys.exit(2)
    if not re.match(schema.title_pattern, title):
        click.echo(f"ERROR: title {title!r} does not match {schema.title_pattern!r}", err=True)
        sys.exit(2)
    card_dir = DECK_DIR / title
    if card_dir.exists():
        click.echo(f"ERROR: {card_dir} already exists", err=True)
        sys.exit(2)
    for tag in tags:
        if tag not in schema.canonical_tags:
            click.echo(f"ERROR: unknown tag '{tag}' (not in SCHEMA.md canonical_tags)", err=True)
            sys.exit(2)
    card_dir.mkdir(parents=True)
    today = date.today().isoformat()
    fm = {
        "title": title,
        "summary": "",
        "status": "open",
        "stage": None,
        "contribution": contribution,
        "created": today,
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
    click.echo(f"created {card_dir.relative_to(REPO_ROOT)}/")
    click.echo(f"Next: edit deck/{title}/README.md to fill the body and DoD; then ask your agent to implement the card.")


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
    if not (child_dir / "README.md").exists():
        click.echo(f"ERROR: {child_title}: not found", err=True)
        sys.exit(2)
    if not (parent_dir / "README.md").exists():
        click.echo(f"ERROR: {parent_title}: not found", err=True)
        sys.exit(2)
    op = _add_to_list_field if add else _remove_from_list_field
    child_text = (child_dir / "README.md").read_text()
    parent_text = (parent_dir / "README.md").read_text()
    (child_dir / "README.md").write_text(op(child_text, field_on_child, parent_title))
    (parent_dir / "README.md").write_text(op(parent_text, field_on_parent, child_title))


@cli.command()
@click.argument("title")
@click.option("--by", "advancer", required=True, help="Slug of the card that advances <title>.")
@click.option("--commit", is_flag=True, help="Force auto-commit for this edge mutation.")
@click.option("--no-commit", is_flag=True, help="Skip auto-commit for this edge mutation.")
def advance(title, advancer, commit, no_commit):
    """Add bidirectional value-flow edge: title.advanced_by += advancer, advancer.advances += title."""
    if title == advancer:
        click.echo("ERROR: cannot advance a card with itself", err=True)
        sys.exit(2)
    cards = load_all_cards()
    if _would_create_advance_cycle(cards, title, advancer):
        click.echo(f"ERROR: adding {advancer} → {title} would create a cycle in the advances graph", err=True)
        sys.exit(2)
    _mutate_pair(title, advancer, "advanced_by", "advances", add=True)
    click.echo(f"advance: {title}.advanced_by += {advancer}; {advancer}.advances += {title}")
    commit_policy = _commit_override(commit, no_commit)
    if auto_commit_enabled(commit_policy):
        if _git_auto_commit([DECK_DIR / title, DECK_DIR / advancer], f"deck: {advancer} advances {title}"):
            click.echo("  committed")


@cli.command()
@click.argument("title")
@click.option("--by", "advancer", required=True)
@click.option("--commit", is_flag=True, help="Force auto-commit for this edge mutation.")
@click.option("--no-commit", is_flag=True, help="Skip auto-commit for this edge mutation.")
def unadvance(title, advancer, commit, no_commit):
    """Remove bidirectional value-flow edge."""
    _mutate_pair(title, advancer, "advanced_by", "advances", add=False)
    click.echo(f"unadvance: {title}.advanced_by -= {advancer}; {advancer}.advances -= {title}")
    commit_policy = _commit_override(commit, no_commit)
    if auto_commit_enabled(commit_policy):
        if _git_auto_commit([DECK_DIR / title, DECK_DIR / advancer], f"deck: {advancer} no longer advances {title}"):
            click.echo("  committed")


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
    """Yield (Path, str) for tracked text files; falls back to rglob outside git."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=str(REPO_ROOT), capture_output=True, check=True, timeout=30,
        )
        paths = [
            REPO_ROOT / entry.decode("utf-8", errors="replace")
            for entry in result.stdout.split(b"\x00")
            if entry
        ]
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


@cli.command()
@click.argument("old_title")
@click.argument("new_title")
@click.option(
    "--allow-jargon", is_flag=True, help="Bypass the title-antipattern check (rare; used by migration tools)."
)
@click.option("--dry-run", is_flag=True, help="Print sites that would be rewritten without making changes.")
def move(old_title, new_title, allow_jargon, dry_run):
    """Rename a title and rewrite known cross-references.

    Rewrites references in tracked text files (via ``git ls-files``):

    \b
    - ``# {old}`` H1 headings
    - ``[{old}](../{old}/)`` markdown cross-link form
    - ``deck/{old}/`` and ``.game-of-cards/deck/{old}/`` path forms
    - bare slug with slug-boundary anchoring (not preceded/followed by ``[-\\w]``)

    Appends a dated rename entry to the moved card's log.md.
    Outside-repo references (commit messages, GitHub PRs, external docs) are out of scope.
    """
    schema = load_schema()
    if not allow_jargon:
        antipatterns_hit = _check_title_antipatterns(new_title)
        if antipatterns_hit:
            click.echo(f"ERROR: title {new_title!r} contains engineer-jargon antipattern(s):", err=True)
            for reason in antipatterns_hit:
                click.echo(f"  - {reason}", err=True)
            click.echo(
                "\n  Titles are kanban labels; a non-engineer must understand the card from the title alone.", err=True
            )
            click.echo("  Rephrase to describe the *observable problem* (e.g.", err=True)
            click.echo("    `r88-csubstrate-replication` → `pong-cannot-recover-prior-task-performance`).", err=True)
            click.echo("  Pass --allow-jargon to bypass (rare; for migration tools).", err=True)
            sys.exit(2)
    if not re.match(schema.title_pattern, new_title):
        click.echo(f"ERROR: title {new_title!r} does not match {schema.title_pattern!r}", err=True)
        sys.exit(2)
    src = DECK_DIR / old_title
    dst = DECK_DIR / new_title
    if not src.exists():
        click.echo(f"ERROR: {src} does not exist", err=True)
        sys.exit(2)
    if dst.exists():
        click.echo(f"ERROR: {dst} already exists", err=True)
        sys.exit(2)

    if dry_run:
        sites = _move_preview_sites(old_title, new_title)
        if sites:
            for site in sites:
                click.echo(site)
        else:
            click.echo("(no tracked text files would be modified)")
        click.echo(f"(directory move: {src} → {dst})")
        return

    try:
        subprocess.run(["git", "mv", str(src), str(dst)], cwd=REPO_ROOT, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        shutil.move(str(src), str(dst))

    # Repo-wide text rewrite: H1s, markdown links, path forms, bare slugs,
    # frontmatter title/advances/advanced_by fields.
    _move_rewrite_tracked_files(old_title, new_title)

    # Dated rename log entry.
    today = date.today().isoformat()
    log_path = dst / "log.md"
    existing = log_path.read_text() if log_path.exists() else ""
    sep = "\n\n" if existing.strip() else ""
    log_path.write_text(existing.rstrip("\n") + sep + f"## {today}: renamed from {old_title}\n")

    click.echo(f"{old_title} → {new_title}")


@cli.command()
@click.argument("title")
@click.option("--decision", required=True, help="One-line decision (the WHAT).")
@click.option("--because", "reasoning", required=True, help="One-line reasoning (the WHY).")
@click.option("--commit", is_flag=True, help="Force auto-commit for this decision record.")
@click.option("--no-commit", is_flag=True, help="Skip auto-commit for this decision record.")
def decide(title, decision, reasoning, commit, no_commit):
    """Record a decision in the body + log; lower the human gate to `none`.

    The Andon-cord lowering action: pull-card raises the gate when it can't
    decide; this command captures the human's resolution (what + why) and
    re-enables autonomous claiming. Status is unchanged (stays `open`); the
    next pull-card claims and implements per the recorded decision.
    """
    card_dir = DECK_DIR / title
    t = load_card(card_dir)
    if t is None:
        click.echo(f"ERROR: {title}: not found", err=True)
        sys.exit(2)
    if t.human_gate == "none":
        click.echo(
            f"ERROR: {title}: gate already 'none' (no decision pending)",
            err=True,
        )
        sys.exit(2)
    prior_gate = t.human_gate
    today = date.today().isoformat()
    text = (card_dir / "README.md").read_text()
    fm, body = parse_frontmatter(text)
    body = replace_or_append_decision(body, decision, reasoning, today)
    text = emit_frontmatter(fm, body=body)
    text = mutate_frontmatter_field(text, "human_gate", "none")
    (card_dir / "README.md").write_text(text)
    log_path = card_dir / "log.md"
    existing = log_path.read_text() if log_path.exists() else ""
    sep = "\n\n" if existing.strip() else ""
    log_path.write_text(
        existing.rstrip("\n")
        + sep
        + f"## {today}: decision recorded\n\n"
        + f"{decision} — {reasoning}. Gate {prior_gate} → none.\n"
    )
    click.echo(f"{title}: decision recorded; gate {prior_gate} → none")
    click.echo("Next: gate lowered to none — any agent can now claim this card. goc to see the queue.")
    commit_policy = _commit_override(commit, no_commit)
    if auto_commit_enabled(commit_policy):
        decision_short = decision[:60] + ("…" if len(decision) > 60 else "")
        if _git_auto_commit([card_dir], f"decide: {title} — {decision_short}"):
            click.echo("  committed")


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Emit JSON for Q&A consumers.")
@click.option(
    "--worker",
    default=None,
    envvar="GOC_WORKER",
    help="Filter parked cards by worker.who (substring match). Also read from GOC_WORKER env var.",
)
def triage(as_json, worker):
    """List parked cards (gate ≠ none), grouped by gate, oldest-first.

    The supportive default for `Skill(scan-deck)` when the user asks
    "what's up?" / "where do you need me?" — surfaces what's blocking
    progress before the open queue. Each entry includes age and the
    `## Decision required` body section preview. With `--json`, returns
    structured payload for the AskUserQuestion-driven Q&A flow.
    """
    all_cards = [t for t in load_all_cards() if t.status == "open" and t.human_gate != "none"]
    if worker:
        needle = worker.lower()
        cards = [t for t in all_cards if needle in _worker_who(t.frontmatter.get("worker")).lower()]
    else:
        cards = all_cards
    today = date.today()

    def aged_days(t: Card) -> int:
        try:
            return (today - date.fromisoformat(t.created)).days
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
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if not payload:
        click.echo("No parked cards (gate ≠ none).")
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
    click.echo("\n".join(lines))


@cli.command()
@click.argument("title")
def show(title):
    """Print full README.md to stdout."""
    p = DECK_DIR / title / "README.md"
    if not p.exists():
        click.echo(f"ERROR: {p} not found", err=True)
        sys.exit(2)
    click.echo(p.read_text())


@cli.command()
@click.option("--dry-run", is_flag=True, help="Show what would happen without making changes.")
@click.option("--yes", "auto_yes", is_flag=True, help="Skip confirmation prompt.")
def migrate(dry_run, auto_yes):
    """Merge legacy deck/ into .game-of-cards/deck/ and remove the stale tree.

    Refuses if any card exists in both trees with differing content — resolve
    the drift manually first, then re-run.  Safe to run against a single-tree
    repo (it reports nothing to do and exits cleanly).
    """
    canonical = REPO_ROOT / ".game-of-cards" / "deck"
    legacy = REPO_ROOT / "deck"

    if not legacy.exists():
        click.echo("No legacy deck/ found; nothing to migrate.")
        return

    if not canonical.exists():
        click.echo(
            f"ERROR: canonical deck location {canonical} does not exist.\n"
            "Run `goc install` first to set up the canonical deck location.",
            err=True,
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
        click.echo(
            "ERROR: cards with content drift — cannot merge safely:",
            err=True,
        )
        for c in conflicts:
            click.echo(c, err=True)
        click.echo(
            "\nResolve the drifted cards manually (pick the authoritative version),\n"
            "then re-run `goc migrate`.",
            err=True,
        )
        sys.exit(1)

    if to_copy:
        click.echo("Cards to migrate (legacy-only):")
        for name in to_copy:
            click.echo(f"  deck/{name}/  →  .game-of-cards/deck/{name}/")
    if identical:
        click.echo(f"Cards already in canonical tree (identical, will skip): {len(identical)}")

    if not to_copy and not identical:
        click.echo("Legacy deck/ contains no card directories; nothing to migrate.")
        if not dry_run and not _DUAL_TREE_CONFLICT:
            return

    if dry_run:
        if to_copy or not legacy_dirs:
            click.echo(f"Would remove legacy tree: {legacy}")
        click.echo("Dry run — no changes made.")
        return

    if to_copy or identical:
        if not auto_yes:
            click.confirm(
                f"\nMigrate {len(to_copy)} card(s) and remove legacy deck/?",
                abort=True,
            )

    for name in to_copy:
        shutil.copytree(str(legacy_dirs[name]), str(canonical / name))
        click.echo(f"  migrated: {name}")

    shutil.rmtree(legacy)
    click.echo(f"\nRemoved legacy tree: {legacy}")
    click.echo("Migration complete. Run `goc validate` to confirm.")
    click.echo("Next: `goc validate` to verify card integrity after migration.")


@cli.command("migrate-list-style")
@click.option("--dry-run", is_flag=True, help="Show which cards would change without writing files.")
def migrate_list_style(dry_run):
    """Re-emit every card to convert advances/advanced_by to block-style lists.

    One-time migration: after running this, all cards will use block-style
    for `advances` and `advanced_by` (one `- item` per line) instead of
    inline flow style (`[a, b, c]`). Empty lists remain as `[]`.
    The diff is whitespace-equivalent for all fields except these two.
    """
    if not DECK_DIR.exists():
        click.echo(f"ERROR: {DECK_DIR} does not exist", err=True)
        sys.exit(1)

    changed: list[str] = []
    for card_dir in sorted(DECK_DIR.iterdir()):
        readme = card_dir / "README.md"
        if not readme.exists():
            continue
        original = readme.read_text()
        fm, body = parse_frontmatter(original)
        if not fm:
            continue
        rewritten = emit_frontmatter(fm, body=body)
        if rewritten != original:
            changed.append(card_dir.name)
            if not dry_run:
                readme.write_text(rewritten)

    if not changed:
        click.echo("All cards already use block-style for advances/advanced_by — nothing to do.")
        return

    if dry_run:
        click.echo(f"Would rewrite {len(changed)} card(s):")
        for name in changed:
            click.echo(f"  {name}")
        click.echo("Dry run — no changes made.")
    else:
        click.echo(f"Rewrote {len(changed)} card(s):")
        for name in changed:
            click.echo(f"  {name}")
        click.echo("Done. Run `goc validate` to confirm.")


if __name__ == "__main__":
    cli()
