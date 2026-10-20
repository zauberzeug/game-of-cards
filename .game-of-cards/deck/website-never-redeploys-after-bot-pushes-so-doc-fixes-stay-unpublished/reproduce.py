"""Reproduce: game-of-cards.com lags main because bot pushes never deploy it.

For each file `pages.yml` publishes verbatim, fetch the live copy, find the
commit on main whose version of the file it is byte-identical to, and report
how long the oldest change since then has sat on main without being
published. Also prints the Pages trigger block, the most recent Pages run
(when `gh` is available) and the closed cards whose committed fixes are not
on the site.

Exit codes: 0 — every mirror is current or lags main by less than
MAX_LAG_HOURS (the DoD target); 1 — at least one mirror lags longer (the
defect); 2 — the site or git could not be read, so no verdict.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


ROOT = _repo_root()
SITE = "https://game-of-cards.com"
# repo path -> live URL path, per the header map in .github/workflows/pages.yml.
MIRRORS = {
    "README.md": "/README.md",
    "goc.md": "/goc.md",
    "ABOUT.md": "/ABOUT.md",
    "site/llms.txt": "/llms.txt",
    "site/index.html": "/",
    "site/privacy.html": "/privacy.html",
    "site/styles.css": "/styles.css",
    "site/stars.js": "/stars.js",
}
# A scheduled deploy may trail main by one interval; anything past two days
# means the change is not going to be published on its own.
MAX_LAG_HOURS = 48


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, encoding="utf-8", check=True
    ).stdout


def blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def fetch(url_path: str) -> bytes:
    req = urllib.request.Request(SITE + url_path, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def matching_commit(path: str, live_blob: str) -> str | None:
    """Newest commit on main whose version of `path` is the live bytes."""
    for sha in git("log", "--format=%H", "HEAD", "--", path).split():
        try:
            if git("rev-parse", f"{sha}:{path}").strip() == live_blob:
                return sha
        except subprocess.CalledProcessError:
            continue
    return None


def main() -> int:
    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    on_block = re.search(r"^on:\n(?:[ \t].*\n|\n)+", workflow, re.MULTILINE)
    print("pages.yml trigger block (the only events that deploy the site):")
    for line in (on_block.group(0) if on_block else "<not found>").rstrip().splitlines():
        print(f"  {line}")
    print()

    try:
        runs = json.loads(subprocess.run(
            ["gh", "run", "list", "--workflow", "pages.yml", "--limit", "1",
             "--json", "createdAt,headSha,event,conclusion"],
            cwd=ROOT, capture_output=True, encoding="utf-8", check=True,
        ).stdout)
        if runs:
            r = runs[0]
            print(f"most recent Pages run: {r['createdAt']} ({r['event']}, "
                  f"{r['conclusion']}) on {r['headSha'][:8]}")
        else:
            print("most recent Pages run: none recorded")
    except (OSError, subprocess.CalledProcessError, ValueError):
        print("most recent Pages run: (gh unavailable — skipped)")
    print()

    now = dt.datetime.now(dt.timezone.utc)
    lagging = 0
    unpublished: dict[str, str] = {}  # sha -> "%h\t%cs\t%an\t%s"
    print(f"live mirror vs main (defect when the oldest unpublished change is > {MAX_LAG_HOURS}h old):")
    for path, url_path in MIRRORS.items():
        try:
            live = fetch(url_path)
        except OSError as exc:
            print(f"  {url_path:<13} cannot fetch: {exc}")
            return 2
        head_blob = git("rev-parse", f"HEAD:{path}").strip()
        live_blob = blob_id(live)
        if live_blob == head_blob:
            print(f"  {url_path:<13} == main")
            continue
        sha = matching_commit(path, live_blob)
        if sha is None:
            print(f"  {url_path:<13} matches no commit of {path} on main — cannot date it")
            return 2
        pending = git("log", "--format=%H%x09%cI%x09%h%x09%cs%x09%an%x09%s",
                      f"{sha}..HEAD", "--", path).splitlines()
        for line in pending:
            full, _iso, rest = line.split("\t", 2)
            unpublished[full] = rest
        oldest_iso = pending[-1].split("\t")[1]
        oldest = dt.datetime.fromisoformat(oldest_iso.replace("Z", "+00:00"))
        age_h = (now - oldest).total_seconds() / 3600
        when = git("log", "-1", "--format=%cs", sha).strip()
        verdict = "DEFECT" if age_h > MAX_LAG_HOURS else "pending"
        if age_h > MAX_LAG_HOURS:
            lagging += 1
        print(f"  {url_path:<13} == {path} at {sha[:8]} ({when}); {len(pending)} later "
              f"commit(s) unpublished, oldest {age_h / 24:.0f} days old [{verdict}]")
    print()

    if unpublished:
        rows = sorted((line.split("\t", 3) for line in unpublished.values()),
                      key=lambda row: row[1])
        authors = sorted({row[2] for row in rows})
        print(f"commits on main whose content is not on the site: {len(rows)}, "
              f"authored by: {', '.join(authors)}")
        closed = [m.group(1) for row in rows
                  if (m := re.search(r"closes ([a-z0-9-]+)", row[3]))]
        if closed:
            print("closed cards whose committed fix is not on the site:")
            for title in closed:
                print(f"  - {title}")
        print()

    if lagging:
        print(f"[DEFECT] {lagging} of {len(MIRRORS)} published mirrors lag main by more than "
              f"{MAX_LAG_HOURS}h: pages.yml deploys only on push, and pushes made with the "
              "default GITHUB_TOKEN start no workflow run, so bot-authored doc fixes never "
              "reach game-of-cards.com.")
        return 1
    print(f"[OK] every published mirror is within {MAX_LAG_HOURS}h of main.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
