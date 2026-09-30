import copy
import math
import pickle

import numpy as np
import pint
import pytest

from engparams import DimensionalityError, Parameter, ParameterError, UnitError, ureg

# Construction ---------------------------------------------------------------


def test_defaults_to_dimensionless():
    parameter = Parameter(5)
    assert (parameter.value, parameter.units, parameter.description) == (5, "-", "")


@pytest.mark.parametrize("units", [None, "", "-", "1", "dimensionless", " - "])
def test_dimensionless_units_are_normalised(units):
    assert Parameter(5, units).units == "-"


def test_units_text_is_kept_as_written():
    assert Parameter(3, " N.mm ").units == "N.mm"


def test_lists_become_arrays():
    parameter = Parameter([1, 2, 3], "mm")
    assert isinstance(parameter.value, np.ndarray)
    np.testing.assert_array_equal(parameter.value, [1, 2, 3])


def test_numpy_scalars_become_python_scalars():
    assert type(Parameter(np.float64(1.5), "m").value) is float
    assert type(Parameter(np.array(2), "m").value) is int


def test_non_numeric_values():
    assert not Parameter("RC-100").is_numeric
    assert not Parameter(True).is_numeric
    assert Parameter(["a", "b"]).value == ["a", "b"]


def test_non_numeric_value_cannot_have_units():
    with pytest.raises(ParameterError, match="cannot have units"):
        Parameter("text", "m")


def test_invalid_units_raise():
    with pytest.raises(UnitError, match="'foo'"):
        Parameter(1, "foo")


def test_mixed_list_raises():
    with pytest.raises(ParameterError, match="mixes numbers and text"):
        Parameter([1, "m", 2])


def test_ragged_list_raises():
    with pytest.raises(ParameterError, match="not rectangular"):
        Parameter([[1, 2], [3]])


def test_from_quantity():
    assert Parameter(ureg.Quantity(2, "kN")) == Parameter(2000, "N")
    converted = Parameter(ureg.Quantity(2, "m"), "mm")
    assert (converted.value, converted.units) == (2000, "mm")
    assert Parameter.from_quantity(ureg.Quantity(1, "s"), "t").description == "t"


def test_from_parameter():
    original = Parameter(1, "inch")
    assert Parameter(original).units == "inch"
    assert Parameter(original, "mm") == Parameter(25.4, "mm")
    assert Parameter(original, "mm").units == "mm"


def test_is_immutable():
    parameter = Parameter(1, "m")
    with pytest.raises(AttributeError):
        parameter.value = 2
    with pytest.raises(AttributeError):
        parameter.other = 2


def test_is_unhashable():
    with pytest.raises(TypeError):
        hash(Parameter(1, "m"))


# Parsing ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "value", "units"),
    [
        ([150, "mm"], 150, "mm"),
        ((150, "mm"), 150, "mm"),
        ([[0, 120, 240], "deg"], [0, 120, 240], "deg"),
        ("150 mm", 150, "mm"),
        ("  -1.5e3 N.m ", -1500.0, "N.m"),
        ("10mm", 10, "mm"),
        ("20 degC", 20, "degC"),
        ("1_000 N", 1000, "N"),
        ("1e-3", "1e-3", "-"),
        ("0042", "0042", "-"),
        ("1.2.3", "1.2.3", "-"),
        ("2024-01-01", "2024-01-01", "-"),
        ("12:30", "12:30", "-"),
        (["1e-3", "m"], 0.001, "m"),
        (["1_000", "m"], 1000, "m"),
        ({"value": 150, "units": "mm"}, 150, "mm"),
        ({"value": 150}, 150, "-"),
        (50, 50, "-"),
        ([1, 2], [1, 2], "-"),
        (["string", "-"], "string", "-"),
        (["red", "blue"], ["red", "blue"], "-"),
        (["2nd", "floor"], ["2nd", "floor"], "-"),
        ("RC-100", "RC-100", "-"),
        (True, True, "-"),
        (None, None, "-"),
    ],
)
def test_parse(data, value, units):
    parameter = Parameter.parse(data)
    assert parameter.units == units
    if isinstance(parameter.value, np.ndarray):
        np.testing.assert_array_equal(parameter.value, value)
    else:
        assert parameter.value == value


