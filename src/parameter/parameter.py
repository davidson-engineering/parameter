"""The Parameter type: a value with units."""

from __future__ import annotations

import numbers
import operator
import re
import warnings
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pint
import pint.compat

from parameter import units as _units
from parameter.errors import ParameterError

REL_TOL = 1e-9
"""Default relative tolerance for ``==`` and :meth:`Parameter.isclose`."""

ABS_TOL = 0.0
"""Default absolute tolerance for ``==`` and :meth:`Parameter.isclose`."""

_SUMMARY_THRESHOLD = 20
_EDGE_ITEMS = 3

_NUMBER = r"[-+]?(?:\d(?:_?\d)*(?:\.(?:\d(?:_?\d)*)?)?|\.\d(?:_?\d)*)(?:[eE][-+]?\d+)?"
_FLOAT = re.compile(_NUMBER)
_QUANTITY_TEXT = re.compile(rf"\s*({_NUMBER})\s*(.*?)\s*", re.DOTALL)
_LEAF_KEYS = frozenset({"value", "units", "description"})


def _comparison(op: Callable[[Any, Any], Any]) -> Callable[[Parameter, Any], Any]:
    def compare(self: Parameter, other: Any) -> Any:
        operand = _operand(other)
        if operand is NotImplemented:
            return NotImplemented
        return op(self.quantity, operand)

    return compare


def _arithmetic(
    op: Callable[[Any, Any], Any], reflected: bool = False, align: bool = False
) -> Callable[[Parameter, Any], Any]:
    """An operator method.

    With ``align``, the right operand is first expressed in the left operand's
    units where their dimensions match, so m * mm gives m^2 rather than m.mm.
    """

    def arithmetic(self: Parameter, other: Any) -> Any:
        operand = _operand(other)
        if operand is NotImplemented:
            return NotImplemented
        left, right = (operand, self.quantity) if reflected else (self.quantity, operand)
        if align and isinstance(left, pint.Quantity) and isinstance(right, pint.Quantity):
            right = right.to(_units.align_units(right.units, left.units))
        return Parameter(op(left, right))

    return arithmetic


