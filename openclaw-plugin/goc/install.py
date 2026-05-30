"""`goc install` — scaffold the methodology into a target repo.

Drops the shared deck/config scaffold plus selected agent harness assets into
the current working directory. No-flag installs detect existing Claude/Codex
project surfaces and fall back to the Claude Code reference harness when no
agent marker is present. Codex uses the shared AGENTS.md guidance plus
Codex-readable skills, without Claude-only hooks. The exception is the OpenClaw
plugin context (this engine running from `openclaw-plugin/`): OpenClaw ships
skills via its plugin runtime and has no harness surface, so the no-flag default
there is no harness at all — shared scaffold + AGENTS.md only, never CLAUDE.md.
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
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

from goc import __version__

GOC_BEGIN = f"<!-- BEGIN GOC v{__version__} -->"
GOC_BEGIN_RE = re.compile(r"<!-- BEGIN GOC v[\w.+!-]+ -->")
GOC_END = "<!-- END GOC -->"
CLAUDE_IMPORT_BEGIN = "<!-- BEGIN GOC IMPORT -->"
CLAUDE_IMPORT_END = "<!-- END GOC IMPORT -->"
CLAUDE_IMPORT_RE = re.compile(
    rf"{re.escape(CLAUDE_IMPORT_BEGIN)}.*?{re.escape(CLAUDE_IMPORT_END)}\n?",
    re.DOTALL,
)
CLAUDE_IMPORTABLE_TARGETS = ("AGENTS.md", "CLAUDE.local.md")

SUPPORTED_AGENTS = ("claude", "codex")
# Hosts whose skills ship via plugin rather than `goc install --agents`.
# Listed for skill-prefix filtering only — adding a name here keeps
# `<host>-foo` skills out of every other host's install tree without
# making `<host>` a valid `--agents` target.
PLUGIN_ONLY_AGENTS = ("openclaw",)
DEFAULT_AGENTS = ("claude",)
AGENT_SIGNAL_PATHS = {
    "claude": (Path("CLAUDE.md"), Path(".claude"), Path(".mcp.json")),
    "codex": (Path("AGENTS.md"), Path(".codex")),
}

BRIEFING_TARGETS = ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md")
DEFAULT_BRIEFING_TARGET = "AGENTS.md"
BRIEFING_HEADERS = {
    "AGENTS.md": "# Agent Guidelines",
    "CLAUDE.md": "# Claude Code Guidelines",
    "CLAUDE.local.md": "# Local notes for Claude Code (not checked in)",
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


def _validate_briefing_target(briefing_target: str) -> None:
    """Exit with a clear error if the briefing target is not one of the supported homes."""

    if briefing_target not in BRIEFING_TARGETS:
        supported = ", ".join(BRIEFING_TARGETS)
        print(
            f"goc: error: --briefing-target: unknown target {briefing_target!r}; supported: {supported}",
            file=sys.stderr,
        )
        sys.exit(2)


def _briefing_body(templates: Path, briefing_target: str) -> str:
    """Return the full briefing body for `briefing_target`.

    AGENTS.md and CLAUDE.local.md receive the host-agnostic body verbatim.
    CLAUDE.md (sole-home mode) gets the host-agnostic body plus the
    Claude-specific extras appended — option (a) from the card body
    (merge inline rather than maintain a unified template).
    """

    agents_body = (templates / AGENTS_GUIDANCE.template).read_text().rstrip()
    if briefing_target == "CLAUDE.md":
        claude_body = (templates / CLAUDE_GUIDANCE.template).read_text().rstrip()
        return f"{agents_body}\n\n{claude_body}\n"
    return agents_body + "\n"


def _detect_briefing_targets_on_disk(target: Path) -> tuple[str, ...]:
    """Return briefing-target candidates that already carry a GoC marker block."""

    found: list[str] = []
    for candidate in BRIEFING_TARGETS:
        path = target / candidate
        if not path.exists():
            continue
        try:
            text = path.read_text()
        except OSError:
            continue
        if GOC_BEGIN_RE.search(text):
            found.append(candidate)
    return tuple(found)


def _detect_newline(raw: bytes) -> str:
    """Return *raw*'s dominant line ending — ``\\r\\n`` if CRLF predominates, else ``\\n``."""

    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    return "\r\n" if crlf > lf else "\n"


def _read_text_keep_newline(path: Path) -> tuple[str, str]:
    """Read *path* as LF-normalized text, returning ``(text, detected_newline)``.

    The returned text matches `Path.read_text()`'s universal-newline
    normalization, but the second element reports the file's dominant line
    ending so callers can re-emit it via `_write_text_keep_newline` instead of
    silently forcing LF on a CRLF-authored file.
    """

    raw = path.read_bytes()
    newline = _detect_newline(raw)
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return text, newline


def _write_text_keep_newline(path: Path, text: str, newline: str) -> None:
    """Write LF-normalized *text* to *path*, translating ``\\n`` back to *newline*."""

    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("utf-8"))


def _strip_goc_block(path: Path) -> None:
    """Remove the GoC marker-bounded block from a markdown file (no-op if absent).

    If the file becomes empty or holds nothing but a stock header, delete it.
    """

    if not path.exists():
        return
    text, newline = _read_text_keep_newline(path)
    pattern = re.compile(rf"\n*{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n*", re.DOTALL)
    new = pattern.sub("\n\n", text).strip()
    header_only = re.fullmatch(r"# (Agent Guidelines|Claude Code Guidelines|Local notes for Claude Code \(not checked in\))\s*", new)
    if not new or header_only:
        path.unlink()
    else:
        _write_text_keep_newline(path, new + "\n", newline)


