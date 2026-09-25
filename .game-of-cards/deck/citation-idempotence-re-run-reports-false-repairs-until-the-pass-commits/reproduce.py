#!/usr/bin/env python3
"""The citation idempotence re-run is only valid once the repairs are committed.

`goc/templates/skills/refine-deck/reference.md` § "Citation anchor check" ends
with an idempotence check — "After applying the rewrites, run the decision
phase again over the cards just written and assert it proposes ZERO further
repairs" — and `SKILL.md` carries the same order: apply, then re-run.  Neither
mentions the commit.

The anchor walk reads the card's history out of `git log`, so an uncommitted
rewrite is invisible to it.  A cite the pass has just written correctly is
therefore anchored on the newest commit where that TOKEN turned from absent to
present in the card, and for a renumbering pass that is routinely a *retired*
occurrence — the number the card used to carry for a different cite, before an
earlier pass moved that cite elsewhere.  The re-run then proposes moving the
correct cite onto whatever the retired occurrence's text now occupies.

This is not the collision the 2026-09-14 fix addressed.  Presence is already
set membership, so no range spells the token; and the token occurs exactly
once in the card, so the ambiguous-occurrence decline never fires.  The
colliding occurrence is in the card's PAST, and the current-occurrence count
cannot see it.

Census, read-only: for every in-scope cite that occurs exactly once in an
open/active card, compare the anchor the walk picks over the full history
against the anchor it picks when the commit that wrote the token is withheld,
together with every commit after it — which is exactly what the walk sees
before the pass commits, since its history ends at the pass's input state.
(Withholding the writing commit alone overcounts: on a card touched again
later, the next commit reads as a fresh absent -> present turn.)  Reports the
cites where the withheld-commit reading proposes a confident, unique repair
while the full reading verdicts the cite current.

Exits 0 when no such cite exists.
"""
import collections
import re
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
DECK = ROOT / ".game-of-cards" / "deck"
MIRROR = ("claude-plugin/", "codex-plugin/", "openclaw-plugin/", ".claude/",
          ".codex/", "node_modules/", "dist/")
CITE_RE = re.compile(
    r'(?<![\w/.-])'
    r'(?P<path>(?:[\w.\-]+/)*[\w.\-]+\.(?:py|md|yaml|yml|json|ts|js|sh|toml|cfg|txt))'
    r':(?P<start>\d+)(?:-(?P<end>\d+))?(?![\d.])')
DEF_RE = re.compile(r'^\s*(?:async\s+)?(def|class)\s+(\w+)')


def git(*a):
    return subprocess.run(["git"] + list(a), cwd=ROOT,
                          capture_output=True, text=True).stdout


def fence_mask(lines):
    inside, fence = [], None
    for ln in lines:
        m = re.match(r'^(`{3,}|~{3,})', ln.lstrip())
        if fence is None:
            if m:
                fence = m.group(1)
                inside.append(True)
                continue
            inside.append(False)
        else:
            inside.append(True)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
    return inside


def cites(text):
    """In-scope cites only: prose, and comment labels inside fences."""
    lines = text.split("\n")
    mask = fence_mask(lines)
    out = []
    for i, line in enumerate(lines):
        for m in CITE_RE.finditer(line):
            if m.group('end') is None and line[m.end():].startswith(':'):
                continue                      # pasted grep -n record
            if mask[i] and not re.search(r'(^|\s)(#|//)[^\n]*$', line[:m.start()]):
                continue                      # pasted output inside a fence
            out.append((m.group(0), m.group('path'), int(m.group('start')),
                        int(m.group('end')) if m.group('end') else None, i))
    return out


FILES = [f for f in git("ls-files").split("\n") if f]
BY_SUFFIX = collections.defaultdict(list)
for f in FILES:
    parts = f.split("/")
    for i in range(len(parts)):
        BY_SUFFIX["/".join(parts[i:])].append(f)


def resolve(path):
    if path in FILES:
        return path
    pool = [c for c in BY_SUFFIX.get(path, []) if not c.startswith(MIRROR)] \
        or BY_SUFFIX.get(path, [])
    if not pool:
        return None
    return sorted(pool, key=lambda p: (p.count("/"), len(p)))[0]


_blob = {}


def blob(commit, path):
    k = (commit, path)
    if k not in _blob:
        r = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT,
                           capture_output=True, text=True)
        _blob[k] = r.stdout.split("\n") if r.returncode == 0 else None
    return _blob[k]


