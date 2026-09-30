"""Parameters: a nested, unit-aware collection of parameters."""

from __future__ import annotations

import copy
import json
import os
import re
from collections.abc import Callable, Iterator, Mapping, MutableMapping
from pathlib import Path
from typing import IO, Any, Self, TypeAlias

import yaml
from prettytable import PrettyTable

from parameter.errors import ParameterError
from parameter.parameter import Parameter, format_value

Node: TypeAlias = "Parameter | Parameters"

TABLE_FORMATS = ("text", "markdown", "csv", "html", "latex")
DATA_FORMATS = ("yaml", "json")


# Plain scalars resolve as in the YAML 1.2 core schema rather than PyYAML's YAML
# 1.1: "1e-3" is a float, "0042" is 42, and "on", "1:30" and dates are text.
# JSON's NaN and Infinity are floats, so JSON written by render("json") reads back.
_RESOLVERS = [
    ("null", r"~|null|Null|NULL|", ["~", "n", "N", ""]),
    ("bool", r"true|True|TRUE|false|False|FALSE", list("tTfF")),
    ("int", r"[-+]?[0-9](?:_?[0-9])*|0o[0-7]+|0x[0-9a-fA-F]+", list("-+0123456789")),
    (
        "float",
        r"""[-+]?(?:D\.(?:D)?|\.D)(?:[eE][-+]?[0-9]+)?
        |[-+]?D[eE][-+]?[0-9]+
        |[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN)|[-+]?Infinity|NaN""".replace(
            "D", "[0-9](?:_?[0-9])*"
        ),
        list("-+0123456789.IN"),
    ),
    ("merge", r"<<", ["<"]),
]


class _YamlLoader(yaml.SafeLoader):
    yaml_implicit_resolvers: dict[Any, Any] = {}  # noqa: RUF012 - filled in below

    def construct_mapping(self, node: Any, deep: bool = False) -> Any:
        seen: set[Any] = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                continue
            key = self.construct_object(key_node, deep=True)
            try:
                duplicate = key in seen
            except TypeError:  # unhashable, which the base class reports
                continue
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _construct_int(loader: yaml.SafeLoader, node: Any) -> int:
    text = loader.construct_scalar(node).replace("_", "").lower()
    return int(text, 16 if "0x" in text else 8 if "0o" in text else 10)


_YamlLoader.add_constructor("tag:yaml.org,2002:int", _construct_int)


class _FlowList(list[Any]):
    """A list that YAML output writes inline, like ``[150, mm]``."""


class _YamlDumper(yaml.SafeDumper):
    # The same resolvers, so text that would read back as a number is quoted.
    yaml_implicit_resolvers: dict[Any, Any] = {}  # noqa: RUF012 - filled in below


for _tag, _pattern, _first in _RESOLVERS:
    for _cls in (_YamlLoader, _YamlDumper):
        _cls.add_implicit_resolver(
            f"tag:yaml.org,2002:{_tag}", re.compile(f"^(?:{_pattern})$", re.VERBOSE), _first
        )

_YamlDumper.add_representer(
    _FlowList,
    lambda dumper, data: dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True),
)