def _strip_claude_import(path: Path) -> None:
    """Remove GoC's Claude import pointer from CLAUDE.md, preserving user text."""

    if not path.exists():
        return
    text, newline = _read_text_keep_newline(path)
    text = CLAUDE_IMPORT_RE.sub("", text)
    lines = [
        line
        for line in text.splitlines()
        if line.strip() not in {f"@{target}" for target in CLAUDE_IMPORTABLE_TARGETS}
    ]
    new = "\n".join(lines).strip()
    header_only = re.fullmatch(r"# Claude Code Guidelines\s*", new)
    if not new or header_only:
        path.unlink()
    else:
        _write_text_keep_newline(path, new + "\n", newline)


def _sync_claude_import(target: Path, briefing_target: str) -> None:
    """Ensure Claude Code loads a non-CLAUDE.md briefing home via @ import.

    Fresh GoC-owned CLAUDE.md files stay as a single `@...` line. If the
    user already has custom CLAUDE.md content, keep it and manage a small
    marker-bounded import block instead of overwriting their text.
    """

    if briefing_target not in CLAUDE_IMPORTABLE_TARGETS:
        return
    claude_md = target / "CLAUDE.md"
    import_line = f"@{briefing_target}"
    if not claude_md.exists():
        claude_md.write_text(import_line + "\n")
        return

    text, newline = _read_text_keep_newline(claude_md)
    stripped = text.strip()
    import_lines = {f"@{candidate}" for candidate in CLAUDE_IMPORTABLE_TARGETS}
    if not stripped or stripped in import_lines:
        _write_text_keep_newline(claude_md, import_line + "\n", newline)
        return

    block = f"{CLAUDE_IMPORT_BEGIN}\n{import_line}\n{CLAUDE_IMPORT_END}\n"
    if CLAUDE_IMPORT_RE.search(text):
        _write_text_keep_newline(claude_md, CLAUDE_IMPORT_RE.sub(lambda _: block, text), newline)
        return

    lines = text.splitlines()
    replaced_bare_import = False
    for idx, line in enumerate(lines):
        if line.strip() in import_lines:
            lines[idx] = import_line
            replaced_bare_import = True
    if replaced_bare_import:
        _write_text_keep_newline(claude_md, "\n".join(lines).rstrip() + "\n", newline)
        return

    _write_text_keep_newline(claude_md, text.rstrip() + "\n\n" + block, newline)


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


def deck_hook_scripts(templates: Path) -> list[str]:
    """Return sorted basenames of deck hook scripts under templates/hooks/.

    Each `.py` file in that directory is a Claude Code hook: copied into a
    consuming repo's `.claude/hooks/` by the local-skills install path,
    mirrored byte-for-byte to `claude-plugin/hooks/` for plugin distribution,
    and registered with an event in `GOC_CLAUDE_HOOKS`. Treating the
    directory as the source of truth means dropping a new `.py` file there
    wires it into the install copy and the parity mirrors automatically;
    `validate_hook_registration` then catches the only remaining hand-edit
    (the event-to-script mapping in `GOC_CLAUDE_HOOKS`).
    """
    hooks_dir = templates / "hooks"
    if not hooks_dir.exists():
        return []
    return sorted(p.name for p in hooks_dir.iterdir() if p.is_file() and p.suffix == ".py")