def test_parse_description():
    parameter = Parameter.parse({"value": 3, "units": "kg", "description": "Mass"})
    assert parameter.description == "Mass"
    assert Parameter.parse({"value": 3, "description": None}).description == ""


def test_parse_passes_through_parameters_and_quantities():
    parameter = Parameter(1, "m")
    assert Parameter.parse(parameter) is parameter
    assert Parameter.parse(ureg.Quantity(1, "m")) == parameter


@pytest.mark.parametrize(
    ("data", "match"),
    [
        ([1, "foo"], "invalid units 'foo'"),
        ("2nd floor", "cannot read '2nd floor'"),
        ("3 m / 2 s", "cannot read '3 m / 2 s'"),
        ("1 ft 6 in", "use '.' to multiply units"),
        ("1 m$", "unexpected '\\$'"),
        (["1_", "mm"], "cannot read '1_' as a number"),
        ({"value": 1, "unit": "m"}, "at most 'units' and 'description'"),
        ({"units": "m"}, "needs a 'value' key"),
        (object(), "cannot make a parameter from object"),
    ],
)
def test_parse_errors(data, match):
    with pytest.raises(ParameterError, match=match):
        Parameter.parse(data)


# Comparison -------------------------------------------------------------------


def test_equality_converts_units():
    assert Parameter(1, "m") == Parameter(1000, "mm")
    assert Parameter(1, "lbf") == Parameter(4.4482216152605, "N")
    assert Parameter(1, "psi") == Parameter(6894.757293168361, "Pa")
    assert Parameter(36.487, "MPa") == Parameter(36487, "kPa")


def test_inequality():
    # Regressions: 0.1 reported all of these as equal.
    assert Parameter(1, "m") != Parameter(5, "m")
    assert Parameter(5, "m") != Parameter(1, "m")
    assert Parameter(1, "m") != 100
    assert Parameter([1.0, 2.0], "m") != Parameter([1.0, 5.0], "m")


def test_equality_across_dimensions_is_false():
    assert Parameter(1, "m") != Parameter(1, "s")
    assert Parameter(1, "m") != 1


def test_equality_with_numbers_and_quantities():
    assert Parameter(5) == 5
    assert Parameter(5, "-") == 5.0
    assert Parameter(1, "m") == ureg.Quantity(100, "cm")


def test_equality_with_other_types():
    assert Parameter(1, "m") != None  # noqa: E711
    assert Parameter(1, "m") != "1 m"
    assert Parameter("text") == Parameter("text")
    assert Parameter("text") != Parameter("other")
    assert Parameter("5") != Parameter(5)


def test_equality_tolerance():
    assert Parameter(0.1, "m") + Parameter(0.2, "m") == Parameter(0.3, "m")
    assert Parameter(1, "m") != Parameter(1.001, "m")
    assert Parameter(1, "m").isclose(Parameter(1.001, "m"), rel_tol=1e-2)
    assert Parameter(0, "m").isclose(Parameter(1e-12, "m"), abs_tol=1e-9)
    assert not Parameter(0, "m").isclose(Parameter(1e-12, "m"))
    assert Parameter(math.inf, "m") == Parameter(math.inf, "m")
    assert Parameter(math.nan, "m") != Parameter(math.nan, "m")


def test_array_equality():
    assert Parameter([1.0, 2.0], "m") == Parameter([1000, 2000], "mm")
    assert Parameter([1, 1], "m") != Parameter(1, "m")
    data = np.random.default_rng(0).random((10, 10))
    assert Parameter(data, "m") == Parameter(data, "mm") * 1000


def test_ordering_returns_bools():
    # Regression: 0.1 returned a truthy Parameter from every comparison.
    assert (Parameter(1, "m") > Parameter(5, "m")) is False
    assert Parameter(40, "m") > Parameter(300, "mm")
    assert Parameter(300, "mm") < Parameter(1, "ft")
    assert Parameter(1, "m") <= Parameter(100, "cm")
    assert Parameter(1, "m") >= Parameter(100, "cm")


def test_ordering_arrays_is_elementwise():
    np.testing.assert_array_equal(Parameter([1, 5], "m") > Parameter(2, "m"), [False, True])


def test_ordering_across_dimensions_raises():
    with pytest.raises(DimensionalityError):
        _ = Parameter(1, "m") < Parameter(1, "s")


