"""`goc install` — scaffold the methodology into a target repo.

Drops the shared deck/config scaffold plus selected agent harness assets into
the current working directory. No-flag installs detect existing Claude/Codex
project surfaces and fall back to the Claude Code reference harness when no
agent marker is present. Codex uses the shared AGENTS.md guidance plus
Codex-readable skills, without Claude-only hooks.
Idempotent — second runs detect existing installs via `.game-of-cards/deck/.goc-version`
(or legacy `deck/.goc-version`) and exit clean.

Reads templates via `importlib.resources` so it works from a wheel install.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import click

from goc import __version__

GOC_BEGIN = f"<!-- BEGIN GOC v{__version__} -->"
GOC_BEGIN_RE = re.compile(r"<!-- BEGIN GOC v[\d.]+ -->")
GOC_END = "<!-- END GOC -->"

SUPPORTED_AGENTS = ("claude", "codex")
DEFAULT_AGENTS = ("claude",)
AGENT_SIGNAL_PATHS = {
    "claude": (Path("CLAUDE.md"), Path(".claude"), Path(".mcp.json")),
    "codex": (Path("AGENTS.md"), Path(".codex")),
}

PRE_COMMIT_HOOK = """\
  - repo: local
    hooks:
      - id: goc-validate
        name: goc validate
        entry: goc validate
        language: system
        pass_filenames: false
        files: ^\\.game-of-cards/deck/.*$