def _load_agent_shim(templates: Path, agent: str) -> AgentShim:
    """Load the path/format convention for one agent harness."""

    manifest_path = templates / "agents" / agent / "manifest.json"
    try:
        raw = json.loads(manifest_path.read_text())
    except FileNotFoundError:
        print(f"goc: error: agent {agent!r} has no template manifest at {manifest_path}", file=sys.stderr)
        sys.exit(1)

    skills = None
    if raw.get("skills"):
        skill_spec = raw["skills"]
        frontmatter = skill_spec.get("frontmatter", "native")
        if frontmatter not in {"native", "codex"}:
            print(f"goc: error: agent {agent!r} uses unsupported skill frontmatter mode {frontmatter!r}", file=sys.stderr)
            sys.exit(1)
        skills = SkillShim(target=Path(skill_spec["target"]), frontmatter=frontmatter)

    files = tuple(
        ShimFile(
            source=Path(file_spec["source"]),
            target=Path(file_spec["target"]),
            mode=file_spec.get("mode"),
        )
        for file_spec in raw.get("files", [])
    )
    if agent == "claude":
        files = files + tuple(
            ShimFile(
                source=Path("hooks") / name,
                target=Path(".claude/hooks") / name,
            )
            for name in deck_hook_scripts(templates)
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
        print(f"goc: error: --agents: unknown agent(s): {', '.join(unknown)}; supported: {supported}", file=sys.stderr)
        sys.exit(2)

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
        except SystemExit:
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


_PACKAGE_DIR = Path(__file__).resolve().parent  # this goc/ package on disk


def _is_plugin_context() -> bool:
    """True when this engine is running from a copy bundled inside a GoC plugin.

    Plugin payloads carry `goc/` at `<plugin_root>/goc/` and their wrappers set
    PYTHONPATH so `python -m goc.cli` resolves to that nested copy. In every
    other layout (pipx, editable install, `uv run --project .`) the parent of
    the package directory is the project root or a site-packages dir.
    """
    return _PACKAGE_DIR.parent.name in {"claude-plugin", "codex-plugin", "openclaw-plugin"}


def _is_openclaw_plugin_context() -> bool:
    """True when this engine runs from the bundled copy inside `openclaw-plugin/`.

    OpenClaw provides skills and lifecycle hooks through its plugin runtime and
    has no Claude/Codex-style harness surface (no CLAUDE.md, no settings.json,
    no `.claude/` tree). So under this context the install/upgrade default is
    *no harness* — only the shared `.game-of-cards/` scaffold plus the AGENTS.md
    briefing — rather than the Claude fallback every other layout uses. Keyed on
    the same package-location signal as `_is_plugin_context()` so it is automatic
    regardless of how `goc install` was invoked.
    """
    return _PACKAGE_DIR.parent.name == "openclaw-plugin"


_LOCAL_SKILLS_PLUGIN_REFUSAL = (
    "ERROR: --local-skills is not supported when running under the plugin.\n"
    "       Skills are already provided by the plugin payload and\n"
    "       registered with the host runtime.\n"
    "\n"
    "       To use vendored skills (e.g. for CI without plugin support, or a\n"
    "       repo that forks/templates GoC), install goc via pipx instead:\n"
    "\n"
    "           pipx install game-of-cards\n"
    "           goc install --local-skills\n"
    "\n"
    "       Or omit --local-skills here to use the plugin path."
)
_KEEP_LOCAL_SKILLS_PLUGIN_REFUSAL = (
    "ERROR: --keep-local-skills is not supported when running under the plugin.\n"
    "       Skills are already provided by the plugin payload and\n"
    "       registered with the host runtime; there is no vendored layout for the\n"
    "       plugin engine to preserve.\n"
    "\n"
    "       If you need to keep a vendored .claude/skills/ tree (e.g. for CI\n"
    "       without plugin support), upgrade via pipx instead:\n"
    "\n"
    "           pipx install game-of-cards\n"
    "           goc upgrade --keep-local-skills\n"
    "\n"
    "       Or omit --keep-local-skills here to migrate to the plugin path."
)


def _should_use_local_skills(agent: str, *, local_skills: bool) -> bool:
    """True if this agent should use the vendored skills layout (vs the plugin path).

    Codex always uses vendored layout (no plugin yet).
    Claude defaults to the plugin path; --local-skills opts in to vendored.
    """
    return agent != "claude" or local_skills


GOC_CLAUDE_HOOKS: dict[str, str] = {
    "SessionStart": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py",
    "UserPromptSubmit": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_prompt_router.py",
    "Stop": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/pattern_generalization_check.py",
}

_HOOK_FILE_RE = re.compile(r"\$\{CLAUDE_PROJECT_DIR\}/(.+?\.py)")


def _backup_unparseable_settings(settings_path: Path, original: str) -> Path:
    """Preserve an unparseable settings file's bytes in a timestamped sibling."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = settings_path.with_name(f"{settings_path.name}.{ts}.bak")
    backup.write_text(original)
    return backup


def _merge_claude_settings(settings_path: Path) -> None:
    """Write or merge .claude/settings.json with GoC hook registrations.

    Adds GoC-managed hook entries under each event type without removing
    unrelated keys or hooks that belong to the user.
    """
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings: dict = {}
    original: str = ""
    backup_path: Path | None = None

    def _ensure_backup() -> Path:
        nonlocal backup_path
        if backup_path is None:
            backup_path = _backup_unparseable_settings(settings_path, original)
        return backup_path

    if settings_path.exists():
        original = settings_path.read_text()
        try:
            settings = json.loads(original)
        except json.JSONDecodeError as exc:
            backup = _ensure_backup()
            print(
                f"  warning: {settings_path} is not valid JSON ({exc}); "
                f"backed it up to {backup.name} before writing GoC hooks. "
                f"Merge your keys back in by hand.",
                file=sys.stderr,
            )
        if not isinstance(settings, dict):
            backup = _ensure_backup()
            print(
                f"  warning: {settings_path} is valid JSON but not an object "
                f"(got {type(settings).__name__}); backed it up to {backup.name} "
                f"before writing GoC hooks. Merge your keys back in by hand.",
                file=sys.stderr,
            )
            settings = {}

    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        backup = _ensure_backup()
        print(
            f"  warning: {settings_path} has a non-object `hooks` field "
            f"(got {type(hooks).__name__}); backed it up to {backup.name} "
            f"before writing GoC hooks. Merge your keys back in by hand.",
            file=sys.stderr,
        )
        settings["hooks"] = {}
        hooks = settings["hooks"]

    for event, command in GOC_CLAUDE_HOOKS.items():
        event_hooks = hooks.setdefault(event, [])
        if not isinstance(event_hooks, list):
            backup = _ensure_backup()
            print(
                f"  warning: {settings_path} hooks.{event} is "
                f"{type(event_hooks).__name__} (expected list); backed it up "
                f"to {backup.name} and reset to []. Merge your value back in "
                f"by hand.",
                file=sys.stderr,
            )
            hooks[event] = []
            event_hooks = hooks[event]
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
    except json.JSONDecodeError as exc:
        print(
            f"  warning: {settings_path} is not valid JSON ({exc}); "
            f"leaving it untouched (GoC hook entries not removed).",
            file=sys.stderr,
        )
        return
    if not isinstance(settings, dict):
        print(
            f"  warning: {settings_path} is valid JSON but not an object "
            f"(got {type(settings).__name__}); leaving it untouched "
            f"(GoC hook entries not removed).",
            file=sys.stderr,
        )
        return

    goc_commands = set(GOC_CLAUDE_HOOKS.values())
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        print(
            f"  warning: {settings_path} has a non-object `hooks` field "
            f"(got {type(hooks).__name__}); leaving it untouched "
            f"(GoC hook entries not removed).",
            file=sys.stderr,
        )
        return

    changed = False
    for event in list(hooks.keys()):
        event_value = hooks[event]
        if not isinstance(event_value, list):
            print(
                f"  warning: {settings_path} hooks.{event} is "
                f"{type(event_value).__name__} (expected list); leaving it "
                f"untouched (GoC hook entries not removed for this event).",
                file=sys.stderr,
            )
            continue
        new_groups: list = []
        for group in event_value:
            if not isinstance(group, dict):
                new_groups.append(group)
                continue
            filtered = [h for h in group.get("hooks", []) if h.get("command") not in goc_commands]
            if len(filtered) != len(group.get("hooks", [])):
                changed = True
            if filtered:
                new_groups.append({**group, "hooks": filtered})
        if new_groups != event_value:
            changed = True
        hooks[event] = new_groups

    for event in list(hooks.keys()):
        if isinstance(hooks[event], list) and not hooks[event]:
            del hooks[event]
            changed = True

    if not hooks:
        settings.pop("hooks", None)

    if changed:
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def _strip_claude_vendored_harness(target: Path, templates: Path) -> None:
    """Remove GoC-managed vendored files from a Claude install.

    Removes only the skill directories whose names match GoC templates,
    the hook files registered in the manifest and settings, and strips
    GoC entries from .claude/settings.json. User-authored skills with
    other names in `.claude/skills/` are preserved.
    """
    shim = _load_agent_shim(templates, "claude")

    if shim.skills:
        skills_dir = target / shim.skills.target
        if skills_dir.is_dir():
            skills_src = templates / "skills"
            goc_owned = {
                p.name for p in skills_src.iterdir()
                if p.is_dir() and skill_for_agent(p.name, "claude")
            }
            for child in list(skills_dir.iterdir()):
                if child.is_dir() and child.name in goc_owned:
                    shutil.rmtree(child)
            try:
                if not any(skills_dir.iterdir()):
                    skills_dir.rmdir()
            except OSError:
                pass

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
    briefing_target: str = DEFAULT_BRIEFING_TARGET,
) -> list[PlannedWrite]:
    """Compute the list of writes the installer will perform.

    Agents in `local_skills_agents` get the full vendored layout (skills +
    hooks + settings). Other agents get guidance only (plugin path model).
    The briefing block lands in `briefing_target`. When Claude is one of
    the installed agents and the briefing lives outside CLAUDE.md, CLAUDE.md
    also gets a lightweight @ import pointer to that home.
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
    writes.append(PlannedWrite("shared", "append", target / briefing_target, "guidance"))
    if "claude" in agents and briefing_target in CLAUDE_IMPORTABLE_TARGETS:
        writes.append(PlannedWrite("claude", "append", target / "CLAUDE.md", "guidance"))
    for agent in agents:
        shim = _load_agent_shim(templates, agent)
        is_local = agent in local_skills_agents
        if is_local and shim.skills:
            for rel in _iter_skill_assets(templates / "skills", agent):
                writes.append(PlannedWrite(agent, "write", target / shim.skills.target / rel, "harness"))
        if is_local:
            for file in shim.files:
                writes.append(PlannedWrite(agent, "write", target / file.target, "harness"))
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
    briefing_target: str = DEFAULT_BRIEFING_TARGET,
) -> list[PlannedWrite]:
    """Compute the list of writes the upgrader will perform.

    Project-state `.game-of-cards/` files are labeled with the ownership-aware
    `create` / `unchanged` / `preserved` actions rather than the blanket
    `sync`, so a dry-run truthfully reports which authored files will be
    preserved on the real run vs which absent files will be scaffolded.
    """

    classifications = _user_owned_classifications(target, templates)
    config_root = target / ".game-of-cards"

    writes: list[PlannedWrite] = []
    for write in _plan_writes(
        target,
        templates,
        agents,
        local_skills_agents=local_skills_agents,
        briefing_target=briefing_target,
    ):
        if write.path.name == "log.md":
            continue
        if write.category == "project-state":
            try:
                rel = write.path.relative_to(config_root)
            except ValueError:
                rel = None
            if rel is not None and rel in classifications:
                writes.append(
                    PlannedWrite(write.owner, classifications[rel], write.path, write.category)
                )
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
    print(f"goc {command} (dry-run) — agents: {agents_str} — {len(writes)} writes planned")
    for cat_key, cat_label in _CATEGORY_LABELS:
        cat_writes = [w for w in writes if w.category == cat_key]
        if not cat_writes:
            continue
        print(f"\n{cat_label}:")
        for write in cat_writes:
            print(f"  {write.owner:6s} {write.action:6s} {write.path.relative_to(target)}")


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


