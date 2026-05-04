"""Console-script entry point for the `goc` command.

Re-exports the engine's Click group, attaches the `install` and `upgrade`
subcommands, and adds a `--version` flag. Wired in `pyproject.toml` as
`[project.scripts] goc = "goc.cli:main"`.
"""

from __future__ import annotations

import click

from goc import __version__
from goc.engine import cli as engine_cli
from goc.install import install as install_cmd
from goc.install import upgrade as upgrade_cmd

engine_cli.add_command(install_cmd)
engine_cli.add_command(upgrade_cmd)


def main() -> None:
    """Console-script entry point."""

    wrapped = click.version_option(__version__, "-V", "--version", prog_name="goc")(engine_cli)
    wrapped()


if __name__ == "__main__":
    main()
