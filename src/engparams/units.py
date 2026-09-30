"""Unit parsing, formatting and SI conversion, backed by pint.

All parameters share pint's application registry, so quantities created here
interoperate with any other pint code in the same program.
"""

from __future__ import annotations

import re
from tokenize import TokenError
from typing import TYPE_CHECKING, Any

import pint
from pint.util import to_units_container

from engparams.errors import UnitError

if TYPE_CHECKING:
    from pint.util import UnitsContainer

ureg = pint.get_application_registry()

DIMENSIONLESS_TOKENS = frozenset({"", "-", "1", "dimensionless"})
"""Units strings that mean "no units"."""

SI_UNITS = frozenset(
    {
        "meter",
        "second",
        "ampere",
        "kelvin",
        "mole",
        "candela",
        "radian",
        "steradian",
        "newton",
        "pascal",
        "joule",
        "watt",
        "coulomb",
        "volt",
        "farad",
        "ohm",
        "siemens",
        "weber",
        "tesla",
        "henry",
        "hertz",
        "lumen",
        "lux",
        "becquerel",
        "gray",
        "sievert",
        "katal",
    }
)
"""Named coherent SI units, which SI conversion keeps (minus any prefix)."""

SI_DERIVED_UNITS: list[str] = ["newton", "pascal", "joule", "watt"]
"""Units that a non-SI unit converts to when their dimensionality matches.

This is what turns psi into Pa and kWh into J rather than into base units.
Earlier entries win. Append to this list to add your own preferences.
"""

SYMBOLS: dict[str, str] = {"turn": "rev", "revolution": "rev"}
"""Symbol overrides used when formatting units, keyed by pint unit name."""

# "." between unit names means multiplication, as in "N.m". A "." followed by a
# digit is a decimal point in an exponent and is left alone.
_PRODUCT = re.compile(r"(?<=\S)\.(?=[^\d\s.])")
_OPERATOR_SPACE = re.compile(r"\s*(\*\*|[*/^()])\s*")
_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", "0123456789+-")
_SUPERSCRIPT = re.compile(r"[⁺⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+")
_EXPONENT_THEN_UNIT = re.compile(r"(\^[-+]?\d+(?:\.\d+)?)(?=[^\d\s*/^().])")

# pint's parser skips unknown characters and doubled operators ("kg$" parses as kg),
# so typos are rejected before they get that far.
_INVALID = re.compile(r"[^\w\s.*/^()·°%‰+\-⁺⁻]|\.\.|//|\*{3}|^[.*/^]|[.*/^+-]$")

_PARSE_ERRORS = (
    pint.PintError,
    ValueError,
    TypeError,
    AttributeError,
    SyntaxError,
    TokenError,
    AssertionError,  # pint asserts on some malformed input, e.g. "5 -"
)

if "rev" not in ureg:
    ureg.define("@alias revolution = rev")


def define(definition: str) -> None:
    """Add a unit, prefix or alias to the registry using pint's syntax.

    For example ``define("smoot = 1.7018 * meter")`` or
    ``define("@alias inch = inches")``.
    """
    ureg.define(definition)


def parse_units(units: str | pint.Unit | None) -> pint.Unit:
    """Parse a units expression such as ``"kN.m"``, ``"mm/s^2"`` or ``"-"``."""
    if isinstance(units, pint.Unit):
        return units
    text = "" if units is None else str(units).strip()
    if text in DIMENSIONLESS_TOKENS:
        return ureg.dimensionless
    expression = _expression(text)
    try:
        return ureg.parse_units(expression)
    except _PARSE_ERRORS as error:
        raise UnitError(f"invalid units {text!r}: {error}") from error


def _expression(text: str) -> str:
    """Translate a units expression to pint syntax, rejecting typos and ambiguity."""
    if match := _INVALID.search(text):
        raise UnitError(f"invalid units {text!r}: unexpected {match.group()!r}")
    expression = _OPERATOR_SPACE.sub(r"\1", _PRODUCT.sub("*", text.replace("·", "*")))
    # Write superscript exponents out, making products after them explicit: "m²K" is m^2*K.
    expression = _SUPERSCRIPT.sub(lambda m: "^" + m.group().translate(_SUPERSCRIPTS), expression)
    expression = _EXPONENT_THEN_UNIT.sub(r"\1*", expression)
    if re.search(r"\s", expression):
        # pint reads a space as multiplication, so "deg C" would be degree coulombs.
        raise UnitError(f"invalid units {text!r}: use '.' to multiply units, as in 'N.m'")
    divided = [False]  # whether a "/" has been seen, per level of parentheses
    for index, char in enumerate(expression):
        if char == "(":
            divided.append(False)
        elif char == ")" and len(divided) > 1:
            divided.pop()
        elif char == "/":
            divided[-1] = True
        elif char == "*" and divided[-1] and "**" not in expression[max(index - 1, 0) : index + 2]:
            # "W/m.K" reads as W.K/m, which is rarely what was meant.
            raise UnitError(
                f"invalid units {text!r}: ambiguous, put the units after '/' in "
                "parentheses, as in 'W/(m.K)'"
            )
    return expression