# Files under `.game-of-cards/` that are "evolving" — goc ships real content
# that may change across versions, AND the consumer is allowed to customize.
# On upgrade the engine still preserves the consumer's bytes (deterministic
# safety), but the divergence report tags these so the `upgrade` skill knows
# to offer a 2-way LLM reconcile rather than just "kept yours".
# Every other shipped file is "user-owned" (a content stub or workflow hook
# whose template ships permanently blank).
_EVOLVING_USER_OWNED_FILES = frozenset({Path("README.md"), Path("config.yaml")})

# Sentinel marker the `upgrade` skill greps for in stdout to extract the
# JSON divergence report. Single-line JSON on the line immediately after.
_DIVERGENCE_REPORT_MARKER = "GoC project-state divergence report (JSON):"


def _classify_user_owned_file(template: Path, dest: Path) -> str:
    """Classify a `.game-of-cards/` file against its shipped template.

    Returns one of: `create` (destination absent), `unchanged` (byte-identical),
    or `preserved` (diverged — never overwrite on upgrade).
    """

    if not dest.exists():
        return "create"
    try:
        return "unchanged" if dest.read_bytes() == template.read_bytes() else "preserved"
    except OSError:
        return "preserved"


def _user_owned_classifications(target: Path, templates: Path) -> dict[Path, str]:
    """Map each shipped `.game-of-cards/<rel>` to its `create`/`unchanged`/`preserved` label."""

    src = templates / "game_of_cards"
    result: dict[Path, str] = {}
    if not src.exists():
        return result
    for asset in src.rglob("*"):
        if asset.is_dir() or "__pycache__" in asset.parts:
            continue
        rel = asset.relative_to(src)
        dest = target / ".game-of-cards" / rel
        result[rel] = _classify_user_owned_file(asset, dest)
    return result


