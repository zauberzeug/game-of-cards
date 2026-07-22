"""Prove that render_json(slim=True) omits `worker` and `draft`.

Builds one in-memory card that is claimed (worker set) and one draft
scaffold, renders both full and slim JSON, and asserts the slim records
carry the same claim-ownership and draft-visibility fields the full
records do. Exits non-zero while the defect fires; exits zero once the
slim record includes both fields.
"""

import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402


def _card(tmpdir: Path, title: str, extra_frontmatter: str) -> "engine.Card":
    card_dir = tmpdir / title
    card_dir.mkdir(parents=True)
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        "summary: \"probe card\"\n"
        "status: open\n"
        "stage: null\n"
        "contribution: medium\n"
        "created: 2026-07-22\n"
        "closed_at: null\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [ ] real criterion\n"
        f"{extra_frontmatter}"
        "---\n\n"
        f"# {title}\n",
        encoding="utf-8",
    )
    return engine.load_card(card_dir)


def main() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        claimed = _card(
            tmp,
            "claimed-card",
            'worker: {who: "alice", where: feature/x}\n',
        )
        draft = _card(tmp, "draft-card", "draft: true\n")
        cards = [claimed, draft]

        full = {r["title"]: r for r in json.loads(engine.render_json(cards))}
        slim = {r["title"]: r for r in json.loads(engine.render_json(cards, slim=True))}

    print("full record fields (claimed-card):",
          f"worker={full['claimed-card'].get('worker')!r}",
          f"draft={full['draft-card'].get('draft')!r}")
    print("slim record keys:", sorted(slim["claimed-card"].keys()))

    failures = []
    if "worker" not in slim["claimed-card"]:
        failures.append("slim record omits `worker` (full record has "
                        f"{full['claimed-card']['worker']!r})")
    elif slim["claimed-card"]["worker"] != full["claimed-card"]["worker"]:
        failures.append("slim `worker` disagrees with full record")
    if "draft" not in slim["draft-card"]:
        failures.append("slim record omits `draft` (full record has "
                        f"{full['draft-card']['draft']!r})")
    elif slim["draft-card"]["draft"] is not True:
        failures.append("slim `draft` disagrees with full record")
    for key in ("worker", "draft"):
        if key in slim["claimed-card"] and key not in engine.SLIM_JSON_KEYS:
            failures.append(f"SLIM_JSON_KEYS (the --slim help-text contract) omits `{key}`")

    if failures:
        for f in failures:
            print(f"[FAIL] {f}")
        return 1
    print("[OK] slim records expose worker and draft, matching the full record")
    return 0


if __name__ == "__main__":
    sys.exit(main())