class Parameter:
    """An immutable value with units.

    The value is a number, a numpy array (lists of numbers are converted to
    one), or a non-numeric value such as text, a bool or a list of strings.
    Numeric parameters support unit-aware arithmetic, comparisons and numpy
    functions. Non-numeric parameters are carried along unchanged and must be
    dimensionless.

    >>> Parameter(10, "m") / Parameter(2, "s")
    Parameter(5.0, 'm/s')
    """

    __slots__ = ("_description", "_unit", "_units", "_value")

    def __init__(
        self,
        value: Any,
        units: str | pint.Unit | None = None,
        description: str | None = None,
    ) -> None:
        if isinstance(value, Parameter):
            if description is None:
                description = value.description
            if units is None:
                value, units = value.value, value.units
            else:
                value = value.quantity
        if isinstance(value, pint.Quantity):
            if units is None:
                units = value.units  # type: ignore[assignment]  # pint types this as PlainUnit
            else:
                value = value.to(_units.parse_units(units))
            value = value.magnitude
        value = _normalize_value(value)
        unit = _units.parse_units(units)
        if not _is_numeric(value) and unit != _units.ureg.dimensionless:
            raise ParameterError(f"non-numeric value {value!r} cannot have units {units!r}")
        if isinstance(units, pint.Unit):
            text = _units.format_units(units)
        elif units is None or str(units).strip() in _units.DIMENSIONLESS_TOKENS:
            text = "-"
        else:
            text = str(units).strip()
        self._value = value
        self._units = text
        self._unit = unit
        self._description = "" if description is None else str(description)

    @classmethod
    def parse(cls, data: Any) -> Parameter:
        """Build a parameter from any of the forms accepted in parameter files.

        - ``[value, units]``, e.g. ``[150, mm]`` or ``[[0, 120, 240], deg]``
        - ``{value: ..., units: ..., description: ...}`` (only ``value`` required)
        - a string starting with a number, e.g. ``"150 mm"``
        - any other value, which becomes a dimensionless or text parameter
        """
        if isinstance(data, Parameter):
            return data
        if isinstance(data, pint.Quantity):
            return cls(data)
        if isinstance(data, Mapping):
            if "value" not in data or not set(data) <= _LEAF_KEYS:
                raise ParameterError(
                    f"a parameter mapping needs a 'value' key and at most "
                    f"'units' and 'description', got keys {sorted(map(str, data))}"
                )
            return cls(data["value"], data.get("units"), data.get("description", ""))
        if isinstance(data, (list, tuple)) and len(data) == 2 and isinstance(data[1], str):
            value, units = data
            if isinstance(value, str) and _FLOAT.fullmatch(value.strip()):
                value = _number(value.strip())
            if not isinstance(value, str) or units.strip() in _units.DIMENSIONLESS_TOKENS:
                return cls(value, units)
            if re.match(r"\s*[-+]?\.?\d", value) and _is_units(units):
                raise ParameterError(f"cannot read {value!r} as a number")
        if isinstance(data, str) and (match := _QUANTITY_TEXT.fullmatch(data)):
            number, units = match.groups()
            # Only a number followed by something that starts like units is read
            # as a quantity. "0042", "1.2.3" and "2024-01-01" stay text.
            if units and (units[0].isalpha() or units[0] in "(%°‰"):
                try:
                    return cls(_number(number), units)
                except ParameterError as error:
                    raise ParameterError(
                        f"cannot read {data!r} as a number with units ({error}); "
                        "to store it as text use {value: ...}"
                    ) from error
        if isinstance(data, (str, numbers.Number, np.ndarray, np.generic, list, tuple)) or (
            data is None
        ):
            return cls(data)
        raise ParameterError(f"cannot make a parameter from {type(data).__name__} {data!r}")

    @classmethod
    def from_quantity(cls, quantity: pint.Quantity, description: str = "") -> Parameter:
        """Wrap a pint quantity."""
        return cls(quantity, description=description)

    @property
    def value(self) -> Any:
        """The value, in :attr:`units`."""
        return self._value

    @property
    def units(self) -> str:
        """The units as text, ``"-"`` when dimensionless."""
        return self._units

    @property
    def unit(self) -> pint.Unit:
        """The units as a pint unit."""
        return self._unit

    @property
    def description(self) -> str:
        return self._description

    @property
    def is_numeric(self) -> bool:
        """Whether the value is a number or numeric array (and so has a quantity)."""
        return _is_numeric(self._value)

    @property
    def quantity(self) -> pint.Quantity:
        """The parameter as a pint quantity."""
        if not self.is_numeric:
            raise TypeError(f"{self!r} is not numeric")
        return _units.ureg.Quantity(self._value, self._unit)

    @property
    def dimensionality(self) -> Any:
        """The pint dimensionality, e.g. ``[length] / [time]``."""
        return self.quantity.dimensionality

    def to(self, units: str | pint.Unit) -> Parameter:
        """Convert to other units, e.g. ``Parameter(1, "m").to("mm")``."""
        quantity = self.quantity.to(_units.parse_units(units))
        return Parameter(quantity.magnitude, units, self._description)

    def to_si(self) -> Parameter:
        """Convert to coherent SI units (see :func:`parameter.units.si_units`).

        Non-numeric parameters are returned unchanged.
        """
        if not self.is_numeric:
            return self
        return self.to(_units.si_units(self._unit))

    def to_numpy(self, units: str | pint.Unit | None = None) -> np.ndarray:
        """The value as an array, optionally converted to ``units`` first."""
        return np.asarray((self if units is None else self.to(units)).value)

    def is_compatible_with(self, other: str | pint.Unit | Parameter) -> bool:
        """Whether this can convert to ``other``: units, a parameter or ``"[length]"``."""
        if not self.is_numeric:
            return False
        if isinstance(other, Parameter):
            return other.is_numeric and self.dimensionality == other.dimensionality
        return self.dimensionality == _units.parse_dimensionality(other)

    def isclose(self, other: Any, *, rel_tol: float = REL_TOL, abs_tol: float = ABS_TOL) -> bool:
        """Whether ``other`` is the same quantity, within tolerance.

        Values are compared after converting ``other`` to these units, so
        ``Parameter(1, "m").isclose(Parameter(1000, "mm"))`` is true.
        Tolerances follow :func:`math.isclose`. Arrays must match in shape and
        be close everywhere. Non-numeric parameters must match exactly.
        """
        other = other if isinstance(other, Parameter) else Parameter(other)
        if self.is_numeric != other.is_numeric:
            return False
        if not self.is_numeric:
            return self._unit == other._unit and bool(np.all(self._value == other._value))
        mine, theirs = self.quantity, other.quantity
        if mine.dimensionality != theirs.dimensionality:
            return False
        a = _float_array(mine.magnitude)
        b = _float_array(theirs.to(mine.units).magnitude)
        if a.shape != b.shape:
            return False
        with np.errstate(invalid="ignore", over="ignore"):
            tolerance = np.maximum(rel_tol * np.maximum(np.abs(a), np.abs(b)), abs_tol)
            finite = np.isfinite(a) & np.isfinite(b)
            return bool(np.all((a == b) | (finite & (np.abs(a - b) <= tolerance))))

    def to_builtin(self) -> Any:
        """Plain-Python form that :meth:`parse` reads back, for YAML or JSON.

        This is the most compact of ``value``, ``[value, units]`` or
        ``{value: ..., units: ..., description: ...}`` that round-trips.
        """
        value = _to_builtin(self._value)
        if not self._description:
            compact = value if self._units == "-" else [value, self._units]
            try:
                if Parameter.parse(compact)._same_as(self):
                    return compact
            except ParameterError:
                pass
        data: dict[str, Any] = {"value": value}
        if self._units != "-":
            data["units"] = self._units
        if self._description:
            data["description"] = self._description
        return data

    def _same_as(self, other: Parameter) -> bool:
        return (
            self._units == other._units
            and self._unit == other._unit
            and self.is_numeric == other.is_numeric
            and type(self._value) is type(other._value)
            and bool(np.array_equal(self._value, other._value))
        )

    # Comparison -----------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (Parameter, pint.Quantity, numbers.Number, np.ndarray)):
            return NotImplemented
        return self.isclose(other)

    __hash__ = None  # type: ignore[assignment]

    __lt__ = _comparison(operator.lt)
    __le__ = _comparison(operator.le)
    __gt__ = _comparison(operator.gt)
    __ge__ = _comparison(operator.ge)

    # Arithmetic -------------------------------------------------------------

    __add__ = _arithmetic(operator.add)
    __radd__ = _arithmetic(operator.add, reflected=True)
    __sub__ = _arithmetic(operator.sub)
    __rsub__ = _arithmetic(operator.sub, reflected=True)
    __mul__ = _arithmetic(operator.mul, align=True)
    __rmul__ = _arithmetic(operator.mul, reflected=True, align=True)
    __truediv__ = _arithmetic(operator.truediv, align=True)
    __rtruediv__ = _arithmetic(operator.truediv, reflected=True, align=True)
    __floordiv__ = _arithmetic(operator.floordiv)
    __rfloordiv__ = _arithmetic(operator.floordiv, reflected=True)
    __mod__ = _arithmetic(operator.mod)
    __rmod__ = _arithmetic(operator.mod, reflected=True)
    __pow__ = _arithmetic(operator.pow)
    __rpow__ = _arithmetic(operator.pow, reflected=True)

    def __neg__(self) -> Parameter:
        return Parameter(-self.quantity)

    def __pos__(self) -> Parameter:
        return Parameter(+self.quantity)

    def __abs__(self) -> Parameter:
        return Parameter(abs(self.quantity))

    def __round__(self, ndigits: int | None = None) -> Parameter:
        value = self.quantity.magnitude
        rounded = (
            np.round(value, ndigits or 0)
            if isinstance(value, np.ndarray)
            else round(value, ndigits)
        )
        return Parameter(rounded, self._unit, self._description)

    def __float__(self) -> float:
        return float(self.quantity)

    def __int__(self) -> int:
        return int(self.quantity)

    def __complex__(self) -> complex:
        return complex(self.quantity)

    def __bool__(self) -> bool:
        return bool(self._value)

    # Sequences and numpy ---------------------------------------------------

    def __len__(self) -> int:
        return len(self._value)

    def __getitem__(self, index: Any) -> Parameter:
        return Parameter(self._value[index], self._unit)

    def __iter__(self) -> Iterator[Parameter]:
        if not isinstance(self._value, (np.ndarray, list)):
            raise TypeError(f"{self!r} is not iterable")
        return (Parameter(item, self._unit) for item in self._value)

    def __array__(self, dtype: Any = None, copy: bool | None = None) -> np.ndarray:
        warnings.warn(
            "units are stripped when converting a Parameter to an array; "
            "use Parameter.to_numpy() to do this explicitly",
            pint.UnitStrippedWarning,
            stacklevel=2,
        )
        array = np.asarray(self._value, dtype=dtype)
        return array.copy() if copy else array

    def __array_ufunc__(self, ufunc: np.ufunc, method: str, *inputs: Any, **kwargs: Any) -> Any:
        if "out" in kwargs:
            return NotImplemented
        return _from_result(getattr(ufunc, method)(*_to_quantities(inputs), **kwargs))

    def __array_function__(
        self, func: Callable[..., Any], types: Any, args: Any, kwargs: dict[str, Any]
    ) -> Any:
        return _from_result(func(*_to_quantities(args), **_to_quantities(kwargs)))

    # Representation --------------------------------------------------------

    def __str__(self) -> str:
        return self.__format__("")

    def __format__(self, spec: str) -> str:
        if isinstance(self._value, np.ndarray) and spec:
            text = _format_array(self._value, lambda x: format(x, spec))
        elif spec:
            text = format(self._value, spec)
        else:
            text = format_value(self._value)
        return text if self._units == "-" else f"{text} {self._units}"

    def __repr__(self) -> str:
        value = self._value.tolist() if isinstance(self._value, np.ndarray) else self._value
        args = [repr(value), repr(self._units)]
        if self._description:
            args.append(f"description={self._description!r}")
        return f"Parameter({', '.join(args)})"

    def __reduce__(self) -> tuple[Any, ...]:
        return (Parameter, (self._value, self._units, self._description))

    # pydantic --------------------------------------------------------------

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(
            cls.parse,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda parameter: parameter.to_builtin(), when_used="json"
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: Any, handler: Any) -> dict[str, Any]:
        return {
            "description": "A value with units: [value, units], 'value units', "
            "{value, units, description}, or a plain value",
            "anyOf": [
                {"type": ["number", "string", "boolean", "array", "null"]},
                {
                    "type": "object",
                    "properties": {
                        "value": {},
                        "units": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["value"],
                    "additionalProperties": False,
                },
            ],
        }


@dataclass(frozen=True)
class Dimension:
    """A constraint that a parameter converts to the given units or dimensionality.

    Use it directly, or as pydantic metadata::

        class Motor(BaseModel):
            mass: Annotated[Parameter, Dimension("[mass]")]
            shaft_length: Annotated[Parameter, Dimension("mm")]
    """

    spec: str

    def __post_init__(self) -> None:
        _units.parse_dimensionality(self.spec)

    def validate(self, parameter: Parameter) -> Parameter:
        """Return ``parameter``, or raise :class:`ParameterError` if it is incompatible."""
        if not isinstance(parameter, Parameter):
            raise ParameterError(
                f"Dimension checks Parameter values, got {type(parameter).__name__}"
            )
        if not parameter.is_numeric:
            raise ParameterError(
                f"expected a number with units compatible with {self.spec!r}, "
                f"got {parameter.value!r}"
            )
        if not parameter.is_compatible_with(self.spec):
            raise ParameterError(
                f"expected units compatible with {self.spec!r}, got {parameter.units!r}"
            )
        return parameter

    def __get_pydantic_core_schema__(self, source_type: Any, handler: Any) -> Any:
        from pydantic_core import core_schema

        # None passes through, for Optional[Parameter] fields.
        return core_schema.no_info_after_validator_function(
            lambda value: value if value is None else self.validate(value), handler(source_type)
        )


def format_value(value: Any, precision: int | None = None) -> str:
    """Format a parameter value, rounding floats to ``precision`` significant figures."""

    def number(x: Any) -> str:
        if precision is not None and isinstance(x, (float, complex)):
            return f"{x:.{precision}g}"
        return str(x)

    if isinstance(value, np.ndarray):
        return _format_array(value, number)
    if isinstance(value, list):
        return f"[{', '.join(map(str, value))}]"
    return "" if value is None else number(value)


def _format_array(array: np.ndarray, number: Callable[[Any], str]) -> str:
    """Format like a Python list, eliding the middle of long axes in big arrays."""
    summarize = array.size > _SUMMARY_THRESHOLD

    def fmt(item: Any) -> str:
        if isinstance(item, np.ndarray):
            rows = list(item)
            if summarize and len(rows) > 2 * _EDGE_ITEMS:
                parts = [*map(fmt, rows[:_EDGE_ITEMS]), "...", *map(fmt, rows[-_EDGE_ITEMS:])]
            else:
                parts = list(map(fmt, rows))
            return f"[{', '.join(parts)}]"
        return number(item.item() if isinstance(item, np.generic) else item)

    return fmt(array)


# Make pint defer to Parameter in mixed operations such as ``quantity * parameter``,
# the same mechanism pint uses for xarray and pint-pandas.
# pint < 0.26 types the map as a read-only Mapping; it is a dict at runtime.
pint.compat.upcast_type_map[  # type: ignore[index, unused-ignore]
    f"{Parameter.__module__}.{Parameter.__qualname__}"
] = Parameter


def _is_numeric(value: Any) -> bool:
    if isinstance(value, np.ndarray):
        return value.dtype.kind in "iufc"
    return isinstance(value, numbers.Number) and not isinstance(value, bool)


def _normalize_value(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return value.item()
        return _read_only(np.array(value))
    if isinstance(value, (list, tuple)):
        try:
            array = np.asarray(value)
        except ValueError as error:
            raise ParameterError(f"list {value!r} is not rectangular") from error
        if array.dtype.kind in "iufc":
            return _read_only(array)
        if _mixes_numbers(value):
            raise ParameterError(f"list {value!r} mixes numbers and text")
        return list(value)
    return value


def _read_only(array: np.ndarray) -> np.ndarray:
    # Parameters are immutable, so arrays are private copies that cannot be written.
    array.flags.writeable = False
    return array


def _is_units(text: str) -> bool:
    try:
        _units.parse_units(text)
    except ParameterError:
        return False
    return True


def _number(text: str) -> int | float:
    return int(text) if re.fullmatch(r"[-+]?\d(?:_?\d)*", text) else float(text)


def _float_array(value: Any) -> np.ndarray:
    array = np.asarray(value)
    return array if array.dtype.kind in "fc" else array.astype(float)


def _mixes_numbers(items: list[Any] | tuple[Any, ...]) -> bool:
    for item in items:
        if isinstance(item, (list, tuple)):
            if _mixes_numbers(item):
                return True
        elif _is_numeric(item):
            return True
    return False


def _to_builtin(value: Any) -> Any:
    return value.tolist() if isinstance(value, np.ndarray) else value


def _operand(other: Any) -> Any:
    if isinstance(other, Parameter):
        return other.quantity
    if isinstance(other, (pint.Quantity, numbers.Number, np.ndarray, np.generic)):
        return other
    if isinstance(other, (list, tuple)):
        return np.asarray(other)
    return NotImplemented


def _to_quantities(value: Any) -> Any:
    if isinstance(value, Parameter):
        return value.quantity
    if isinstance(value, (list, tuple)):
        return type(value)(_to_quantities(item) for item in value)
    if isinstance(value, dict):
        return {key: _to_quantities(item) for key, item in value.items()}
    return value


def _from_result(result: Any) -> Any:
    if isinstance(result, pint.Quantity):
        return Parameter(result)
    if isinstance(result, tuple):
        return tuple(_from_result(item) for item in result)
    return result