def test_ordering_non_numeric_raises():
    with pytest.raises(TypeError):
        _ = Parameter("a") < Parameter("b")


# Arithmetic -------------------------------------------------------------------


def test_addition_uses_left_units():
    result = Parameter(1, "m") + Parameter(25, "mm")
    assert (result.value, result.units) == (1.025, "m")
    assert Parameter(12, "ft") + Parameter(1, "m") == Parameter(4.6576, "m")


def test_subtraction():
    assert Parameter(1, "m") - Parameter(25, "mm") == Parameter(0.975, "m")
    assert 5 - Parameter(2) == Parameter(3)


def test_multiplication_combines_units():
    assert (Parameter(1, "m") * Parameter(25, "mm")).to("m^2") == Parameter(0.025, "m^2")
    assert Parameter(3, "N") * Parameter(2, "m") == Parameter(6, "N.m")
    assert (Parameter(3, "N") * Parameter(2, "m")).units == "N.m"
    assert 2 * Parameter(3, "m") == Parameter(6, "m")


def test_division_combines_units():
    speed = Parameter(10, "m") / Parameter(2, "s")
    assert (speed.value, speed.units) == (5.0, "m/s")
    assert Parameter(1, "m") / Parameter(25, "mm") == Parameter(40)
    inverse = 2 / Parameter(4, "m")
    assert (inverse.value, inverse.units) == (0.5, "1/m")


def test_floor_division_and_modulo():
    assert Parameter(36.487, "MPa") // Parameter(10, "MPa") == Parameter(3)
    assert Parameter(7, "m") % Parameter(2, "m") == Parameter(1, "m")
    assert 7 // Parameter(2) == Parameter(3)
    assert 7 % Parameter(2) == Parameter(1)


def test_power():
    assert Parameter(2, "m") ** 2 == Parameter(4, "m^2")
    assert 2 ** Parameter(3) == Parameter(8)


def test_unary_operators():
    assert -Parameter(1, "m") == Parameter(-1, "m")
    assert +Parameter(1, "m") == Parameter(1, "m")
    assert abs(Parameter(-1, "m")) == Parameter(1, "m")


def test_round():
    rounded = round(Parameter(1.23456, "m", "length"), 2)
    assert (rounded.value, rounded.units, rounded.description) == (1.23, "m", "length")
    np.testing.assert_array_equal(round(Parameter([1.26, 2.5], "m"), 1).value, [1.3, 2.5])


def test_sum():
    assert sum([Parameter(1, "m"), Parameter(2, "m")]) == Parameter(3, "m")


def test_arithmetic_across_dimensions_raises():
    with pytest.raises(DimensionalityError):
        _ = Parameter(1, "m") + Parameter(1, "s")
    with pytest.raises(DimensionalityError):
        _ = Parameter(1, "m") + 1


def test_arithmetic_on_text_raises():
    with pytest.raises(TypeError):
        _ = Parameter("a") + Parameter("b")


def test_arithmetic_with_unsupported_types_raises():
    with pytest.raises(TypeError):
        _ = Parameter(1, "m") + "1 m"


def test_arithmetic_with_quantities_returns_parameters():
    assert isinstance(Parameter(3, "m/s") * ureg.Quantity(2, "s"), Parameter)
    assert isinstance(ureg.Quantity(2, "s") * Parameter(3, "m/s"), Parameter)
    assert ureg.Quantity(2, "s") * Parameter(3, "m/s") == Parameter(6, "m")
    assert ureg.Quantity(1, "m") + Parameter(1, "m") == Parameter(2, "m")


def test_arithmetic_with_lists_and_arrays():
    assert Parameter(2, "m") * [1, 2] == Parameter([2, 4], "m")
    assert np.array([1, 2]) * Parameter(2, "m") == Parameter([2, 4], "m")


# numpy ---------------------------------------------------------------------------


def test_numpy_ufuncs():
    assert np.sin(Parameter(30, "deg")) == Parameter(0.5)
    assert np.sqrt(Parameter(4, "m^2")) == Parameter(2, "m")
    assert np.hypot(Parameter(3, "m"), Parameter(400, "cm")) == Parameter(5, "m")


def test_numpy_functions():
    assert np.mean(Parameter([1, 2, 3], "mm")) == Parameter(2, "mm")
    assert np.linalg.norm(Parameter([3, 4], "m")) == Parameter(5, "m")
    stacked = np.concatenate([Parameter([1], "m"), Parameter([2000], "mm")])
    assert stacked == Parameter([1, 2], "m")