def _emit_divergence_report(
    classifications: dict[Path, str], templates_src: Path
) -> None:
    """Print a single-line JSON divergence report after a sentinel marker.

    The `upgrade` skill parses the JSON on the line immediately after the
    marker to drive the reconciliation pass. Safety does NOT depend on this
    report — the engine has already preserved every diverged file before the
    report is emitted.
    """

    files = []
    for rel in sorted(classifications):
        ownership = "evolving" if rel in _EVOLVING_USER_OWNED_FILES else "user-owned"
        files.append(
            {
                "path": rel.as_posix(),
                "status": classifications[rel],
                "ownership": ownership,
            }
        )
    payload = {
        "version": 1,
        "templates_root": str(templates_src),
        "files": files,
    }
    print(_DIVERGENCE_REPORT_MARKER)
    print(json.dumps(payload))


def _sync_game_of_cards_config(
    target: Path,
    templates: Path,
    *,
    migrate_legacy: bool = False,
    emit_report: bool = False,
) -> None:
    """Sync `.game-of-cards/` assets without ever overwriting authored content.

    Per file: absent → scaffold from template; identical to template → no-op
    (existing bytes left in place); diverged → preserve, do NOT overwrite.
    This is the unconditional safety guarantee — it holds for every consumer
    (CI runs, headless cron, agent sessions) regardless of whether the
    `upgrade` skill is in the loop.

    When `emit_report=True`, after the sync prints a sentinel-marked JSON
    divergence report the `upgrade` skill consumes to drive its reconciliation
    pass (2-way reconcile for evolving files, confirmation for user-owned).
    """

    config_dst = target / ".game-of-cards"
    config_dst.mkdir(parents=True, exist_ok=True)
    config_file = config_dst / "config.yaml"
    legacy_config = target / ".claude" / "deck-config.yaml"
    if migrate_legacy and not config_file.exists() and legacy_config.exists():
        shutil.copy2(legacy_config, config_file)

    src = templates / "game_of_cards"
    classifications = _user_owned_classifications(target, templates)
    for rel, status in classifications.items():
        if status != "create":
            continue
        dest = config_dst / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, dest)

    if emit_report:
        _emit_divergence_report(classifications, src)


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


def skill_for_agent(
    skill_name: str,
    agent: str,
    *,
    supported_agents: tuple[str, ...] = SUPPORTED_AGENTS,
    plugin_only_agents: tuple[str, ...] = PLUGIN_ONLY_AGENTS,
) -> bool:
    """True if a skill named `skill_name` should be installed for `agent`.

    Skills whose directory name starts with `<other_agent>-` are agent-specific
    complements (e.g. `claude-kickoff` only ships under the claude harness).
    Skills with no agent prefix are host-agnostic and apply to every agent.
    `plugin_only_agents` (e.g. `openclaw`) ship skills via plugin payload, not
    via `goc install`; their prefixes are filtered out of every local install.
    """

    for other in (*supported_agents, *plugin_only_agents):
        if other != agent and skill_name.startswith(f"{other}-"):
            return False
    return True


def _iter_skill_assets(skills_src: Path, agent: str) -> list[Path]:
    """Return bundled skill assets relative to the skill tree root, filtered for `agent`."""

    paths: list[Path] = []
    for skill_dir in sorted(p for p in skills_src.iterdir() if p.is_dir()):
        if not skill_for_agent(skill_dir.name, agent):
            continue
        for asset in skill_dir.rglob("*"):
            if asset.is_dir() or "__pycache__" in asset.parts:
                continue
            paths.append(asset.relative_to(skills_src))
    return paths


def _sync_skill_tree(
    templates: Path,
    skills_dst: Path,
    agent: str,
    *,
    replace_skills: bool = False,
    codex_frontmatter: bool = False,
) -> None:
    """Copy GoC skills into a runtime-specific skill root, filtered for `agent`.

    `replace_skills=True` wipes only the eligible (current-GoC-template) skill
    directories before recopying them, so a refresh picks up template edits.
    Non-eligible directories are left untouched — `.claude/skills/` may hold
    user-owned skills (or skills from other tools) that GoC does not own and
    must never delete as a side effect of upgrade.
    """

    skills_src = templates / "skills"
    skills_dst.mkdir(parents=True, exist_ok=True)
    eligible = {
        p.name for p in skills_src.iterdir() if p.is_dir() and skill_for_agent(p.name, agent)
    }
    if replace_skills:
        for name in sorted(eligible):
            target = skills_dst / name
            if target.exists():
                shutil.rmtree(target)
    for asset in skills_src.rglob("*"):
        if asset.is_dir() or "__pycache__" in asset.parts:
            continue
        rel = asset.relative_to(skills_src)
        if rel.parts[0] not in eligible:
            continue
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
    text, newline = _read_text_keep_newline(target)
    pattern = re.compile(rf"{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n?", re.DOTALL)
    if pattern.search(text):
        _write_text_keep_newline(target, pattern.sub(lambda _: block, text), newline)
        return
    _write_text_keep_newline(target, text.rstrip() + "\n\n" + block, newline)


