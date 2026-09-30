"""Command line interface: show a parameter file as a table or convert it."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from parameter import __version__
from parameter.collection import DATA_FORMATS, TABLE_FORMATS, Parameters
from parameter.errors import ParameterError
from parameter.parameter import Parameter


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="parameter",
        description="Show a YAML or JSON parameter file as a table, optionally in SI units.",
    )
    parser.add_argument("file", type=Path, help="parameter file to read")
    parser.add_argument("key", nargs="?", help="dotted path of the group or parameter to show")
    parser.add_argument("--si", action="store_true", help="convert values to SI units")
    parser.add_argument(
        "-f",
        "--format",
        choices=TABLE_FORMATS + DATA_FORMATS,
        default="text",
        metavar="FORMAT",
        help=f"output format: {', '.join(TABLE_FORMATS + DATA_FORMATS)} (default: text)",
    )
    parser.add_argument(
        "-p",
        "--precision",
        type=_positive_int,
        default=6,
        metavar="N",
        help="significant figures shown in tables (default: 6)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    try:
        parameters = Parameters.from_yaml(args.file)
        if args.key:
            selected = parameters[args.key]
            if isinstance(selected, Parameter):
                selected = Parameters({args.key.rsplit(".", 1)[-1]: selected})
            parameters = selected
    except KeyError:
        return _fail(f"{args.file} has no parameter or group {args.key!r}")
    except UnicodeDecodeError as error:
        return _fail(f"{args.file} is not UTF-8 text: {error}")
    except (OSError, ParameterError, yaml.YAMLError) as error:
        return _fail(str(error))

    if args.si:
        parameters = parameters.to_si()
    print(parameters.render(args.format, args.precision))
    return 0


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {value}")
    return value


def _fail(message: str) -> int:
    print(f"parameter: error: {message}", file=sys.stderr)
    return 1
