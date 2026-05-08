#!/usr/bin/env bash
# Local-dev mirror of .github/workflows/release.yml's `smoke` job.
#
# Runs Path A (kickoff completes when goc + Bash(goc:*) are pre-set) and
# Path B (preflight routes to kickoff when goc is denied) against the
# plugin payload at ./claude-plugin. Use this before pushing a release tag
# to catch regressions without burning CI minutes.
#
# Requirements:
#   - `claude` CLI installed (npm install -g @anthropic-ai/claude-code) and
#     authenticated (`claude login` or CLAUDE_CODE_OAUTH_TOKEN env var).
#   - `goc` CLI installable from this checkout (we install it for Path A).
#   - `uv` available on PATH.
#
# Usage:
#   ./scripts/smoke_release.sh                # both paths
#   ./scripts/smoke_release.sh A              # Path A only
#   ./scripts/smoke_release.sh B              # Path B only

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/claude-plugin"
WHICH="${1:-AB}"

if [ ! -d "$PLUGIN_DIR/.claude-plugin" ]; then
    echo "error: $PLUGIN_DIR is not a Claude Code plugin (missing .claude-plugin/)" >&2
    exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
    echo "error: claude CLI not on PATH. Install with: npm install -g @anthropic-ai/claude-code" >&2
    exit 1
fi

run_path_a() {
    echo "=== Path A: kickoff completes against fresh repo ==="
    local workdir=/tmp/smoke-A-local
    rm -rf "$workdir" && mkdir -p "$workdir"
    ( cd "$workdir" && git init -q -b main )

    echo "  pre-installing goc CLI from $REPO_ROOT..."
    uv tool install --force "$REPO_ROOT" >/dev/null

    ( cd "$workdir" && claude -p "
CI smoke test, Path A. Test directory: $workdir (fresh empty git repo).

1. Invoke Skill(audit-deck). Its preflight should route you to Skill(kickoff).
2. Run Skill(kickoff) to completion. goc is on PATH and Bash(goc:*) is allowed.
3. Verify .game-of-cards/deck/ exists, then write 'A:passed' to result.txt.
" \
        --plugin-dir "$PLUGIN_DIR" \
        --permission-mode dontAsk \
        --allowedTools "Read,Write,Edit,Bash(cd:*),Bash(ls:*),Bash(pwd:*),Bash(goc:*),Bash(git:*),Bash(which:*),Skill(kickoff),Skill(audit-deck)" \
        --max-turns 30 )

    test -d "$workdir/.game-of-cards/deck" || { echo "FAIL Path A: deck dir not created"; exit 1; }
    grep -q '^A:passed' "$workdir/result.txt" || { echo "FAIL Path A: result.txt missing"; exit 1; }
    echo "Path A passed"
}

run_path_b() {
    echo "=== Path B: preflight routes to kickoff when goc is not allowed ==="
    local workdir=/tmp/smoke-B-local
    rm -rf "$workdir" && mkdir -p "$workdir"
    ( cd "$workdir" && git init -q -b main )

    ( cd "$workdir" && claude -p "
CI smoke test, Path B. Test directory: $workdir (fresh empty git repo).
goc is NOT in the allowlist this run, simulating a fresh consumer install
where Bash(goc:*) has not yet been granted.

1. Invoke Skill(audit-deck). !-blocks calling goc will be denied.
2. Per the preflight section, invoke Skill(kickoff).
3. Kickoff should surface verbatim remediation text telling the user
   to add 'Bash(goc:*)' to permissions.allow in ~/.claude/settings.json.
4. After confirming the remediation text is emitted, write 'B:passed'
   to result.txt. Do NOT attempt to install goc or modify settings.
" \
        --plugin-dir "$PLUGIN_DIR" \
        --permission-mode dontAsk \
        --allowedTools "Read,Write,Bash(cd:*),Bash(ls:*),Bash(pwd:*),Bash(which:*),Skill(kickoff),Skill(audit-deck)" \
        --max-turns 20 )

    grep -q '^B:passed' "$workdir/result.txt" || { echo "FAIL Path B: result.txt missing"; exit 1; }
    echo "Path B passed"
}

case "$WHICH" in
    A)  run_path_a ;;
    B)  run_path_b ;;
    AB) run_path_a; run_path_b ;;
    *)  echo "usage: $0 [A|B|AB]" >&2; exit 2 ;;
esac

echo
echo "All requested smoke paths passed."
