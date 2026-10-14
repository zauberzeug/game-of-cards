"""Reproduce: the pattern-generalization Stop hook crashes on a config or
transcript that does not decode.

Runs the shipped hook template the way Claude Code does (JSON on stdin) in
three scratch projects:

1. Hook off (the default), config.yaml holding one Latin-1 byte (0xE9).
   Python's UTF-8 mode is forced, so the byte does not decode on any host.
2. Hook off, config.yaml copied from the shipped template, with Python's
   default encoding forced to ASCII (LC_ALL=C, PYTHONUTF8=0) as the stand-in
   for a host whose default encoding is not UTF-8. The template's em dash
   does not decode there.
3. Hook on (an ASCII config), a UTF-8 transcript whose last turn used Edit
   and whose prompt holds an emoji, under the same ASCII default encoding.

Expected: cases 1 and 2 exit 0 (the hook is off), case 3 exits 2 with the
reminder. Exits non-zero while any case does otherwise.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
HOOK = ROOT / "goc" / "templates" / "hooks" / "pattern_generalization_check.py"
TEMPLATE_CONFIG = ROOT / "goc" / "templates" / "game_of_cards" / "config.yaml"

UTF8_MODE = {"PYTHONUTF8": "1"}
# LC_ALL=C names the C locale; PYTHONUTF8=0 and PYTHONCOERCECLOCALE=0 stop
# Python from swapping it for UTF-8, so the default encoding is ASCII.
ASCII_DEFAULT = {"LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}


def _project(root: Path, name: str, config: bytes) -> Path:
    project = root / name
    (project / ".game-of-cards").mkdir(parents=True)
    (project / ".game-of-cards" / "config.yaml").write_bytes(config)
    return project


def _transcript(project: Path) -> Path:
    lines = [
        {"type": "user", "message": {"role": "user", "content": "fix the typo \U0001F601"}},
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "name": "Edit", "input": {}}],
            },
        },
    ]
    path = project / "transcript.jsonl"
    text = "".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines)
    path.write_bytes(text.encode("utf-8"))
    return path


def _run(project: Path, transcript: Path | None, env: dict[str, str]):
    payload = {
        "hook_event_name": "Stop",
        "stop_hook_active": False,
        "cwd": str(project),
        "transcript_path": str(transcript) if transcript else "",
    }
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload).encode("ascii"),
        capture_output=True,
        cwd=project,
        env={**os.environ, **env},
    )


def main() -> int:
    template = TEMPLATE_CONFIG.read_bytes()
    print("shipped config.yaml template under common Windows code pages:")
    for codec in ("cp1252", "cp932", "cp936", "cp949", "cp950"):
        try:
            template.decode(codec)
            verdict = "decodes"
        except UnicodeDecodeError as exc:
            verdict = f"does not decode ({exc.reason} at byte {exc.start})"
        print(f"  {codec}: {verdict}")
    print()

    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        on = _project(root, "on", b"pattern_generalization_check: true\n")
        cases = [
            (
                "hook off, config.yaml with one Latin-1 byte, UTF-8 mode",
                _project(root, "latin1", b"layer_2_project_dod: []\n# owner: Ren\xe9\n"),
                None,
                UTF8_MODE,
                0,
            ),
            (
                "hook off, shipped template config.yaml, ASCII default encoding",
                _project(root, "template", template),
                None,
                ASCII_DEFAULT,
                0,
            ),
            (
                "hook on, UTF-8 transcript with an emoji, ASCII default encoding",
                on,
                _transcript(on),
                ASCII_DEFAULT,
                2,
            ),
        ]
        for label, project, transcript, env, expected in cases:
            proc = _run(project, transcript, env)
            stderr = proc.stderr.decode("utf-8", "replace").strip()
            last = stderr.splitlines()[-1] if stderr else ""
            ok = proc.returncode == expected and (
                expected != 2 or "pattern-check" in stderr
            )
            failures += not ok
            detail = f" ({last})" if "Error" in last else ""
            print(
                f"[{'OK' if ok else 'FAIL'}] {label}: "
                f"exit {proc.returncode}, expected {expected}{detail}"
            )

    print()
    if failures:
        print(f"FAIL: {failures} of {len(cases)} cases crash the Stop hook.")
        return 1
    print("OK: the hook exits 0 when off and reminds when on, whatever the bytes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
