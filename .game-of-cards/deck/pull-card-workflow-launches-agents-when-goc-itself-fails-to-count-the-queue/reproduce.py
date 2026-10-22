"""Reproduce: pull-card.yml's queue-count steps fail open when goc fails.

`.github/workflows/pull-card.yml` gates the agent launch and the self
re-trigger on two count steps (`Check autonomous queue`, `Re-check queue`)
whose bodies run

    count="$(uv run goc ... --json | jq 'length')"

GitHub runs a `run:` step that names no `shell:` as `bash -e {0}`, without
`pipefail`. The pipeline's status is then jq's, and jq given empty input
prints nothing and exits 0. So when goc exits non-zero the count is empty,
the step succeeds, and `count != '0'` launches the agent.

This script runs every step whose output a later step's `if:` reads, the way
GitHub would run it: under the shell the step resolves to (its own `shell:`,
else the job's then the workflow's `defaults.run.shell`, else the runner
default), with `uv` and `goc` stand-ins first on PATH and a scratch
GITHUB_OUTPUT.

- Controls: the stand-ins print `[]`, then a two-card array, and exit 0. The
  step must succeed and report 0, then 2. If it does not, the harness is not
  running the step faithfully and nothing is concluded.
- Failure: the stand-ins exit 2, the way a broken engine does. The step
  fails closed if it exits non-zero (the steps reading its output then skip
  on their implicit `success()`, unless their `if:` opts out with
  `always()` / `failure()` / `cancelled()` or the step sets
  `continue-on-error`), or if it reports exactly 0.

Exit 0: every count step fails closed.
Exit 1: some count step fails open (the defect).
Exit 2: inconclusive: the workflow shape, a control, or a tool did not hold.

Usage: python reproduce.py [--workflow PATH]
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
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
sys.path.insert(0, str(ROOT))

from goc._vendor import yaml_lite  # noqa: E402

# The command GitHub runs for each `shell:` on a Linux runner. `None` is the
# unspecified default, which is NOT what an explicit `shell: bash` runs.
SHELLS = {
    None: ["bash", "-e", "{0}"],
    "bash": ["bash", "--noprofile", "--norc", "-eo", "pipefail", "{0}"],
    "sh": ["sh", "-e", "{0}"],
}

# A status-check function in an `if:` stops GitHub from ANDing in the implicit
# `success()`, so the step runs even after the step it reads from failed.
RUNS_AFTER_FAILURE = re.compile(r"\b(always|failure|cancelled)\s*\(")
OUTPUT_REF = re.compile(r"\bsteps\.([\w-]+)\.outputs\.([\w-]+)")

# Inherited variables that would change how the step's shell starts.
SHELL_STARTUP_VARS = ("BASH_ENV", "ENV", "SHELLOPTS", "BASHOPTS")

STAND_IN = """#!/bin/sh
case "$REPRODUCE_STAND_IN_MODE" in
  zero) echo '[]' ;;
  two) echo '[{"title": "a"}, {"title": "b"}]' ;;
  *) echo "stand-in: simulated goc failure" >&2; exit 2 ;;