def parse_dimensionality(spec: str | pint.Unit) -> UnitsContainer:
    """Return the dimensionality of a units expression or a ``"[length]"`` style spec."""
    if isinstance(spec, str) and spec.strip().startswith("["):
        try:
            return ureg.get_dimensionality(spec.strip())
        except _PARSE_ERRORS as error:
            raise UnitError(f"invalid dimensionality {spec!r}: {error}") from error
    return parse_units(spec).dimensionality


def format_units(unit: pint.Unit) -> str:
    """Format a unit compactly with symbols, e.g. ``"kg/(m.s^2)"`` or ``"-"``."""
    numerator: list[str] = []
    denominator: list[str] = []
    for name, exponent in _atoms(unit).items():
        symbol = _symbol(name)
        term = symbol if abs(exponent) == 1 else f"{symbol}^{_format_exponent(abs(exponent))}"
        (numerator if exponent > 0 else denominator).append(term)
    if not numerator and not denominator:
        return "-"
    text = ".".join(numerator) or "1"
    if denominator:
        joined = ".".join(denominator)
        text += f"/({joined})" if len(denominator) > 1 else f"/{joined}"
    return text


def align_units(unit: Any, reference: Any) -> pint.Unit:
    """``unit`` with each part expressed in the part of ``reference`` of the same dimension.

    For example ``mm/s`` aligned to ``m`` is ``m/s``. Dimensionless parts such
    as ``deg`` or ``%`` are left alone.
    """
    targets: dict[Any, str] = {}
    for name in _atoms(reference):
        dimensionality = ureg.get_dimensionality(name)
        if dimensionality:
            targets.setdefault(dimensionality, name)
    result = ureg.dimensionless
    for name, exponent in _atoms(unit).items():
        target = targets.get(ureg.get_dimensionality(name), name)
        result *= ureg.Unit(target) ** exponent
    return result


def si_units(unit: pint.Unit) -> pint.Unit:
    """Return the coherent SI unit equivalent to ``unit``.

    Each unit in the expression is converted on its own, so named SI units
    survive: ``kN.mm`` becomes ``N.m`` rather than ``kg.m^2/s^2``. Other units
    become a unit from :data:`SI_DERIVED_UNITS` when one has the same
    dimensionality (``psi`` becomes ``Pa``), or SI base units otherwise
    (``rev/min`` becomes ``rad/s``).
    """
    result = ureg.dimensionless
    for name, exponent in _atoms(unit).items():
        result *= _si_atom(name) ** exponent
    return result


def _si_atom(name: str) -> pint.Unit:
    candidates = ureg.parse_unit_name(name)
    root = candidates[0][1] if candidates else name
    if root == "gram":
        return ureg.kilogram
    if root in SI_UNITS:
        return ureg.Unit(root)
    dimensionality = ureg.get_dimensionality(name)
    for derived in SI_DERIVED_UNITS:
        if ureg.get_dimensionality(derived) == dimensionality:
            return ureg.Unit(derived)
    return ureg.get_base_units(name)[1]


def _symbol(name: str) -> str:
    # pint's symbol for micro is U+00B5 or U+03BC depending on what it parsed
    # first, so normalise to the Greek letter that SI specifies.
    symbol = (SYMBOLS.get(name) or ureg.get_symbol(name)).replace("\u00b5", "\u03bc")
    # Some symbols read back as a different unit ("kt" is a knot, not a
    # kilotonne) or not at all, so fall back to the name to stay lossless.
    try:
        if _atoms(parse_units(symbol)) == {name: 1}:
            return symbol
    except UnitError:
        pass
    return name


def _atoms(unit: pint.Unit) -> dict[str, Any]:
    return dict(to_units_container(unit, ureg).items())


def _format_exponent(exponent: float) -> str:
    return str(int(exponent)) if float(exponent).is_integer() else f"{exponent:g}"
