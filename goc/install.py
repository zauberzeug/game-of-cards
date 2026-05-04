"""`goc install` — repo-scaffold flow.

Stub for sub-card ``goc-install-command-scaffolds-repo``. Will materialise the
``.claude/skills/``, ``deck/``, ``.game-of-cards/``, ``CLAUDE.md`` and
``AGENTS.md`` scaffolding from packaged templates into the cwd.
"""

from __future__ import annotations

import click


@click.command()
def install() -> None:
    """Scaffold a fresh repo with goc skills, deck, and config stubs."""
    click.echo("goc install — not yet implemented (sub-card: goc-install-command-scaffolds-repo)")


if __name__ == "__main__":
    install()