"""


@dataclass(frozen=True)
class PlannedWrite:
    owner: str
    action: str
    path: Path
    category: str  # "project-state" | "guidance" | "harness"


@dataclass(frozen=True)
class GuidanceBlock:
    path: str
    template: str
    header: str


@dataclass(frozen=True)
class ShimFile:
    source: Path
    target: Path
    mode: str | None = None


@dataclass(frozen=True)
class SkillShim:
    target: Path
    frontmatter: str


@dataclass(frozen=True)
class AgentShim:
    name: str
    skills: SkillShim | None
    files: tuple[ShimFile, ...]
    guidance: tuple[GuidanceBlock, ...]
    settings_json: Path | None = None


AGENTS_GUIDANCE = GuidanceBlock("AGENTS.md", "AGENTS_GOC.md", "# Agent Guidelines")
CLAUDE_GUIDANCE = GuidanceBlock("CLAUDE.md", "CLAUDE_GOC.md", "# Claude Code Guidelines")


def _templates_root() -> Path:
    """Return the on-disk path to the bundled `goc/templates/` tree."""

    return Path(str(resources.files("goc.templates")))


def _registered_agents(templates: Path) -> tuple[str, ...]:
    """Return installable agent names backed by `templates/agents/<agent>/`."""

    agents_root = templates / "agents"
    if not agents_root.exists():
        return SUPPORTED_AGENTS

    discovered = {path.name for path in agents_root.iterdir() if (path / "manifest.json").is_file()}
    ordered = [agent for agent in SUPPORTED_AGENTS if agent in discovered]
    ordered.extend(sorted(discovered - set(ordered)))
    return tuple(ordered) or SUPPORTED_AGENTS


def _load_agent_shim(templates: Path, agent: str) -> AgentShim:
    """Load the path/format convention for one agent harness."""

    manifest_path = templates / "agents" / agent / "manifest.json"
    try:
        raw = json.loads(manifest_path.read_text())
    except FileNotFoundError as exc:
        raise click.ClickException(f"agent {agent!r} has no template manifest at {manifest_path}") from exc

    skills = None
    if raw.get("skills"):
        skill_spec = raw["skills"]
        frontmatter = skill_spec.get("frontmatter", "native")
        if frontmatter not in {"native", "codex"}:
            raise click.ClickException(
                f"agent {agent!r} uses unsupported skill frontmatter mode {frontmatter!r}"
            )
        skills = SkillShim(target=Path(skill_spec["target"]), frontmatter=frontmatter)

    files = tuple(
        ShimFile(
            source=Path(file_spec["source"]),
            target=Path(file_spec["target"]),
            mode=file_spec.get("mode"),
        )
        for file_spec in raw.get("files", [])
    )
    guidance = tuple(
        GuidanceBlock(
            path=guidance_spec["target"],
            template=guidance_spec["source"],
            header=guidance_spec["header"],
        )
        for guidance_spec in raw.get("guidance", [])
    )
    settings_json = Path(raw["settings_json"]) if raw.get("settings_json") else None
    return AgentShim(
        name=raw.get("name", agent),
        skills=skills,
        files=files,
        guidance=guidance,
        settings_json=settings_json,
    )


def _parse_agents(
    agent_specs: tuple[str, ...],
    *,
    claude: bool = False,
    codex: bool = False,
    supported_agents: tuple[str, ...] = SUPPORTED_AGENTS,
    default_agents: tuple[str, ...] = DEFAULT_AGENTS,
) -> tuple[str, ...]:
    """Parse comma-separated/repeated `--agents` values into known harness names."""

    tokens: list[str] = []
    for spec in agent_specs:
        tokens.extend(part.strip().lower() for part in spec.split(",") if part.strip())
    if claude:
        tokens.append("claude")
    if codex:
        tokens.append("codex")
    if not tokens:
        tokens = list(default_agents)

    unknown = sorted(set(tokens) - set(supported_agents))
    if unknown:
        supported = ", ".join(supported_agents)
        raise click.BadParameter(
            f"unknown agent(s): {', '.join(unknown)}; supported: {supported}",
            param_hint="--agents",
        )

    requested = set(tokens)
    return tuple(agent for agent in supported_agents if agent in requested)


def _agent_override_requested(agent_specs: tuple[str, ...], *, claude: bool, codex: bool) -> bool:
    """Return whether the caller explicitly selected an agent harness."""

    return bool(agent_specs or claude or codex)


def _detect_agent_surfaces(
    target: Path,
    *,
    supported_agents: tuple[str, ...] = SUPPORTED_AGENTS,
) -> tuple[str, ...]:
    """Detect agent harnesses from repo-local files that predate installation."""

    detected: list[str] = []
    for agent in supported_agents:
        signals = AGENT_SIGNAL_PATHS.get(agent, ())
        if any((target / signal).exists() for signal in signals):
            detected.append(agent)
    return tuple(detected)


def _detect_installed_surfaces(
    target: Path,
    templates: Path,
    *,
    supported_agents: tuple[str, ...] = SUPPORTED_AGENTS,
) -> tuple[str, ...]:
    """Detect which agent harnesses GoC previously installed into *target*.

    Uses each harness's skill-tree directory as the canonical install marker,
    since those paths are agent-specific and GoC never writes one harness's
    skill directory for another harness.
    """

    detected: list[str] = []
    for agent in supported_agents:
        try:
            shim = _load_agent_shim(templates, agent)
        except click.ClickException:
            continue
        if shim.skills and (target / shim.skills.target).is_dir():
            detected.append(agent)
    return tuple(detected)


def _default_install_agents(target: Path, *, supported_agents: tuple[str, ...]) -> tuple[str, ...]:
    """Choose install defaults: detected harnesses, otherwise the documented default."""

    detected = _detect_agent_surfaces(target, supported_agents=supported_agents)
    if detected:
        return detected
    return tuple(agent for agent in supported_agents if agent in DEFAULT_AGENTS) or DEFAULT_AGENTS


def _detect_existing(deck_dir: Path) -> str | None:
    """Return the version pinned by `<deck_dir>/.goc-version`, or None if absent."""

    sentinel = deck_dir / ".goc-version"
    if not sentinel.exists():
        return None
    return sentinel.read_text().strip()


def _find_installed_deck_dir(target: Path) -> Path | None:
    """Return the path of an existing GoC install (new or legacy), or None."""
    new = target / ".game-of-cards" / "deck"
    if (new / ".goc-version").exists():
        return new
    legacy = target / "deck"
    if (legacy / ".goc-version").exists():
        return legacy
    return None


def _detect_claude_code() -> bool:
    """Return True if running inside a Claude Code session."""
    return bool(
        os.environ.get("CLAUDECODE")
        or os.environ.get("CLAUDE_CODE")
        or os.environ.get("CLAUDE_PROJECT_DIR")
    )


def _should_use_local_skills(agent: str, *, local_skills: bool) -> bool:
    """True if this agent should use the vendored skills layout (vs the plugin path).

    Codex always uses vendored layout (no plugin yet).
    Claude defaults to the plugin path; --local-skills opts in to vendored.
    """
    return agent != "claude" or local_skills


GOC_CLAUDE_HOOKS: dict[str, str] = {
    "SessionStart": "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py",
    "UserPromptSubmit": "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_prompt_router.py",
    "Stop": "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/pattern_generalization_check.py",
}

_HOOK_FILE_RE = re.compile(r"\$\{CLAUDE_PROJECT_DIR\}/(.+?\.py)")


def _merge_claude_settings(settings_path: Path) -> None:
    """Write or merge .claude/settings.json with GoC hook registrations.

    Adds GoC-managed hook entries under each event type without removing
    unrelated keys or hooks that belong to the user.
    """
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings: dict = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            pass

    hooks = settings.setdefault("hooks", {})
    for event, command in GOC_CLAUDE_HOOKS.items():
        event_hooks: list = hooks.setdefault(event, [])
        already = any(
            any(h.get("command") == command for h in group.get("hooks", []))
            for group in event_hooks
            if isinstance(group, dict)
        )
        if not already:
            event_hooks.append({"hooks": [{"type": "command", "command": command}]})

    settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def _strip_goc_settings_entries(settings_path: Path) -> None:
    """Remove GoC-managed hook entries from .claude/settings.json."""
    if not settings_path.exists():
        return
    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        return

    goc_commands = set(GOC_CLAUDE_HOOKS.values())
    hooks = settings.get("hooks", {})
    changed = False
    for event in list(hooks.keys()):
        new_groups: list = []
        for group in hooks[event]:
            if not isinstance(group, dict):
                new_groups.append(group)
                continue
            filtered = [h for h in group.get("hooks", []) if h.get("command") not in goc_commands]
            if len(filtered) != len(group.get("hooks", [])):
                changed = True
            if filtered:
                new_groups.append({**group, "hooks": filtered})
        if new_groups != hooks[event]:
            changed = True
        hooks[event] = new_groups

    for event in list(hooks.keys()):
        if not hooks[event]:
            del hooks[event]
            changed = True

    if not hooks:
        settings.pop("hooks", None)

    if changed:
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def _strip_claude_vendored_harness(target: Path, templates: Path) -> None:
    """Remove GoC-managed vendored files from a Claude install.

    Removes the skill tree, hook files (from the manifest and settings),
    and strips GoC entries from .claude/settings.json. User-authored files
    in .claude/ are not touched.
    """
    shim = _load_agent_shim(templates, "claude")

    if shim.skills:
        skills_dir = target / shim.skills.target
        if skills_dir.is_dir():
            shutil.rmtree(skills_dir)

    files_to_remove: set[Path] = set()
    for file in shim.files:
        files_to_remove.add(target / file.target)
    for cmd in GOC_CLAUDE_HOOKS.values():
        m = _HOOK_FILE_RE.search(cmd)
        if m:
            files_to_remove.add(target / m.group(1))

    for f in files_to_remove:
        if f.is_file():
            f.unlink()
        parent = f.parent
        try:
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
        except OSError:
            pass

    if shim.settings_json:
        _strip_goc_settings_entries(target / shim.settings_json)


def _plan_writes(
    target: Path,
    templates: Path,
    agents: tuple[str, ...],
    *,
    local_skills_agents: frozenset[str] = frozenset(),
) -> list[PlannedWrite]:
    """Compute the list of writes the installer will perform.

    Agents in `local_skills_agents` get the full vendored layout (skills +
    hooks + settings). Other agents get guidance only (plugin path model).
    """

    deck_dir = target / ".game-of-cards" / "deck"
    writes: list[PlannedWrite] = []
    writes.append(PlannedWrite("shared", "write", deck_dir / "log.md", "project-state"))
    writes.append(PlannedWrite("shared", "write", deck_dir / ".goc-version", "project-state"))
    config_src = templates / "game_of_cards"
    for asset in config_src.rglob("*"):
        if asset.is_dir() or "__pycache__" in asset.parts:
            continue
        rel = asset.relative_to(config_src)
        writes.append(PlannedWrite("shared", "write", target / ".game-of-cards" / rel, "project-state"))
    writes.append(PlannedWrite("shared", "append", target / AGENTS_GUIDANCE.path, "guidance"))
    for agent in agents:
        shim = _load_agent_shim(templates, agent)
        is_local = agent in local_skills_agents
        if is_local and shim.skills:
            for rel in _iter_skill_assets(templates / "skills"):
                writes.append(PlannedWrite(agent, "write", target / shim.skills.target / rel, "harness"))
        if is_local:
            for file in shim.files:
                writes.append(PlannedWrite(agent, "write", target / file.target, "harness"))
        for guidance in shim.guidance:
            writes.append(PlannedWrite(agent, "append", target / guidance.path, "guidance"))
        if is_local and shim.settings_json:
            writes.append(PlannedWrite(agent, "merge", target / shim.settings_json, "harness"))
    writes.append(PlannedWrite("shared", "append", target / ".pre-commit-config.yaml", "guidance"))
    return writes


def _plan_upgrade_writes(
    target: Path,
    templates: Path,
    agents: tuple[str, ...],
    *,
    local_skills_agents: frozenset[str] = frozenset(),
) -> list[PlannedWrite]:
    """Compute the list of writes the upgrader will perform."""

    writes: list[PlannedWrite] = []
    for write in _plan_writes(target, templates, agents, local_skills_agents=local_skills_agents):
        if write.path.name == "log.md":
            continue
        action = "sync" if write.action == "write" else write.action
        writes.append(PlannedWrite(write.owner, action, write.path, write.category))
    return writes


_CATEGORY_LABELS = [
    ("project-state", "Project state"),
    ("guidance", "Guidance"),
    ("harness", "Runtime affordances"),
]


def _print_plan(command: str, target: Path, writes: list[PlannedWrite], agents: tuple[str, ...]) -> None:
    """Render a dry-run write plan grouped by category."""

    agents_str = ",".join(agents) if agents else "none"
    click.echo(f"goc {command} (dry-run) — agents: {agents_str} — {len(writes)} writes planned")
    for cat_key, cat_label in _CATEGORY_LABELS:
        cat_writes = [w for w in writes if w.category == cat_key]
        if not cat_writes:
            continue
        click.echo(f"\n{cat_label}:")
        for write in cat_writes:
            click.echo(f"  {write.owner:6s} {write.action:6s} {write.path.relative_to(target)}")


def _copy_tree(src: Path, dst: Path, *, skip_existing: set[Path] | None = None) -> None:
    """Copy a directory tree, skipping `__pycache__`."""

    skip_existing = skip_existing or set()
    for asset in src.rglob("*"):
        if asset.is_dir() or "__pycache__" in asset.parts:
            continue
        rel = asset.relative_to(src)
        target = dst / rel
        if rel in skip_existing and target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset, target)


def _sync_game_of_cards_config(target: Path, templates: Path, *, migrate_legacy: bool = False) -> None:
    """Sync `.game-of-cards/` assets, preserving migrated closure config."""

    config_dst = target / ".game-of-cards"
    config_dst.mkdir(parents=True, exist_ok=True)
    config_file = config_dst / "config.yaml"
    legacy_config = target / ".claude" / "deck-config.yaml"
    if migrate_legacy and not config_file.exists() and legacy_config.exists():
        shutil.copy2(legacy_config, config_file)
    skip_existing = {Path("config.yaml")} if migrate_legacy else set()
    _copy_tree(templates / "game_of_cards", config_dst, skip_existing=skip_existing)


def _frontmatter_value(text: str, key: str) -> str:
    """Extract a single-line frontmatter value without requiring valid YAML."""

    prefix = f"{key}:"
    for line in text.splitlines():
        if not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            return value[1:-1]
        return value
    return ""


def _write_codex_skill(src: Path, dst: Path, *, skill_name: str) -> None:
    """Write a Codex-compatible SKILL.md copy from the shared template."""

    text = src.read_text()
    if not text.startswith("---\n"):
        shutil.copy2(src, dst)
        return

    try:
        _, frontmatter, body = text.split("---", 2)
    except ValueError:
        shutil.copy2(src, dst)
        return

    name = _frontmatter_value(frontmatter, "name") or skill_name
    description = _frontmatter_value(frontmatter, "description")
    body = body.replace("echo .claude/skills", "echo .codex/skills")
    body = body.replace(".claude/skills/_goc-bootstrap.sh", ".codex/skills/_goc-bootstrap.sh")
    codex_frontmatter = "\n".join(
        (
            "---",
            f"name: {name}",
            f"description: {json.dumps(description, ensure_ascii=False)}",
            "---",
        )
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(codex_frontmatter + body)


def _iter_skill_assets(skills_src: Path) -> list[Path]:
    """Return bundled skill assets relative to the skill tree root."""

    paths: list[Path] = []
    for skill_dir in sorted(p for p in skills_src.iterdir() if p.is_dir()):
        for asset in skill_dir.rglob("*"):
            if asset.is_dir() or "__pycache__" in asset.parts:
                continue
            paths.append(asset.relative_to(skills_src))
    return paths


def _sync_skill_tree(
    templates: Path,
    skills_dst: Path,
    *,
    replace_skills: bool = False,
    codex_frontmatter: bool = False,
) -> None:
    """Copy GoC skills into a runtime-specific skill root."""

    skills_src = templates / "skills"
    skills_dst.mkdir(parents=True, exist_ok=True)
    if replace_skills:
        for skill_dir in sorted(p for p in skills_src.iterdir() if p.is_dir()):
            target = skills_dst / skill_dir.name
            if target.exists():
                shutil.rmtree(target)
    for asset in skills_src.rglob("*"):
        if asset.is_dir() or "__pycache__" in asset.parts:
            continue
        rel = asset.relative_to(skills_src)
        target = skills_dst / rel
        if codex_frontmatter and asset.name == "SKILL.md":
            _write_codex_skill(asset, target, skill_name=rel.parts[0])
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset, target)


def _append_marker_block(target: Path, block_body: str, *, header: str) -> None:
    """Append (or replace) a marker-bounded GoC section in a markdown file.

    Works for both AGENTS.md and CLAUDE.md — the marker pattern is identical;
    only the content and the file-creation header differ.
    """

    block = f"{GOC_BEGIN}\n{block_body.rstrip()}\n{GOC_END}\n"
    if not target.exists():
        target.write_text(f"{header}\n\n{block}")
        return
    text = target.read_text()
    pattern = re.compile(rf"{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n?", re.DOTALL)
    if pattern.search(text):
        target.write_text(pattern.sub(block, text))
        return
    target.write_text(text.rstrip() + "\n\n" + block)


def _append_precommit_hook(target: Path) -> None:
    """Append the `goc validate` hook to `.pre-commit-config.yaml` (creating it)."""

    if not target.exists():
        target.write_text("repos:\n" + PRE_COMMIT_HOOK)
        return
    text = target.read_text()
    if "id: goc-validate" in text:
        return
    if not text.endswith("\n"):
        text += "\n"
    target.write_text(text + PRE_COMMIT_HOOK)


def _sync_methodology_blocks(target: Path, templates: Path) -> None:
    """Write the shared marker-bounded methodology block."""

    agents_body = (templates / AGENTS_GUIDANCE.template).read_text()
    _append_marker_block(target / AGENTS_GUIDANCE.path, agents_body, header=AGENTS_GUIDANCE.header)


def _sync_agent_harness(
    target: Path,
    templates: Path,
    agent: str,
    *,
    replace_skills: bool = False,
    guidance_only: bool = False,
) -> None:
    """Copy and render one agent's shim from its template manifest.

    When `guidance_only=True`, only the agent's guidance block (e.g. CLAUDE.md)
    is written. Skills, hook files, and settings.json are skipped — the plugin
    path model.
    """

    shim = _load_agent_shim(templates, agent)
    if not guidance_only:
        if shim.skills:
            _sync_skill_tree(
                templates,
                target / shim.skills.target,
                replace_skills=replace_skills,
                codex_frontmatter=shim.skills.frontmatter == "codex",
            )

        for file in shim.files:
            destination = target / file.target
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(templates / file.source, destination)
            if file.mode == "executable":
                destination.chmod(destination.stat().st_mode | 0o755)

        if shim.settings_json:
            _merge_claude_settings(target / shim.settings_json)

    for guidance in shim.guidance:
        body = (templates / guidance.template).read_text()
        _append_marker_block(target / guidance.path, body, header=guidance.header)


INSTALL_AGENTS_HELP = (
    "Agent harnesses to install; repeat or comma-separate. "
    "Omit to auto-detect Claude/Codex project markers; no marker defaults to claude. "
    "Supported: claude, codex."
)
UPGRADE_AGENTS_HELP = (
    "Agent harnesses to upgrade; repeat or comma-separate. "
    "Omit to auto-detect from installed harnesses; no harness defaults to claude. "
    "Supported: claude, codex."
)
LOCAL_SKILLS_HELP = (
    "Vendor skills, hooks, and settings entries into source control. "
    "Default for Codex (no plugin yet); opt-in for Claude. "
    "Use for CI environments without plugin support, or repos that fork/template GoC."
)
KEEP_LOCAL_SKILLS_HELP = (
    "Preserve the existing vendored skills layout and refresh templates in place. "
    "Skips the migration to the plugin path. "
    "Use in scripted contexts (CI cron, etc.) to opt out of migration."
)

_PLUGIN_INSTALL_CMDS = (
    "  /plugin marketplace add zauberzeug/game-of-cards\n"
    "  /plugin install game-of-cards@game-of-cards"
)


@click.command()
@click.option("--dry-run", is_flag=True, help="Print planned writes; do not touch the filesystem.")
@click.option("--agents", "agent_specs", multiple=True, help=INSTALL_AGENTS_HELP)
@click.option("--claude", "claude_flag", is_flag=True, help="Shortcut for --agents claude.")
@click.option("--codex", "codex_flag", is_flag=True, help="Shortcut for --agents codex.")
@click.option("--local-skills", "local_skills", is_flag=True, help=LOCAL_SKILLS_HELP)
def install(
    dry_run: bool,
    agent_specs: tuple[str, ...],
    claude_flag: bool,
    codex_flag: bool,
    local_skills: bool,
) -> None:
    """Scaffold a fresh repo with the shared GoC files and selected harnesses."""

    target = Path.cwd().resolve()
    deck_dir = target / ".game-of-cards" / "deck"
    templates = _templates_root()
    supported_agents = _registered_agents(templates)

    explicit_agents = _agent_override_requested(agent_specs, claude=claude_flag, codex=codex_flag)
    detected_agents = _detect_agent_surfaces(target, supported_agents=supported_agents)
    default_agents = detected_agents or _default_install_agents(target, supported_agents=supported_agents)
    agents = _parse_agents(
        agent_specs,
        claude=claude_flag,
        codex=codex_flag,
        supported_agents=supported_agents,
        default_agents=default_agents,
    )

    local_skills_agents = frozenset(a for a in agents if _should_use_local_skills(a, local_skills=local_skills))

    writes = _plan_writes(target, templates, agents, local_skills_agents=local_skills_agents)
    if dry_run:
        _print_plan("install", target, writes, agents)
        return

    existing_dir = _find_installed_deck_dir(target)
    if existing_dir is not None:
        existing = _detect_existing(existing_dir)
        rel = existing_dir.relative_to(target)
        click.echo(f"already installed ({rel}/.goc-version → {existing})", err=True)
        click.echo("Run `goc upgrade` to re-sync templates.", err=True)
        sys.exit(1)

    for agent in agents:
        guidance_only = agent not in local_skills_agents
        _sync_agent_harness(target, templates, agent, guidance_only=guidance_only)

    deck_dir.mkdir(parents=True, exist_ok=True)
    (deck_dir / "log.md").write_text("# Deck Log\n\nAppend deck-level events here (sprint notes, schema bumps, etc.).\n")
    (deck_dir / ".goc-version").write_text(__version__ + "\n")

    _sync_game_of_cards_config(target, templates)

    _sync_methodology_blocks(target, templates)

    _append_precommit_hook(target / ".pre-commit-config.yaml")

    source = ""
    if not explicit_agents:
        source = " (auto-detected)" if detected_agents else " (default)"
    click.echo(f"goc {__version__} installed for agents: {','.join(agents)}{source}.")
    click.echo(
        'Next: ask your LLM agent to "expand the deck" — it audits the repo and files initial cards. '
        'Or "create a card for X" if you already know the first change you want to make.'
    )

    if "claude" in agents and "claude" not in local_skills_agents:
        if _detect_claude_code():
            click.echo(
                "GoC plugin: to enable skills and hooks, ask the user to confirm then run:\n"
                + _PLUGIN_INSTALL_CMDS
            )
        else:
            click.echo(
                "Next steps for Claude Code users — install the GoC plugin (one-time per machine):\n"
                + _PLUGIN_INSTALL_CMDS
            )

    click.echo(
        "Engine/debug: `goc` shows the queue; `goc validate` checks cards. "
        "Run `goc upgrade` later to sync template updates."
    )


@click.command()
@click.option("--dry-run", is_flag=True, help="Print planned writes; do not touch the filesystem.")
@click.option("--agents", "agent_specs", multiple=True, help=UPGRADE_AGENTS_HELP)
@click.option("--claude", "claude_flag", is_flag=True, help="Shortcut for --agents claude.")
@click.option("--codex", "codex_flag", is_flag=True, help="Shortcut for --agents codex.")
@click.option("--keep-local-skills", "keep_local_skills", is_flag=True, help=KEEP_LOCAL_SKILLS_HELP)
def upgrade(
    dry_run: bool,
    agent_specs: tuple[str, ...],
    claude_flag: bool,
    codex_flag: bool,
    keep_local_skills: bool,
) -> None:
    """Re-sync skill templates, AGENTS.md, and CLAUDE.md sections from the installed package version."""

    target = Path.cwd().resolve()
    templates = _templates_root()
    supported_agents = _registered_agents(templates)

    agents_explicit = _agent_override_requested(agent_specs, claude=claude_flag, codex=codex_flag)
    if agents_explicit:
        default_agents: tuple[str, ...] = DEFAULT_AGENTS
    else:
        installed = _detect_installed_surfaces(target, templates, supported_agents=supported_agents)
        default_agents = installed or DEFAULT_AGENTS
    agents = _parse_agents(
        agent_specs,
        claude=claude_flag,
        codex=codex_flag,
        supported_agents=supported_agents,
        default_agents=default_agents,
    )

    deck_dir = _find_installed_deck_dir(target)
    if deck_dir is None:
        click.echo("no existing install detected — run `goc install` first.", err=True)
        sys.exit(1)
    existing = _detect_existing(deck_dir)

    # Determine migration status for Claude: vendored → plugin path
    claude_has_vendored = False
    if "claude" in agents:
        claude_shim = _load_agent_shim(templates, "claude")
        claude_has_vendored = bool(claude_shim.skills and (target / claude_shim.skills.target).is_dir())

    do_migrate_claude = claude_has_vendored and not keep_local_skills
    agents_to_migrate: frozenset[str] = frozenset(["claude"]) if do_migrate_claude else frozenset()

    # For the vendored-layout question: either explicitly kept, or migrating away, or never had vendored
    local_skills_agents: frozenset[str]
    if keep_local_skills:
        local_skills_agents = frozenset(a for a in agents if a == "claude" and claude_has_vendored) | frozenset(
            a for a in agents if a != "claude"
        )
    else:
        # After migration (or if no vendored layout): only codex uses local skills
        local_skills_agents = frozenset(a for a in agents if a != "claude")

    pending_migration = do_migrate_claude and not dry_run

    if existing == __version__ and not dry_run and not agents_explicit and not pending_migration and not keep_local_skills:
        click.echo(f"already at goc {__version__} — nothing to do.")
        return

    if dry_run:
        migration_note = " (will migrate vendored .claude/skills/ → plugin path)" if do_migrate_claude else ""
        click.echo(f"goc upgrade would sync {existing} → {__version__}{migration_note}")
        _print_plan(
            "upgrade",
            target,
            _plan_upgrade_writes(target, templates, agents, local_skills_agents=local_skills_agents),
            agents,
        )
        return

    # Interactive migration prompt for Claude vendored → plugin path
    if do_migrate_claude:
        click.echo(
            "This repo has vendored GoC skills. goc upgrade now defaults to the plugin path —\n"
            "this will remove .claude/skills/, .claude/hooks/ (GoC-managed), and GoC\n"
            "entries from .claude/settings.json. Pass --keep-local-skills to skip."
        )
        confirmed = click.confirm("Migrate to plugin path?", default=True)
        if not confirmed:
            agents_to_migrate = frozenset()
            local_skills_agents = local_skills_agents | frozenset(["claude"])

    for agent in agents_to_migrate:
        if agent == "claude":
            _strip_claude_vendored_harness(target, templates)

    for agent in agents:
        guidance_only = agent not in local_skills_agents
        replace = agent in local_skills_agents
        _sync_agent_harness(target, templates, agent, guidance_only=guidance_only, replace_skills=replace)

    _sync_game_of_cards_config(target, templates, migrate_legacy=True)

    _sync_methodology_blocks(target, templates)

    (deck_dir / ".goc-version").write_text(__version__ + "\n")

    click.echo(f"goc upgrade complete for agents: {','.join(agents)} — {existing} → {__version__}.")
    click.echo("Next: re-run goc validate to confirm cards parse against the new schema.")


if __name__ == "__main__":
    install()
