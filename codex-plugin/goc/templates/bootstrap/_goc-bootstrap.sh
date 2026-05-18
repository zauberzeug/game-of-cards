#!/bin/sh

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
GOC_BIN=$(command -v goc 2>/dev/null || true)
USE_UV_GOC=0
if [ -z "$GOC_BIN" ] \
    && [ -f "$repo_root/pyproject.toml" ] \
    && grep -q 'name = "game-of-cards"' "$repo_root/pyproject.toml" \
    && command -v uv >/dev/null 2>&1; then
    USE_UV_GOC=1
fi

if [ -z "$GOC_BIN" ] && [ "$USE_UV_GOC" -eq 0 ]; then
    printf '%s\n' "Game of Cards CLI not found. Install with: pipx install game-of-cards" >&2
    exit 127
fi

run_goc() {
    if [ -n "$GOC_BIN" ]; then
        "$GOC_BIN" "$@"
    else
        uv run goc "$@"
    fi
}

required=""
if [ -f "$repo_root/.game-of-cards/deck/.goc-version" ]; then
    required=$(cat "$repo_root/.game-of-cards/deck/.goc-version" 2>/dev/null || true)
elif [ -f "$repo_root/deck/.goc-version" ]; then
    required=$(cat "$repo_root/deck/.goc-version" 2>/dev/null || true)
fi

if [ -n "$required" ]; then
    installed=$(run_goc --version 2>/dev/null | awk '{print $NF}')
    if awk -v installed="$installed" -v required="$required" '
        BEGIN {
            split(installed, i, ".")
            split(required, r, ".")
            for (n = 1; n <= 3; n++) {
                iv = i[n] + 0
                rv = r[n] + 0
                if (iv < rv) exit 0
                if (iv > rv) exit 1
            }
            exit 1
        }
    '; then
        printf 'Game of Cards CLI is older than this repo'\''s schema (installed: %s, required: %s). Run: pipx upgrade game-of-cards\n' "$installed" "$required" >&2
        exit 1
    fi
fi

if [ -n "$GOC_BIN" ]; then
    exec "$GOC_BIN" "$@"
fi
exec uv run goc "$@"