def _append_precommit_hook(target: Path) -> None:
    """Append the `goc validate` hook to `.pre-commit-config.yaml` (creating it)."""

    if not (target.parent / ".git").exists():
        return
    if not target.exists():
        target.write_text("repos:\n" + PRE_COMMIT_HOOK)
        return
    text, newline = _read_text_keep_newline(target)
    if "id: goc-validate" in text:
        return
    if not text.endswith("\n"):
        text += "\n"
    _write_text_keep_newline(target, text + PRE_COMMIT_HOOK, newline)


def _sync_methodology_blocks(
    target: Path,
    templates: Path,
    briefing_target: str,
    *,
    agents: tuple[str, ...] = (),
) -> None:
    """Write the marker-bounded briefing block into the chosen home file only.

    The briefing has exactly one home — AGENTS.md, CLAUDE.md, or CLAUDE.local.md
    — set by the caller (`goc install --briefing-target …`, default AGENTS.md).
    If Claude is installed and the home is not CLAUDE.md, maintain a minimal
    CLAUDE.md @ import so Claude Code can load the chosen home.
    """

    if briefing_target == "CLAUDE.md":
        _strip_claude_import(target / "CLAUDE.md")
    body = _briefing_body(templates, briefing_target)
    _append_marker_block(
        target / briefing_target,
        body,
        header=BRIEFING_HEADERS[briefing_target],
    )
    if "claude" in agents:
        _sync_claude_import(target, briefing_target)


def _sync_agent_harness(
    target: Path,
    templates: Path,
    agent: str,
    *,
    replace_skills: bool = False,
    guidance_only: bool = False,
) -> None:
    """Copy and render one agent's shim from its template manifest.

    Skills, hook files, and settings.json are written when `guidance_only=False`;
    the plugin path model uses `guidance_only=True` to skip them. The briefing
    block (AGENTS.md / CLAUDE.md / CLAUDE.local.md) is NOT written here — it
    flows through `_sync_methodology_blocks` so a single chosen home is honored
    regardless of which agents are installed.
    """

    shim = _load_agent_shim(templates, agent)
    if guidance_only:
        return
    if shim.skills:
        _sync_skill_tree(
            templates,
            target / shim.skills.target,
            agent,
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
    "Use for CI environments without plugin support, or repos that fork/template GoC. "
    "Requires a pipx install of game-of-cards — refused when running under the GoC plugin."
)
KEEP_LOCAL_SKILLS_HELP = (
    "Preserve the existing vendored skills layout and refresh templates in place. "
    "Skips the migration to the plugin path. "
    "Use in scripted contexts (CI cron, etc.) to opt out of migration. "
    "Requires a pipx install of game-of-cards — refused when running under the GoC plugin."
)
BRIEFING_TARGET_HELP = (
    "File where the GoC briefing block lives. One of: AGENTS.md (default; cross-runtime visible, "
    "with CLAUDE.md @ import when Claude is installed), CLAUDE.md (Claude-only; cross-runtime "
    "visibility lost), CLAUDE.local.md (gitignored, with CLAUDE.md @ import when Claude is installed). "
    "On upgrade, omit to detect from the existing install; supplying it migrates the briefing home."
)

_PLUGIN_INSTALL_CMDS = (
    "  /plugin marketplace add zauberzeug/game-of-cards\n"
    "  /plugin install game-of-cards@game-of-cards"
)


def _confirm(prompt: str, *, default: bool = False) -> bool:
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


_SKILLS_SOURCE_VALUES = ("plugin", "vendored", "auto")


def _write_skills_source(target: Path, value: str) -> None:
    """Set the `skills_source:` key in `.game-of-cards/config.yaml`.

    Append the key if missing; replace the value if a (commented or active)
    line already exists. Treats the config file as line-oriented text to
    avoid round-tripping the whole YAML — preserves comments and ordering
    that a parser-then-dump would lose.
    """
    if value not in _SKILLS_SOURCE_VALUES:
        raise ValueError(f"invalid skills_source value: {value!r}")
    config_path = target / ".game-of-cards" / "config.yaml"
    if not config_path.exists():
        return
    text = config_path.read_text()
    pattern = re.compile(r"^[ \t]*#?[ \t]*skills_source[ \t]*:.*$", re.MULTILINE)
    replacement = f"skills_source: {value}"
    if pattern.search(text):
        new_text = pattern.sub(lambda _: replacement, text, count=1)
    else:
        sep = "" if text.endswith("\n") else "\n"
        new_text = f"{text}{sep}\n{replacement}\n"
    config_path.write_text(new_text)


