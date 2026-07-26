"""Prove the OpenClaw porter breaks quoted description scalars.

Every shipped ``openclaw-plugin/skills/*/SKILL.md`` must carry frontmatter a
strict YAML loader accepts. The porter appends its tool-served fetch hint to
the description *line*; when the source description is a double-quoted scalar
(pull-card, next-card), the hint lands after the closing quote — trailing
content no YAML parser tolerates on a quoted scalar.

PyYAML is not a project dependency, so the check is a self-contained scan of
the one YAML rule at stake: a value that opens with a quote must close with a
matching unescaped quote at end-of-line, with nothing after it. Exits nonzero
while any shipped skill violates that.
"""

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


def quoted_scalar_violation(value: str) -> str | None:
    """Return a description of the YAML violation, or None if clean."""
    if not value or value[0] not in {'"', "'"}:
        return None  # plain scalar — not this defect's shape
    quote = value[0]
    i = 1
    while i < len(value):
        ch = value[i]
        if quote == '"' and ch == "\\":
            i += 2
            continue
        if ch == quote:
            if quote == "'" and value[i + 1 : i + 2] == "'":
                i += 2  # '' escape inside single-quoted scalar
                continue
            trailing = value[i + 1 :].strip()
            if trailing:
                return f"content after closing quote: {trailing[:60]!r}"
            return None
        i += 1
    return "quoted scalar never closes"


def main() -> int:
    skills_dir = _repo_root() / "openclaw-plugin" / "skills"
    failures = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        frontmatter = text.split("---", 2)[1]
        for lineno, line in enumerate(frontmatter.splitlines(), start=1):
            if not line.startswith("description:"):
                continue
            value = line[len("description:") :].strip()
            problem = quoted_scalar_violation(value)
            rel = skill_md.relative_to(_repo_root())
            if problem:
                failures.append(f"{rel}:{lineno}: {problem}")
                print(f"[FAIL] {rel}:{lineno}: {problem}")
            else:
                print(f"[ ok ] {rel}")
    if failures:
        print(f"\n{len(failures)} shipped skill(s) have unparseable frontmatter")
        return 1
    print("\nall shipped openclaw skill descriptions are strict-YAML clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
