import math

import pytest

from engparams import Parameter, UnitError, define, ureg
from engparams import units as units_module
from engparams.units import format_units, parse_dimensionality, parse_units, si_units


@pytest.mark.parametrize("text", [None, "", " ", "-", "1", "dimensionless"])
def test_dimensionless_tokens(text):
    assert parse_units(text) == ureg.dimensionless


@pytest.mark.parametrize(
    ("text", "pint_text"),
    [
        ("N.m", "N*m"),
        ("N·m", "N*m"),
        ("kN.mm/s", "kN*mm/s"),
        ("kg/(m.s^2)", "kg/(m*s**2)"),
        ("m^2.s", "m**2*s"),
        ("m^0.5", "m**0.5"),
        ("m^-1", "1/m"),
        ("m^+2", "m**2"),
        ("kg * m ** 2", "kg*m**2"),
        ("°C", "degC"),
        ("µm", "um"),
        ("Ω", "ohm"),
        ("m²", "m**2"),
        ("m²K", "m**2*K"),
        ("W/(m².K)", "W/(m**2*K)"),
        ("m·s⁻¹", "m/s"),
        ("%", "percent"),
        ("rev/min", "revolution/minute"),
    ],
)
def test_parse_units_syntax(text, pint_text):
    assert parse_units(text) == ureg.parse_units(pint_text)


@pytest.mark.parametrize(
    "text", ["foo", "m/", "10 mm", "(m", "m^x", ".m", "kg//s", "m..s", "kg$", "m***2", "N.mm."]
)
def test_invalid_units_raise_unit_error(text):
    with pytest.raises(UnitError, match="invalid units"):
        parse_units(text)


@pytest.mark.parametrize("text", ["m s", "deg C", "N m"])
def test_space_is_not_multiplication(text):
    # pint would read "deg C" as degree coulombs.
    with pytest.raises(UnitError, match=r"use '\.' to multiply units"):
        parse_units(text)


@pytest.mark.parametrize("text", ["W/m.K", "W/m^2.K", "1/s.m", "W/m*K", "W/m²K"])
def test_product_after_division_is_ambiguous(text):
    with pytest.raises(UnitError, match="ambiguous"):
        parse_units(text)


@pytest.mark.parametrize(
    ("text", "pint_text"),
    [("W/(m.K)", "W/(m*K)"), ("(W/m).K", "W*K/m"), ("m/s/s", "m/s**2"), ("N.m/s", "N*m/s")],
)
def test_unambiguous_division(text, pint_text):
    assert parse_units(text) == ureg.parse_units(pint_text)


@pytest.mark.parametrize("name", ["kilometric_ton", "hectobar", "milliinch", "permille"])
def test_formatted_units_read_back_as_the_same_unit(name):
    # pint's symbols for these ("kt", "hbar", "min") are other units.
    unit = ureg.Unit(name)
    assert parse_units(format_units(unit)) == unit


@pytest.mark.parametrize(
    ("text", "formatted"),
    [
        ("m/s", "m/s"),
        ("N.m", "N.m"),
        ("kg/m/s^2", "kg/(m.s^2)"),
        ("1/s", "1/s"),
        ("-", "-"),
        ("m.m", "m^2"),
        ("m^0.5", "m^0.5"),
        ("rev/min", "rev/min"),
        ("degC", "°C"),
        ("um", "μm"),
    ],
)
def test_format_units(text, formatted):
    assert format_units(parse_units(text)) == formatted


@pytest.mark.parametrize(
    "text",
    ["m/s", "kN.mm/s", "kg/mm^3", "psi", "rpm", "degC", "um", "kWh", "lbf.ft", "m^-2", "%", "rev"],
)
def test_format_units_round_trips(text):
    unit = parse_units(text)
    assert parse_units(format_units(unit)) == unit


# Factors are from their definitions, independent of pint's tables.
@pytest.mark.parametrize(
    ("units", "si", "factor"),
    [
        ("mm", "m", 1e-3),
        ("N.mm", "N.m", 1e-3),
        ("kN.mm/s", "N.m/s", 1.0),
        ("kg/mm^3", "kg/m^3", 1e9),
        ("mm/min^2", "m/s^2", 1e-3 / 3600),
        ("deg/min", "rad/s", math.pi / 180 / 60),
        ("rev/min", "rad/s", 2 * math.pi / 60),
        ("rpm", "rad/s", 2 * math.pi / 60),
        ("rev/hour", "rad/s", 2 * math.pi / 3600),
        ("psi", "Pa", 4.4482216152605 / 0.0254**2),
        ("ksi", "Pa", 4448.2216152605 / 0.0254**2),
        ("bar", "Pa", 1e5),
        ("MPa", "Pa", 1e6),
        ("kWh", "J", 3.6e6),
        ("hp", "W", 550 * 4.4482216152605 * 0.3048),
        ("lbf", "N", 4.4482216152605),
        ("lbf.ft", "N.m", 4.4482216152605 * 0.3048),
        ("g/cm^3", "kg/m^3", 1e3),
        ("gal", "m^3", 231 * 0.0254**3),
        ("l", "m^3", 1e-3),
        ("inch", "m", 0.0254),
        ("mph", "m/s", 1609.344 / 3600),
        ("kHz", "Hz", 1e3),
        ("lb", "kg", 0.45359237),
        ("slug", "kg", 4.4482216152605 / 0.3048),
        ("tonne", "kg", 1e3),
        ("%", "-", 0.01),
        ("m^-1", "1/m", 1.0),
        ("-", "-", 1.0),
    ],
)
def test_to_si(units, si, factor):
    result = Parameter(1, units).to_si()
    assert result.units == si
    assert result.value == pytest.approx(factor, rel=1e-12)


def test_to_si_offset_temperature():
    assert Parameter(20, "degC").to_si() == Parameter(293.15, "K")


def test_si_derived_units_are_configurable(monkeypatch):
    assert format_units(si_units(parse_units("mA.h"))) == "A.s"
    assert format_units(si_units(parse_units("mAh"))) == "A.s"
    monkeypatch.setattr(units_module, "SI_DERIVED_UNITS", ["coulomb"])
    assert format_units(si_units(parse_units("mAh"))) == "C"


def test_symbols_are_configurable(monkeypatch):
    monkeypatch.setitem(units_module.SYMBOLS, "inch", "inch")
    assert (Parameter(1, "inch") * Parameter(2, "inch")).units == "inch^2"


def test_parse_dimensionality():
    assert parse_dimensionality("[length]/[time]") == parse_units("m/s").dimensionality
    assert parse_dimensionality("mm") == parse_dimensionality("[length]")
    with pytest.raises(UnitError, match="invalid dimensionality"):
        parse_dimensionality("[length")


def test_define_adds_units():
    define("test_cubit = 0.4572 * meter")
    assert Parameter(2, "test_cubit").to_si() == Parameter(0.9144, "m")