def install(
    dry_run: bool = False,
    agent_specs: tuple[str, ...] = (),
    claude_flag: bool = False,
    codex_flag: bool = False,
    local_skills: bool = False,
    briefing_target: str = DEFAULT_BRIEFING_TARGET,
) -> None:
    """Scaffold a fresh repo with the shared GoC files and selected harnesses."""

    _validate_briefing_target(briefing_target)
    if local_skills and _is_plugin_context():
        print(_LOCAL_SKILLS_PLUGIN_REFUSAL, file=sys.stderr)
        sys.exit(2)

    target = Path.cwd().resolve()
    deck_dir = target / ".game-of-cards" / "deck"
    templates = _templates_root()
    supported_agents = _registered_agents(templates)

    explicit_agents = _agent_override_requested(agent_specs, claude=claude_flag, codex=codex_flag)
    if not explicit_agents and _is_openclaw_plugin_context():
        # OpenClaw ships skills/hooks via its plugin runtime and has no harness
        # surface, so the default is no harness — never the Claude fallback, and
        # never auto-detecting Codex from the AGENTS.md briefing this very install
        # writes. Explicit --agents still overrides below.
        detected_agents: tuple[str, ...] = ()
        default_agents: tuple[str, ...] = ()
    else:
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

    writes = _plan_writes(
        target,
        templates,
        agents,
        local_skills_agents=local_skills_agents,
        briefing_target=briefing_target,
    )
    if dry_run:
        _print_plan("install", target, writes, agents)
        return

    existing_dir = _find_installed_deck_dir(target)
    if existing_dir is not None:
        existing = _detect_existing(existing_dir)
        rel = existing_dir.relative_to(target)
        print(f"already installed ({rel}/.goc-version → {existing})", file=sys.stderr)
        print("Run `goc upgrade` to re-sync templates.", file=sys.stderr)
        sys.exit(1)

    for agent in agents:
        guidance_only = agent not in local_skills_agents
        _sync_agent_harness(target, templates, agent, guidance_only=guidance_only)

    deck_dir.mkdir(parents=True, exist_ok=True)
    (deck_dir / "log.md").write_text("# Deck Log\n\nAppend deck-level events here (sprint notes, schema bumps, etc.).\n")
    (deck_dir / ".goc-version").write_text(__version__ + "\n")

    _sync_game_of_cards_config(target, templates)

    # Pin skills_source so future `goc upgrade` runs (and `goc validate`)
    # know which mode this repo is in without re-detecting host state.
    chosen_source = "vendored" if "claude" in local_skills_agents else "plugin"
    _write_skills_source(target, chosen_source)

    _sync_methodology_blocks(target, templates, briefing_target, agents=agents)

    _append_precommit_hook(target / ".pre-commit-config.yaml")

    if agents:
        source = ""
        if not explicit_agents:
            source = " (auto-detected)" if detected_agents else " (default)"
        print(f"goc {__version__} installed for agents: {','.join(agents)}{source}.")
    else:
        print(f"goc {__version__} installed (no agent harness; OpenClaw provides skills via its plugin).")
    print(
        'Next: ask your LLM agent to "expand the deck" — it audits the repo and files initial cards. '
        'Or "create a card for X" if you already know the first change you want to make.'
    )

    if "claude" in agents and "claude" not in local_skills_agents:
        if _detect_claude_code():
            print(
                "GoC plugin: to enable skills and hooks, ask the user to confirm then run:\n"
                + _PLUGIN_INSTALL_CMDS
            )
        else:
            print(
                "Next steps for Claude Code users — install the GoC plugin (one-time per machine):\n"
                + _PLUGIN_INSTALL_CMDS
            )

    print(
        "Engine/debug: `goc` shows the queue; `goc validate` checks cards. "
        "Run `goc upgrade` later to sync template updates."
    )


def _resolve_upgrade_briefing_target(
    target: Path,
    *,
    explicit_target: str | None,
    dry_run: bool,
) -> str:
    """Decide which file should hold the briefing block on upgrade.

    Resolution order:
      1. `explicit_target` (from --briefing-target on the upgrade command).
      2. The single existing GoC marker block on disk, if exactly one is found.
      3. A multi-block legacy install — prompt the user to pick one, strip the
         others; in dry-run, default to AGENTS.md without prompting.
      4. No marker blocks at all — fall back to AGENTS.md.
    """

    if explicit_target is not None:
        _validate_briefing_target(explicit_target)
        return explicit_target

    found = _detect_briefing_targets_on_disk(target)
    if len(found) == 1:
        return found[0]
    if len(found) == 0:
        return DEFAULT_BRIEFING_TARGET
    # len(found) >= 2: legacy dual-write install — pick one home, strip others.
    if dry_run:
        return found[0]
    print(
        f"This repo has GoC marker blocks in multiple files: {', '.join(found)}. "
        "GoC now keeps the briefing in exactly one home — pick one and the rest will be stripped."
    )
    print("Briefing-target options:")
    for idx, candidate in enumerate(found, start=1):
        print(f"  {idx}) {candidate}")
    if sys.stdin.isatty():
        raw = input(f"Pick [1-{len(found)}, default 1]: ").strip()
    else:
        try:
            raw = sys.stdin.readline().strip()
        except (EOFError, OSError):
            raw = ""
    if not raw:
        choice = found[0]
    else:
        try:
            choice = found[int(raw) - 1]
        except (ValueError, IndexError):
            print(f"goc: error: invalid selection {raw!r}; aborting upgrade.", file=sys.stderr)
            sys.exit(2)
    print(f"Briefing target set to {choice}; stripping GoC blocks from the others.")
    return choice