def test_numpy_out_argument_is_rejected():
    with pytest.raises(TypeError):
        np.add(Parameter(1, "m"), Parameter(1, "m"), out=np.empty(()))


# Conversion ------------------------------------------------------------------


def test_to_keeps_requested_units_text():
    converted = Parameter(1, "m").to("mm")
    assert (converted.value, converted.units) == (1000, "mm")


def test_to_keeps_description():
    assert Parameter(1, "m", "x").to("mm").description == "x"
    assert Parameter(1, "km", "x").to_si().description == "x"


def test_to_incompatible_raises():
    with pytest.raises(DimensionalityError):
        Parameter(1, "m").to("s")


def test_to_si_leaves_text_alone():
    parameter = Parameter("RC-100")
    assert parameter.to_si() is parameter


def test_to_numpy():
    np.testing.assert_array_equal(Parameter([1, 2], "m").to_numpy("mm"), [1000, 2000])
    assert Parameter(1, "m").to_numpy().shape == ()


def test_is_compatible_with():
    parameter = Parameter(1, "psi")
    assert parameter.is_compatible_with("Pa")
    assert parameter.is_compatible_with("[pressure]")
    assert parameter.is_compatible_with(Parameter(1, "bar"))
    assert not parameter.is_compatible_with("m")
    assert not parameter.is_compatible_with(Parameter("text"))
    assert not Parameter("text").is_compatible_with("-")
    with pytest.raises(UnitError):
        parameter.is_compatible_with("foo")


def test_dimensionality():
    assert Parameter(1, "mm/s").dimensionality == ureg.parse_units("m/s").dimensionality


def test_quantity():
    quantity = Parameter(2, "mm").quantity
    assert quantity == ureg.Quantity(2, "mm")
    with pytest.raises(TypeError, match="not numeric"):
        _ = Parameter("text").quantity


def test_float_and_int():
    assert float(Parameter(30, "deg")) == pytest.approx(math.pi / 6)
    assert int(Parameter(3.7)) == 3
    assert complex(Parameter(2)) == 2 + 0j
    with pytest.raises(DimensionalityError):
        float(Parameter(1, "mm"))


def test_bool():
    assert not Parameter(0, "m")
    assert Parameter(2, "m")
    assert not Parameter("")
    with pytest.raises(ValueError, match="ambiguous"):
        bool(Parameter([1, 2], "m"))


# Sequences ---------------------------------------------------------------------


def test_sequence_protocol():
    angles = Parameter([0, 120, 240], "deg")
    assert len(angles) == 3
    assert angles[1] == Parameter(120, "deg")
    assert angles[1:] == Parameter([120, 240], "deg")
    assert list(angles) == [Parameter(0, "deg"), Parameter(120, "deg"), Parameter(240, "deg")]
    assert list(Parameter(["a", "b"])) == [Parameter("a"), Parameter("b")]


def test_scalars_are_not_sequences():
    with pytest.raises(TypeError):
        iter(Parameter(1, "m"))
    with pytest.raises(TypeError):
        len(Parameter(1, "m"))


# Representation -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("parameter", "text"),
    [
        (Parameter(1, "m"), "1 m"),
        (Parameter(0.5), "0.5"),
        (Parameter([0, 120, 240], "deg"), "[0, 120, 240] deg"),
        (Parameter([[1, 2], [3, 4]], "m"), "[[1, 2], [3, 4]] m"),
        (Parameter(np.arange(30), "s"), "[0, 1, 2, ..., 27, 28, 29] s"),
        (Parameter("RC-100"), "RC-100"),
        (Parameter(["a", "b"]), "[a, b]"),
        (Parameter(None), ""),
    ],
)
def test_str(parameter, text):
    assert str(parameter) == text


def test_format_spec():
    assert f"{Parameter(3.14159, 'm'):.2f}" == "3.14 m"
    assert f"{Parameter([1.234, 2.5], 'm'):.1f}" == "[1.2, 2.5] m"
    assert f"{Parameter(0.5):.0%}" == "50%"
    assert f"{Parameter('ab'):>4}" == "  ab"


