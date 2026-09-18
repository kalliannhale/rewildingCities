"""
canopy/cli/__init__.py ~ the garden's command line

Run as:  python -m canopy.cli <command> ...
(To get a bare `rewilding` command, wire a console script once the project is
packaged; see the note in setup_guide.md.)

  init    <plot> [name]          found a plot for a new community
  wonder  <plot> ["question"]    what can this ground wonder about?
  sows    <experiment.yml>       run a composed experiment

Each command is its own module exposing register(subparsers). Add a command by
writing canopy/cli/<name>.py with a register() that calls set_defaults(func=...),
then listing it in _COMMANDS below. The existing experiment.py runner is left in
place and still works standalone (python -m canopy.cli.experiment). ~
"""

from __future__ import annotations

import argparse
import importlib

_COMMANDS = ("init", "wonder", "sows", "map", "acquire")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rewilding",
        description="the garden's command line ~ found, wonder, sow",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in _COMMANDS:
        importlib.import_module(f"{__name__}.{name}").register(subparsers)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