esac
"""


class Inconclusive(Exception):
    pass


def resolve_shell(workflow: dict, job: dict, step: dict):
    job_run = (job.get("defaults") or {}).get("run") or {}
    workflow_run = (workflow.get("defaults") or {}).get("run") or {}
    for scope in (step, job_run, workflow_run):
        if scope.get("shell"):
            return scope["shell"]
    return None


def shell_argv(shell, script: Path) -> list[str]:
    if shell in SHELLS:
        template = SHELLS[shell]
    elif isinstance(shell, str) and "{0}" in shell:
        template = shlex.split(shell)
    else:
        raise Inconclusive(f"cannot model `shell: {shell}`")
    return [part.replace("{0}", str(script)) for part in template]


def read_outputs(path: Path) -> dict[str, str]:
    """Parse a GITHUB_OUTPUT file: `name=value` and `name<<DELIM` entries."""
    outputs: dict[str, str] = {}
    lines = iter(path.read_text().splitlines())
    for line in lines:
        eq, heredoc = line.find("="), line.find("<<")
        if heredoc != -1 and (eq == -1 or heredoc < eq):
            delim, body = line[heredoc + 2:], []
            for body_line in lines:
                if body_line == delim:
                    break
                body.append(body_line)
            outputs[line[:heredoc]] = "\n".join(body)
        elif eq != -1:
            outputs[line[:eq]] = line[eq + 1:]
    return outputs


def run_step(body: str, argv_for, mode: str, tmp: Path, stand_ins: Path):
    script, output, work = tmp / "step.sh", tmp / "github_output", tmp / "work"
    script.write_text(body)
    output.write_text("")
    work.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k not in SHELL_STARTUP_VARS}
    env["PATH"] = f"{stand_ins}{os.pathsep}{env.get('PATH', '')}"
    env["GITHUB_OUTPUT"] = str(output)
    env["REPRODUCE_STAND_IN_MODE"] = mode
    proc = subprocess.run(
        argv_for(script), cwd=work, env=env, capture_output=True, text=True
    )
    return proc, read_outputs(output)


def check(path: Path) -> int:
    for tool in ("bash", "jq"):
        if shutil.which(tool) is None:
            raise Inconclusive(f"`{tool}` is not on PATH")
    try:
        workflow = yaml_lite.safe_load(path.read_text())
    except yaml_lite.ParseError as exc:
        raise Inconclusive(f"yaml_lite cannot parse {path}: {exc}") from exc

    open_steps = []
    checked = 0
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        stand_ins = tmp / "stand-ins"
        stand_ins.mkdir()
        for name in ("uv", "goc"):
            (stand_ins / name).write_text(STAND_IN)
            (stand_ins / name).chmod(0o755)

        for job in (workflow.get("jobs") or {}).values():
            steps = job.get("steps") or []
            by_id = {s["id"]: s for s in steps if s.get("id")}
            readers: dict[tuple[str, str], list[str]] = {}
            for s in steps:
                condition = str(s.get("if") or "")
                for ref in OUTPUT_REF.findall(condition):
                    readers.setdefault(ref, []).append(condition)

            for (step_id, output), conditions in readers.items():
                step = by_id.get(step_id)
                if not step or not step.get("run"):
                    raise Inconclusive(f"`steps.{step_id}` is read by an `if:` but is not a run step")
                label = step.get("name", step_id)
                body = step["run"]
                if "${{" in body:
                    raise Inconclusive(f"`{label}` uses an expression this harness cannot evaluate")
                continue_on_error = step.get("continue-on-error", False)
                if isinstance(continue_on_error, str):
                    raise Inconclusive(f"`{label}` sets continue-on-error to an expression")
                shell = resolve_shell(workflow, job, step)
                shell_label = " ".join(shell_argv(shell, Path("{0}")))

                def argv_for(script, shell=shell):
                    return shell_argv(shell, script)

                for mode, expected in (("zero", "0"), ("two", "2")):
                    proc, outputs = run_step(body, argv_for, mode, tmp, stand_ins)
                    if proc.returncode != 0 or outputs.get(output) != expected:
                        raise Inconclusive(
                            f"control `{mode}` on `{label}`: exit {proc.returncode}, "
                            f"{output}={outputs.get(output)!r} (want 0, {expected!r}); "
                            f"stderr: {proc.stderr.strip()[-300:]!r}"
                        )

                proc, outputs = run_step(body, argv_for, "fail", tmp, stand_ins)
                value = outputs.get(output, "")
                skips = (
                    proc.returncode != 0
                    and not continue_on_error
                    and not any(RUNS_AFTER_FAILURE.search(c) for c in conditions)
                )
                checked += 1
                where = f"`{label}` (steps.{step_id}.outputs.{output}) under `{shell_label}`"
                if skips or value == "0":
                    outcome = "the steps reading it skip" if skips else "it reports 0"
                    print(f"[CLOSED] {where}: exit {proc.returncode}, {output}={value!r}; {outcome}")
                else:
                    print(
                        f"[OPEN]   {where}: exit {proc.returncode}, {output}={value!r}; "
                        f"the steps reading it are not skipped and see {output}={value!r}"
                    )
                    open_steps.append(label)

    if not checked:
        raise Inconclusive(f"no `if:` in {path} reads a step output; the gate this script checks is gone")
    if open_steps:
        print(
            f"[FAIL] {len(open_steps)} of {checked} count step(s) fail open: when goc exits "
            "non-zero they neither fail nor report 0, so the steps gated on them decide on "
            "an empty count (under `!= '0'`, that launches the agent session and the self "
            "re-trigger)."
        )
        return 1
    print(f"[OK] all {checked} count step(s) fail closed when goc exits non-zero.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--workflow",
        type=Path,
        default=ROOT / ".github" / "workflows" / "pull-card.yml",
        help="workflow file to check (default: the repo's pull-card.yml)",
    )
    args = parser.parse_args()
    try:
        return check(args.workflow)
    except Inconclusive as exc:
        print(f"[INCONCLUSIVE] {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