def test_repr():
    assert repr(Parameter(1, "m")) == "Parameter(1, 'm')"
    assert repr(Parameter([1, 2], "m", "x")) == "Parameter([1, 2], 'm', description='x')"
    assert repr(Parameter("RC-100")) == "Parameter('RC-100', '-')"


@pytest.mark.parametrize(
    "parameter",
    [Parameter(1, "m"), Parameter([1, 2], "N.m", "torque"), Parameter("text"), Parameter(None)],
)
def test_pickle_and_deepcopy(parameter):
    assert pickle.loads(pickle.dumps(parameter)) == parameter
    assert copy.deepcopy(parameter) == parameter
    assert pickle.loads(pickle.dumps(parameter)).description == parameter.description


@pytest.mark.parametrize(
    ("parameter", "builtin"),
    [
        (Parameter(1, "m"), [1, "m"]),
        (Parameter([1, 2], "m"), [[1, 2], "m"]),
        (Parameter(0.5), 0.5),
        (Parameter([1, 2]), [1, 2]),
        (Parameter("text"), "text"),
        (Parameter(True), True),
        (Parameter("10 mm"), {"value": "10 mm"}),
        (Parameter(["a", "-"]), {"value": ["a", "-"]}),
        (Parameter(3, "kg", "Mass"), {"value": 3, "units": "kg", "description": "Mass"}),
        (Parameter(3, "-", "Ratio"), {"value": 3, "description": "Ratio"}),
    ],
)
def test_to_builtin_round_trips(parameter, builtin):
    assert parameter.to_builtin() == builtin
    restored = Parameter.parse(builtin)
    assert restored == parameter
    assert (restored.units, restored.description) == (parameter.units, parameter.description)


# Regressions from review -----------------------------------------------------


def test_scaling_keeps_dimensionless_units():
    assert (Parameter(90, "deg") * 2).units == "deg"
    assert (Parameter(90, "deg") * 2).value == 180
    assert (2 * Parameter(10, "%")).units == "%"
    assert (Parameter(10, "mm/m") / 2).units == "mm/m"


def test_products_express_like_units_in_the_left_operand():
    area = Parameter(1, "m") * Parameter(25, "mm")
    assert (area.value, area.units) == (0.025, "m^2")
    lever = Parameter(1, "kN.m") / Parameter(2, "N")
    assert (lever.value, lever.units) == (500, "m")


def test_infinity_is_only_equal_to_itself():
    inf = float("inf")
    assert Parameter(inf, "m") != Parameter(1, "m")
    assert Parameter(inf) != Parameter(-inf)
    assert Parameter(-inf, "m") == Parameter(-inf, "m")
    assert Parameter([1.0, inf], "m") == Parameter([1.0, inf], "m")


def test_equality_with_decimals_and_big_ints():
    from decimal import Decimal

    assert Parameter(Decimal("1.5"), "m") == Parameter(1.5, "m")
    assert Parameter(10**20, "m") == Parameter(10**20, "m")
    assert Parameter(10**20, "m") != Parameter(10**20 + 10**12, "m")


def test_arrays_are_private_and_read_only():
    data = np.array([1.0, 2.0])
    parameter = Parameter(data, "m")
    data[0] = 99
    assert parameter.value[0] == 1.0
    with pytest.raises(ValueError, match="read-only"):
        parameter.value[0] = 5
    assert (parameter * 2).value[0] == 2.0


def test_copying_a_parameter_keeps_its_description():
    assert Parameter(Parameter(1, "m", "reach")).description == "reach"
    assert Parameter(Parameter(1, "m", "reach"), description="").description == ""


def test_units_survive_round_trips_when_pint_symbols_are_ambiguous():
    # pint's symbol for kilotonne is "kt", which reads back as a knot.
    heavy = Parameter(5, "kilotonne") * 1
    for restored in (
        pickle.loads(pickle.dumps(heavy)),
        Parameter.parse(heavy.to_builtin()),
    ):
        assert restored == heavy
        assert restored.unit == heavy.unit


def test_array_conversion_strips_units_with_a_warning():
    with pytest.warns(pint.UnitStrippedWarning):
        array = np.asarray(Parameter([1, 2], "m"))
    np.testing.assert_array_equal(array, [1, 2])


def test_complex_values_respect_precision():
    from engparams.parameter import format_value

    assert format_value(1 / 3 + 2j, 3) == "0.333+2j"