class Parameters(MutableMapping[str, Node]):
    """A nested collection of :class:`Parameter` objects, grouped by name.

    Build one from a mapping or a YAML file. Leaves can be written in any
    form :meth:`Parameter.parse` accepts, and nested mappings become groups::

        params = Parameters.from_yaml("robot.yaml")
        params["arm.length"]           # dotted path
        params.arm.length              # attribute access
        params.to_si().magnitudes()    # plain SI numbers for a calculation
        print(params.table())

    Keys are strings (other keys are converted) and cannot contain ``"."``,
    which separates the parts of a path.
    """

    _data: dict[str, Node]

    def __init__(self, data: Mapping[Any, Any] | None = None, /, **kwargs: Any) -> None:
        object.__setattr__(self, "_data", {})
        if data is not None and not isinstance(data, Mapping):
            raise ParameterError(f"expected a mapping of parameters, got {type(data).__name__}")
        for key, value in [*(data or {}).items(), *kwargs.items()]:
            key = _check_key(key)
            if key in self._data:
                raise ParameterError(f"duplicate key {key!r}")
            self._data[key] = _coerce(value, key)

    @classmethod
    def from_yaml(cls, source: str | os.PathLike[str] | IO[str]) -> Self:
        """Read parameters from a YAML (or JSON) file path or open text stream."""
        if isinstance(source, (str, os.PathLike)):
            with open(source, encoding="utf-8") as stream:
                data = yaml.load(stream, Loader=_YamlLoader)
        else:
            data = yaml.load(source, Loader=_YamlLoader)
        if data is None:
            data = {}
        if not isinstance(data, Mapping):
            raise ParameterError(
                f"expected a mapping at the top level of {source}, got {type(data).__name__}"
            )
        return cls(data)

    # Mapping protocol --------------------------------------------------------

    def __getitem__(self, key: Any) -> Node:
        node: Node = self
        for part in str(key).split("."):
            if not isinstance(node, Parameters) or part not in node._data:
                raise KeyError(key)
            node = node._data[part]
        return node

    def __setitem__(self, key: Any, value: Any) -> None:
        # Validate everything before changing anything, so a failure leaves no trace.
        *parents, name = [_check_key(part) for part in str(key).split(".")]
        node = _coerce(value, str(key))
        group = self
        for part in parents:
            child = group._data.get(part)
            if isinstance(child, Parameter):
                raise ParameterError(f"{part!r} is a parameter, not a group", str(key))
            if child is None:
                child = group._data[part] = Parameters()
            group = child
        group._data[name] = node

    def __delitem__(self, key: Any) -> None:
        *parents, name = str(key).split(".")
        group = self[".".join(parents)] if parents else self
        if not isinstance(group, Parameters) or name not in group._data:
            raise KeyError(key)
        del group._data[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    # Attribute access --------------------------------------------------------

    def __getattr__(self, name: str) -> Node:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"{type(self).__name__} has no parameter {name!r}") from None

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or hasattr(getattr(type(self), name, None), "__set__"):
            object.__setattr__(self, name, value)
        elif hasattr(type(self), name):
            raise AttributeError(
                f"{name!r} is a {type(self).__name__} attribute; "
                f"use params[{name!r}] = ... to store a parameter with that name"
            )
        else:
            self[name] = value

    def __delattr__(self, name: str) -> None:
        if name in self._data:
            del self._data[name]
        else:
            object.__delattr__(self, name)

    def __dir__(self) -> list[str]:
        return [*super().__dir__(), *(key for key in self._data if key.isidentifier())]

    # Transformations -----------------------------------------------------------

    def copy(self) -> Self:
        """A copy of the group structure. Parameters are immutable and shared."""
        return self._map(lambda parameter: parameter)

    def to_si(self) -> Self:
        """A copy with every parameter converted to SI units."""
        return self._map(Parameter.to_si)

    def flatten(self, sep: str = ".") -> dict[str, Parameter]:
        """All parameters in a flat dict keyed by path, e.g. ``"arm.length"``."""
        flat: dict[str, Parameter] = {}
        for key, node in self._data.items():
            if isinstance(node, Parameters):
                for path, parameter in node.flatten(sep).items():
                    flat[f"{key}{sep}{path}"] = parameter
            else:
                flat[key] = node
        return flat

    def magnitudes(self) -> dict[str, Any]:
        """Nested dict of plain values in the current units, for calculations.

        Use ``params.to_si().magnitudes()`` to get SI values.
        """
        return {
            key: node.magnitudes() if isinstance(node, Parameters) else node.value
            for key, node in self._data.items()
        }

    def merge(self, other: Mapping[Any, Any]) -> Self:
        """A copy updated from ``other``, merging groups recursively.

        Useful for layering a study case over a baseline::

            case = baseline.merge({"arm": {"length": [1.2, "m"]}})
        """
        overrides = other if isinstance(other, Parameters) else Parameters(other)
        merged = self.copy()
        for key, node in overrides._data.items():
            existing = merged._data.get(key)
            if isinstance(existing, Parameters) and isinstance(node, Parameters):
                merged._data[key] = existing.merge(node)
            else:
                merged._data[key] = node.copy() if isinstance(node, Parameters) else node
        return merged

    def stack(self) -> Parameter:
        """Combine this group's parameters into one array parameter.

        Values are converted to the units of the first parameter, so a group
        ``{x: [50, mm], y: [-0.001, m]}`` stacks to ``Parameter([50, -1], "mm")``.
        """
        leaves = [
            node for node in self._data.values() if isinstance(node, Parameter) and node.is_numeric
        ]
        if not leaves or len(leaves) != len(self._data):
            raise ParameterError("stack() needs a non-empty group of numeric parameters")
        first = leaves[0]
        return Parameter([leaf.to(first.unit).value for leaf in leaves], first.units)

    # Output --------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Nested plain-Python data that ``Parameters(...)`` reads back."""
        return {
            key: node.to_dict() if isinstance(node, Parameters) else node.to_builtin()
            for key, node in self._data.items()
        }

    def to_yaml(self, path: str | os.PathLike[str] | None = None) -> str:
        """YAML text that :meth:`from_yaml` reads back, also written to ``path`` if given."""
        text = yaml.dump(
            _flow_lists(self.to_dict()), Dumper=_YamlDumper, sort_keys=False, allow_unicode=True
        )
        if path is not None:
            Path(path).write_text(text, encoding="utf-8")
        return text

    def table(self, precision: int = 6) -> PrettyTable:
        """A table of all parameters, with floats shown to ``precision`` significant figures.

        The result is a :class:`prettytable.PrettyTable`, which can be
        customised further. :meth:`render` renders it in common formats.
        """
        if precision < 1:
            raise ValueError(f"precision must be at least 1, got {precision}")
        flat = self.flatten()
        described = any(parameter.description for parameter in flat.values())
        table = PrettyTable(
            ["Parameter", "Value", "Units", *(["Description"] if described else [])]
        )
        table.align = "l"
        table.align["Value"] = "r"
        for path, parameter in flat.items():
            row = [path, format_value(parameter.value, precision), parameter.units]
            table.add_row([*row, parameter.description] if described else row)
        return table

    def render(self, fmt: str = "text", precision: int = 6) -> str:
        """Render as a table in one of :data:`TABLE_FORMATS`, or as :data:`DATA_FORMATS`.

        Tables show floats to ``precision`` significant figures. Data formats
        are lossless and can be read back.
        """
        if fmt == "yaml":
            return self.to_yaml().rstrip("\n")
        if fmt == "json":
            return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        table = self.table(precision)
        if fmt == "text":
            return table.get_string()
        if fmt == "markdown":
            return _markdown(table)
        if fmt == "csv":
            return table.get_csv_string(lineterminator="\n").rstrip("\n")
        if fmt == "latex":
            return _latex(table)
        if fmt in TABLE_FORMATS:
            return table.get_formatted_string(fmt)
        raise ValueError(f"unknown format {fmt!r}, expected one of {TABLE_FORMATS + DATA_FORMATS}")

    def __str__(self) -> str:
        return self.table().get_string()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._data!r})"

    def _repr_html_(self) -> str:
        return self.table().get_html_string()

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(
            lambda data: data if isinstance(data, cls) else cls(data),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda parameters: parameters.to_dict(), when_used="json"
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: Any, handler: Any) -> dict[str, Any]:
        return {"type": "object", "description": "Parameters, grouped by name"}

    def _map(self, function: Callable[[Parameter], Parameter]) -> Self:
        mapped = copy.copy(self)
        object.__setattr__(
            mapped,
            "_data",
            {
                key: node._map(function) if isinstance(node, Parameters) else function(node)
                for key, node in self._data.items()
            },
        )
        return mapped


