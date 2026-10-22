"""Reproduce: goc run from a subdirectory finds the deck, but attests,
validates and installs against the subdirectory.

Builds a throwaway git repo holding a vendored (`--local-skills`) install and
a plain subdirectory `src/pkg/`, then runs the same goc surfaces twice, once
from the repo root and once from `src/pkg/`, and compares the two runs:

  1. `goc attest`        a project closure check that scans the working tree
  2. `goc validate`      the vendored skill-dir parity check
  3. hooks               the session-start active-card reminder, and the
                         pattern-generalization opt-in read from config.yaml
  4. `goc upgrade`       then the `goc install` its message points at

Precondition, checked first: the engine resolves the root deck from
`src/pkg/` (`_resolve_deck_root` walks upward). So every divergence below is
between two derivations of "the project" in one process, not a missing deck.

Exits 1 while any surface run from `src/pkg/` diverges from the root run.
Exits 0 once every surface agrees with the root run.
"""

from __future__ import annotations

import json
import os
import re
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

HOOKS = ROOT / "goc" / "templates" / "hooks"
CARD = "demo-card"

# A closure check whose only input is its working directory: it reports where
# it ran and fails if any *.py file below that directory holds a FIXME marker.
CHECKER = """\
import os, pathlib, sys
hits = [str(p) for p in pathlib.Path('.').rglob('*.py') if 'FIXME' in p.read_text()]
print(f"ran in {os.getcwd()} -- {len(hits)} FIXME marker(s)")
sys.exit(1 if hits else 0)
"""


def _env(home: Path) -> dict:
    env = dict(os.environ, PYTHONPATH=str(ROOT), HOME=str(home))
    for key in ("GOC_WORKER", "GOC_WORKTREE_DECK", "CLAUDE_PROJECT_DIR",
                "CODEX_PROJECT_DIR", "CLAUDE_PLUGIN_ROOT"):
        env.pop(key, None)
    return env