def line_at(commit, path, n):
    b = blob(commit, path)
    return b[n - 1] if b and 1 <= n <= len(b) else None


def trivial(t):
    return t is None or not t.strip() or len(t.strip()) < 12 \
        or t.strip() in ("{", "}", "(", ")", "[", "]", '"""', "'''", "---", "```")


def relocate(path, anchor):
    b = blob("HEAD", path)
    if b is None:
        return None
    hits = [i + 1 for i, l in enumerate(b) if l == anchor]
    if len(hits) == 1:
        return hits[0]
    if hits:
        return None
    m = DEF_RE.match(anchor)
    if m:
        pat = re.compile(rf'^\s*(?:async\s+)?{m.group(1)}\s+{re.escape(m.group(2))}\s*[\(:]')
        hits = [i + 1 for i, l in enumerate(b) if pat.match(l)]
        if len(hits) == 1:
            return hits[0]
    return None


def tokens_at(commit, title):
    for p in (f".game-of-cards/deck/{title}/README.md", f"deck/{title}/README.md"):
        b = blob(commit, p)
        if b is not None:
            return {c[0] for c in cites("\n".join(b))}
    return None


def anchor_of(title, token, commits):
    """Newest commit where token turns absent -> present."""
    prev, found = set(), None
    for c in commits:
        t = tokens_at(c, title)
        if t is None:
            continue
        if token in t and token not in prev:
            found = c
        prev = t
    return found


def main():
    titles = sorted(p.name for p in DECK.iterdir() if (p / "README.md").exists())
    live = []
    for t in titles:
        head = (DECK / t / "README.md").read_text()
        st = re.search(r'^status:\s*(\S+)', head, re.M)
        if st and st.group(1).strip('"') in ("open", "active"):
            live.append((t, head))

    findings, checked = [], 0
    for t, text in live:
        cs = cites(text)
        occ = collections.Counter(c[0] for c in cs)
        commits = list(reversed([c for c in git(
            "log", "--follow", "--format=%H", "--",
            f".game-of-cards/deck/{t}/README.md").split("\n") if c]))
        for tok, rawpath, start, end, _ln in cs:
            if occ[tok] > 1 or end is not None:
                continue
            path = resolve(rawpath)
            if path is None:
                continue
            full = anchor_of(t, tok, commits)
            if full is None:
                continue
            checked += 1
            # what the walk sees before the writing commit exists: the history
            # ENDS at the pass's input state, so every later commit is withheld
            # too — dropping only `full` would let the next commit that touched
            # the card read as a fresh absent -> present turn
            pre = anchor_of(t, tok, commits[:commits.index(full)])
            if pre is None or pre == full:
                continue
            t_full = line_at(full, path, start)
            t_pre = line_at(pre, path, start)
            head_line = line_at("HEAD", path, start)
            if trivial(t_pre) or t_pre is None:
                continue
            if t_pre == head_line:
                continue
            new = relocate(path, t_pre)
            if new is None or new == start:
                continue
            full_says_current = (t_full == head_line and not trivial(t_full))
            findings.append((t, tok, pre[:9], t_pre.strip()[:60], new,
                             full[:9], full_says_current))

    print(f"open/active cards scanned                 : {len(live)}")
    print(f"single-occurrence in-scope cites anchored  : {checked}")
    print()
    print("cites whose anchor is decided by a RETIRED occurrence when the")
    print("writing commit is withheld — i.e. what the re-run sees before the")
    print("pass commits:")
    print()
    for card, tok, pre, txt, new, full, cur in findings:
        verdict = "current" if cur else "(not current)"
        print(f"  {card}")
        print(f"      cite {tok}  withheld-anchor {pre} -> would rewrite to :{new}")
        print(f"      retired occurrence's text: {txt!r}")
        print(f"      full-history anchor {full} verdicts: {verdict}")
    if not findings:
        print("  (none)")
    print()
    false_repairs = sum(1 for f in findings if f[6])
    print(f"false repairs the pre-commit re-run proposes: {false_repairs}")
    if false_repairs:
        print("  each is individually well-formed — a real anchor, a unique match,")
        print("  a confident rewrite — and each moves a CORRECT cite onto")
        print("  unrelated code; the same re-run after the commit reports zero")
    return 1 if false_repairs else 0


if __name__ == "__main__":
    sys.exit(main())