def upgrade(
    dry_run: bool = False,
    agent_specs: tuple[str, ...] = (),
    claude_flag: bool = False,
    codex_flag: bool = False,
    keep_local_skills: bool = False,
    briefing_target: str | None = None,
) -> None:
    """Re-sync skill templates, AGENTS.md, and CLAUDE.md sections from the installed package version."""

    if keep_local_skills and _is_plugin_context():
        print(_KEEP_LOCAL_SKILLS_PLUGIN_REFUSAL, file=sys.stderr)
        sys.exit(2)

    target = Path.cwd().resolve()
    templates = _templates_root()
    supported_agents = _registered_agents(templates)

    agents_explicit = _agent_override_requested(agent_specs, claude=claude_flag, codex=codex_flag)
    if agents_explicit:
        default_agents: tuple[str, ...] = DEFAULT_AGENTS
    elif _is_openclaw_plugin_context():
        # Mirror install: OpenClaw has no harness surface, so upgrade refreshes
        # only the shared scaffold + AGENTS.md briefing, never the Claude default.
        default_agents = ()
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
        print("no existing install detected — run `goc install` first.", file=sys.stderr)
        sys.exit(1)
    existing = _detect_existing(deck_dir)

    resolved_briefing = _resolve_upgrade_briefing_target(
        target,
        explicit_target=briefing_target,
        dry_run=dry_run,
    )
    legacy_briefings_to_strip = tuple(
        candidate for candidate in _detect_briefing_targets_on_disk(target) if candidate != resolved_briefing
    )

    # Claude skill source — config wins; --keep-local-skills forces vendored;
    # absent config + no host plugin falls back to vendored for legacy compat.
    from goc.engine import effective_skills_source  # local import: engine→install cycle

    if keep_local_skills:
        claude_skills_mode = "vendored"
    elif "claude" in agents:
        claude_skills_mode = effective_skills_source()
    else:
        claude_skills_mode = "vendored"

    # Detect leftover vendored layout (relevant only when the new mode is plugin —
    # then the layout is stale and the user may want it cleaned up).
    claude_has_vendored = False
    if "claude" in agents:
        claude_shim = _load_agent_shim(templates, "claude")
        claude_has_vendored = bool(claude_shim.skills and (target / claude_shim.skills.target).is_dir())

    needs_vendored_cleanup = claude_skills_mode == "plugin" and claude_has_vendored

    local_skills_agents: frozenset[str]
    if claude_skills_mode == "vendored":
        local_skills_agents = frozenset(agents)
    else:
        # plugin mode: claude skills come from the runtime plugin; non-claude
        # agents (codex) still vendor.
        local_skills_agents = frozenset(a for a in agents if a != "claude")

    pending_cleanup = needs_vendored_cleanup and not dry_run
    pending_briefing_migration = bool(legacy_briefings_to_strip) and not dry_run

    if (
        existing == __version__
        and not dry_run
        and not agents_explicit
        and not pending_cleanup
        and not keep_local_skills
        and not pending_briefing_migration
        and briefing_target is None
    ):
        print(f"already at goc {__version__} — nothing to do.")
        return

    if dry_run:
        notes: list[str] = []
        if needs_vendored_cleanup:
            notes.append("will offer cleanup of leftover .claude/skills/ (plugin mode)")
        if legacy_briefings_to_strip:
            notes.append(
                f"briefing target → {resolved_briefing}; will strip blocks from {', '.join(legacy_briefings_to_strip)}"
            )
        suffix = f" ({'; '.join(notes)})" if notes else ""
        print(f"goc upgrade would sync {existing} → {__version__}{suffix}")
        _print_plan(
            "upgrade",
            target,
            _plan_upgrade_writes(
                target,
                templates,
                agents,
                local_skills_agents=local_skills_agents,
                briefing_target=resolved_briefing,
            ),
            agents,
        )
        return

    # Plugin-mode + leftover vendored layout: explicit, opt-in cleanup.
    # Decline path is a no-op — never re-vendor, never touch user skills.
    if needs_vendored_cleanup:
        print(
            "This repo is configured for plugin-mode skills (skills_source: plugin)\n"
            "but a leftover .claude/skills/ from a prior vendored install was found.\n"
            "Cleanup removes GoC-managed skill directories, GoC hook files, and\n"
            "GoC entries in .claude/settings.json. Non-GoC skills in .claude/skills/\n"
            "are preserved."
        )
        confirmed = _confirm("Remove leftover vendored layout?", default=False)
        if confirmed:
            _strip_claude_vendored_harness(target, templates)
        else:
            print("Skipping cleanup; leftover vendored layout preserved as-is.")

    for agent in agents:
        guidance_only = agent not in local_skills_agents
        replace = agent in local_skills_agents
        _sync_agent_harness(target, templates, agent, guidance_only=guidance_only, replace_skills=replace)

    _sync_game_of_cards_config(target, templates, migrate_legacy=True, emit_report=True)
    # Pin the resolved mode so future runs don't re-detect host state.
    if "claude" in agents:
        _write_skills_source(target, claude_skills_mode)

    for stale in legacy_briefings_to_strip:
        _strip_goc_block(target / stale)
    _sync_methodology_blocks(target, templates, resolved_briefing, agents=agents)

    (deck_dir / ".goc-version").write_text(__version__ + "\n")

    if agents:
        print(f"goc upgrade complete for agents: {','.join(agents)} — {existing} → {__version__}.")
    else:
        print(f"goc upgrade complete (no agent harness; OpenClaw plugin path) — {existing} → {__version__}.")
    if legacy_briefings_to_strip:
        print(f"Briefing target is now {resolved_briefing}; stripped GoC blocks from {', '.join(legacy_briefings_to_strip)}.")
    print("Next: re-run goc validate to confirm cards parse against the new schema.")


if __name__ == "__main__":
    install()