def _markdown(table: PrettyTable) -> str:
    """A Markdown table with aligned columns (prettytable's separator row is ragged)."""
    header = table.field_names
    rows = [
        [str(cell).replace("|", "\\|").replace("\n", "<br>") for cell in row] for row in table.rows
    ]
    right = [table.align[name] == "r" for name in header]
    widths = [max(3, len(name), *(len(row[i]) for row in rows)) for i, name in enumerate(header)]

    def line(cells: list[str]) -> str:
        padded = (
            cell.rjust(width) if r else cell.ljust(width)
            for cell, width, r in zip(cells, widths, right, strict=True)
        )
        return f"| {' | '.join(padded)} |"

    rule = [
        ("-" * (width - 1) + ":") if r else (":" + "-" * (width - 1))
        for width, r in zip(widths, right, strict=True)
    ]
    return "\n".join([line(header), line(rule), *map(line, rows)])


_LATEX_SPECIAL = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _latex(table: PrettyTable) -> str:
    """LaTeX for a table, with special characters escaped (prettytable leaves them)."""

    def escape(text: Any) -> str:
        return "".join(_LATEX_SPECIAL.get(char, char) for char in str(text))

    escaped = PrettyTable([escape(name) for name in table.field_names])
    for name in table.field_names:
        escaped.align[escape(name)] = table.align[name]
    escaped.add_rows([[escape(cell) for cell in row] for row in table.rows])
    return escaped.get_latex_string().replace("\r\n", "\n")


def _flow_lists(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: _flow_lists(value) for key, value in data.items()}
    if isinstance(data, list):
        return _FlowList(data)
    return data


def _check_key(key: Any) -> str:
    key = str(key)
    if not key or "." in key:
        raise ParameterError(f"invalid key {key!r}: keys must be non-empty and cannot contain '.'")
    if key == "value":
        raise ParameterError(
            "'value' cannot name a parameter or group, because a mapping with a "
            "'value' key is read as a single parameter"
        )
    return key


def _coerce(value: Any, path: str) -> Node:
    if isinstance(value, Parameter):
        return value
    if isinstance(value, Parameters):
        return value.copy()  # groups are never shared between trees
    try:
        if isinstance(value, Mapping) and "value" not in value:
            return Parameters(value)
        return Parameter.parse(value)
    except ParameterError as error:
        raise error.with_parent(path) from error.__cause__
