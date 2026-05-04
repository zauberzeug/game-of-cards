import sys
from pathlib import Path

import yaml


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


def main() -> int:
    workflow_path = _repo_root() / ".github" / "workflows" / "pull-card.yml"
    workflow_text = workflow_path.read_text()
    workflow = yaml.load(workflow_text, Loader=yaml.BaseLoader)

    errors: list[str] = []

    permissions = workflow.get("permissions") or {}
    if permissions.get("id-token") != "write":
        errors.append("permissions.id-token is not write")

    schedule = (workflow.get("on") or {}).get("schedule") or []
    crons = [
        item.get("cron")
        for item in schedule
        if isinstance(item, dict) and item.get("cron")
    ]
    if crons != ["*/30 * * * *"]:
        errors.append(f"schedule cron is {crons!r}, expected ['*/30 * * * *']")

    if "Check schedule gate" in workflow_text:
        errors.append("workflow still contains the old schedule gate")

    if errors:
        print("defect present: pull-card workflow is not ready to execute every 30 minutes")
        for error in errors:
            print(f"- {error}")
        return 1

    print("ok: pull-card workflow has OIDC permission and a native 30-minute cron")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