class Probe:
    def __init__(self, tmp: Path):
        self.home = tmp / "home"
        self.home.mkdir()
        self.repo = tmp / "repo"
        self.repo.mkdir()
        self.sub = self.repo / "src" / "pkg"
        self.env = _env(self.home)
        self.divergences: list[str] = []

    def rel(self, text: str) -> str:
        return text.replace(str(self.repo), "<repo>")

    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.repo, env=self.env,
                       check=True, capture_output=True, text=True)

    def goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-m", "goc.cli", *args], cwd=cwd,
                              env=self.env, capture_output=True, text=True)

    def hook(self, script: str, payload: dict) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HOOKS / script)],
                              input=json.dumps(payload), env=self.env,
                              capture_output=True, text=True)

    def compare(self, label: str, root_value, sub_value, key=None) -> None:
        """Print both runs; a divergence is judged on `key(value)` when given,
        so wording a fix may legitimately change (paths relative to cwd, an
        extra "upgrading <root>" note) does not count, only the outcome."""
        key = key or (lambda v: v)
        same = key(root_value) == key(sub_value)
        print(f"  {'same' if same else 'DIFFERS'}: {label}")
        print(f"      from <repo>/        : {root_value}")
        print(f"      from <repo>/src/pkg/: {sub_value}")
        if not same:
            self.divergences.append(label)

    # ── fixture ────────────────────────────────────────────────────────────
    def build(self, checker: Path) -> None:
        self.git("init", "-q")
        self.git("config", "user.email", "probe@example.invalid")
        self.git("config", "user.name", "probe")
        self.git("config", "commit.gpgsign", "false")
        self.git("commit", "-q", "--allow-empty", "-m", "init")
        r = self.goc(self.repo, "install", "--agents", "claude", "--local-skills")
        assert r.returncode == 0, r.stderr

        config = self.repo / ".game-of-cards" / "config.yaml"
        text = config.read_text()
        closure = (
            "layer_2_project_dod:\n"
            "  - name: no-fixme-markers\n"
            "    kind: automated\n"
            f"    cmd: [{json.dumps(sys.executable)}, {json.dumps(str(checker))}]\n"
            "layer_3_goc_dod: []\n\n"
        )
        text, n = re.subn(r"(?ms)^layer_2_project_dod:.*?(?=^workflow:)", closure, text)
        assert n == 1, "config.yaml layout changed; update the fixture"
        text, n = re.subn(r"pattern_generalization_check: \w+",
                          "pattern_generalization_check: true", text)
        assert n == 1, "config.yaml layout changed; update the fixture"
        config.write_text(text)
        parsed = yaml_lite.safe_load(text)
        assert parsed["layer_2_project_dod"][0]["cmd"] == [sys.executable, str(checker)]
        assert parsed["hooks"]["pattern_generalization_check"] is True

        (self.repo / "app.py").write_text("print('debug')  # FIXME: remove before release\n")
        self.sub.mkdir(parents=True)
        (self.sub / "mod.py").write_text("VALUE = 1\n")
        r = self.goc(self.repo, "new", CARD, "--summary", "Probe card.", "--gate", "none")
        assert r.returncode == 0, r.stderr
        r = self.goc(self.repo, "status", CARD, "active")
        assert r.returncode == 0, r.stderr
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "fixture")

    def precondition(self) -> None:
        print("Precondition: the engine resolves the root deck from src/pkg/")
        r = self.goc(self.sub, "--status", "all", "--json")
        titles = [c["title"] for c in json.loads(r.stdout)]
        print(f"  `goc --status all --json` from src/pkg/ lists: {titles}")
        assert titles == [CARD], "deck walk-up no longer resolves; probe is moot"
        print()

    # ── surfaces ───────────────────────────────────────────────────────────
    def attest(self) -> None:
        print("1. goc attest: where the project's closure check runs")
        rows = {}
        for where in (self.repo, self.sub):
            r = self.goc(where, "attest", CARD, "--non-interactive")
            row = next(line.strip() for line in r.stdout.splitlines()
                       if "no-fixme-markers" in line and "[" in line)
            rows[where] = (row, "Attestation OK." in r.stdout)
        self.compare("closure-check row",
                     self.rel(rows[self.repo][0]), self.rel(rows[self.sub][0]))
        self.compare("prints 'Attestation OK.'", rows[self.repo][1], rows[self.sub][1])
        log = (self.repo / ".game-of-cards" / "deck" / CARD / "log.md").read_text()
        last = log.rsplit("## Closure verification", 1)[-1]
        recorded = next(l for l in last.splitlines() if "no-fixme-markers" in l)
        print(f"  last block written to log.md records: {self.rel(recorded.strip())}")
        print()

    def validate(self) -> None:
        print("2. goc validate: the vendored skill-dir parity check")
        r = self.goc(self.repo, "validate")
        print(f"  baseline from <repo>/: exit {r.returncode}")
        shutil.rmtree(self.repo / ".claude" / "skills" / "deck")
        print("  removed the vendored .claude/skills/deck/ skill")
        results = {}
        for where in (self.repo, self.sub):
            r = self.goc(where, "validate")
            missing = next((l for l in r.stdout.splitlines() + r.stderr.splitlines()
                            if "missing skills" in l), None)
            results[where] = (r.returncode, "reports missing skill" if missing else "silent")
        self.compare("validate (exit code, parity verdict)", results[self.repo], results[self.sub])
        self.git("checkout", "--", ".claude/skills/deck")
        print()

    def hooks(self) -> None:
        print("3. hooks: the session-start reminder and the pattern-check opt-in")
        r = self.goc(self.sub, "--status", "active", "--json")
        print(f"  `goc --status active --json` from src/pkg/ lists: "
              f"{[c['title'] for c in json.loads(r.stdout)]}")
        banners = {}
        for where in (self.repo, self.sub):
            r = self.hook("deck_session_start.py",
                          {"hook_event_name": "SessionStart", "cwd": str(where)})
            banners[where] = r.stdout.strip() or "(nothing printed)"
        self.compare("session-start hook output", banners[self.repo], banners[self.sub])

        transcript = self.home / "transcript.jsonl"
        transcript.write_text("\n".join(json.dumps(e) for e in (
            {"message": {"role": "user", "content": "rename the helper"}},
            {"message": {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Edit", "input": {"file_path": "app.py"}}]}},
        )) + "\n")
        codes = {}
        for where in (self.repo, self.sub):
            r = self.hook("pattern_generalization_check.py",
                          {"hook_event_name": "Stop", "cwd": str(where),
                           "transcript_path": str(transcript)})
            codes[where] = f"exit {r.returncode} ({'reminder' if r.returncode == 2 else 'disabled'})"
        self.compare("pattern-check hook after an Edit turn", codes[self.repo], codes[self.sub])
        print()

    def upgrade_then_install(self) -> None:
        print("4. goc upgrade, then the goc install it points at")
        up = {}
        for where in (self.repo, self.sub):
            r = self.goc(where, "upgrade", "--dry-run")
            out = r.stdout.strip() or r.stderr.strip()
            up[where] = f"exit {r.returncode}: {out.splitlines()[0]}"
        # Outcome: exit code, and whether the root install was recognized.
        self.compare("goc upgrade --dry-run", up[self.repo], up[self.sub],
                     key=lambda v: (v.split(":")[0], "no existing install" in v))

        inst = {}
        for where in (self.repo, self.sub):
            before = {p.name for p in where.iterdir()}
            r = self.goc(where, "install")
            created = sorted({p.name for p in where.iterdir()} - before)
            out = r.stderr.strip() or r.stdout.strip()
            inst[where] = f"exit {r.returncode}: " + (
                f"created {', '.join(created)} here" if created else out.splitlines()[0])
        # Outcome: exit code, and whether anything was scaffolded.
        self.compare("goc install", self.rel(inst[self.repo]), self.rel(inst[self.sub]),
                     key=lambda v: (v.split(":")[0], v.endswith(" here")))

        views = {}
        for where in (self.repo, self.sub):
            r = self.goc(where, "--status", "all", "--json")
            views[where] = [c["title"] for c in json.loads(r.stdout)]
        self.compare("deck `goc --status all --json` shows afterwards",
                     views[self.repo], views[self.sub])
        r = self.goc(self.sub, "new", "filed-from-the-subdirectory", "--summary", "Probe.")
        print(f"  `goc new` from src/pkg/ then prints: {r.stdout.strip().splitlines()[0]}")
        landed = (self.sub / ".game-of-cards" / "deck" / "filed-from-the-subdirectory").is_dir()
        print(f"  ...and the card landed in: "
              f"{'src/pkg/.game-of-cards/deck/ (the stray deck)' if landed else '.game-of-cards/deck/ (the real deck)'}")
        print()


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="goc-subdir-root-"))
    try:
        checker = tmp / "no_fixme_check.py"
        checker.write_text(CHECKER)
        probe = Probe(tmp)
        probe.build(checker)
        probe.precondition()
        probe.attest()
        probe.validate()
        probe.hooks()
        probe.upgrade_then_install()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if probe.divergences:
        print(f"DEFECT CONFIRMED: {len(probe.divergences)} surface(s) run from a "
              "subdirectory disagree with the root run:")
        for label in probe.divergences:
            print(f"  - {label}")
        return 1
    print("OK: every surface run from src/pkg/ agrees with the root run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
