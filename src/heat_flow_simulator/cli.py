"""Command-line interface for the heat flow simulator."""

import click


@click.command()
@click.version_option(version="0.1.0", prog_name="heatflow")
def main() -> None:
    """Heat Flow Simulator CLI."""
    click.echo("Heat Flow Simulator v0.1.0")
    click.echo("Use --help for available commands.")


if __name__ == "__main__":
    main()
