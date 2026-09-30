import copy
import io
import json
import pickle

import numpy as np
import pytest
import yaml

from parameter import DimensionalityError, Parameter, ParameterError, Parameters, UnitError


def test_reads_every_leaf_form(params):
    expected = {
        "singlename": Parameter(1, "m"),
        "nacelle_mass": Parameter(1500, "g"),
        "arm_reference_angles.1": Parameter(120, "deg"),
        "distal_cogs": Parameter(0.5),
        "end_affector_cog.y": Parameter(-1, "mm"),
        "string_parameter": Parameter("string"),
        "pure_string_parameter": Parameter("string"),
        "link_lengths": Parameter([300, 250, 120], "mm"),
        "max_speed": Parameter(1500, "rpm"),
        "tolerance": Parameter(0.001, "mm"),
        "payload": Parameter(2.5, "kg", "Rated payload"),
        "gear_ratio": Parameter(50),
        "enabled": Parameter(True),
    }
    for path, parameter in expected.items():
        assert params[path] == parameter, path
        assert params[path].units == parameter.units, path
    assert params["payload"].description == "Rated payload"


def test_yaml_reads_exponents_without_a_decimal_point_as_floats():
    params = Parameters.from_yaml(io.StringIO("a: 1e-3\nb: [2E+3, mm]\nc: '1e-3'\nd: 1_000"))
    assert params["a"].value == 0.001
    assert params["b"].value == 2000.0
    assert params["c"].value == "1e-3", "quoted numbers are text"
    assert params["d"].value == 1000


def test_from_yaml_accepts_streams_and_empty_files():
    assert Parameters.from_yaml(io.StringIO("x: [1, m]"))["x"] == Parameter(1, "m")
    assert len(Parameters.from_yaml(io.StringIO(""))) == 0


def test_from_yaml_rejects_non_mappings():
    with pytest.raises(ParameterError, match="expected a mapping at the top level"):
        Parameters.from_yaml(io.StringIO("- 1\n- 2"))


def test_errors_report_their_location():
    with pytest.raises(UnitError) as error:
        Parameters({"motor": {"shaft": {"length": [1, "kgg"]}}})
    assert str(error.value).startswith("motor.shaft.length: invalid units 'kgg'")
    assert error.value.path == "motor.shaft.length"
    with pytest.raises(ParameterError, match=r"^arm\.angles: list .* mixes numbers and text"):
        Parameters({"arm": {"angles": [1, "deg", 2]}})


def test_rejects_non_mapping_data():
    with pytest.raises(ParameterError, match="expected a mapping"):
        Parameters([1, 2])  # type: ignore[arg-type]


@pytest.mark.parametrize("key", ["", "a.b"])
def test_rejects_invalid_keys(key):
    with pytest.raises(ParameterError, match="invalid key"):
        Parameters({key: 1})


def test_keys_are_strings():
    params = Parameters({0: [1, "m"]})
    assert list(params) == ["0"]
    assert params[0] == Parameter(1, "m")


# Access ------------------------------------------------------------------------


def test_item_and_attribute_access(params):
    assert params["end_affector_cog"]["x"] == Parameter(50, "mm")
    assert params["end_affector_cog.x"] == Parameter(50, "mm")
    assert params.end_affector_cog.x == Parameter(50, "mm")
    assert params["arm_reference_angles"][2] == Parameter(240, "deg")


def test_missing_items(params):
    with pytest.raises(KeyError):
        params["missing"]
    with pytest.raises(KeyError):
        params["end_affector_cog.w"]
    with pytest.raises(KeyError):
        params["singlename.x"]
    with pytest.raises(AttributeError, match="no parameter 'missing'"):
        _ = params.missing
    assert "end_affector_cog.x" in params
    assert "end_affector_cog.w" not in params
    assert params.get("missing") is None


def test_iteration_follows_file_order(params):
    assert list(params)[:4] == ["singlename", "base_zheight", "nacelle_mass", "nacelle_radius"]
    assert len(params) == 15


def test_set_items_from_any_leaf_form():
    params = Parameters()
    params["a"] = [1, "m"]
    params["b"] = "2 kg"
    params["c"] = {"x": [1, "mm"]}
    params["d"] = Parameter(3, "s")
    params.e = {"value": 4, "units": "N"}
    assert params["a"] == Parameter(1, "m")
    assert params["b"] == Parameter(2, "kg")
    assert isinstance(params["c"], Parameters)
    assert params["d"] == Parameter(3, "s")
    assert params["e"] == Parameter(4, "N")


def test_set_dotted_path_creates_groups():
    params = Parameters()
    params["arm.upper.length"] = [1, "m"]
    assert params.arm.upper.length == Parameter(1, "m")
    with pytest.raises(ParameterError, match="'length' is a parameter, not a group"):
        params["arm.upper.length.x"] = 1


def test_set_reports_location_of_errors():
    params = Parameters()
    with pytest.raises(UnitError, match=r"^arm\.length: invalid units"):
        params["arm.length"] = [1, "mx"]


def test_failed_set_leaves_no_trace():
    params = Parameters({"arm": {"length": [1, "m"]}})
    with pytest.raises(UnitError):
        params["motor.shaft.length"] = [1, "mx"]
    with pytest.raises(ParameterError, match="invalid key"):
        params["motor..length"] = [1, "m"]
    with pytest.raises(ParameterError, match="not a group"):
        params["arm.length.x"] = [1, "m"]
    assert params.to_dict() == {"arm": {"length": [1, "m"]}}


def test_attributes_cannot_shadow_methods():
    params = Parameters()
    with pytest.raises(AttributeError, match="use params\\['table'\\]"):
        params.table = [1, "m"]
    params["table"] = [1, "m"]
    assert params["table"] == Parameter(1, "m")
    assert callable(params.table)


def test_private_attributes_are_ordinary_attributes():
    params = Parameters()
    params._cache = 1
    assert params._cache == 1
    assert len(params) == 0


def test_delete(params):
    del params["end_affector_cog.x"]
    assert list(params.end_affector_cog) == ["y", "z"]
    del params.singlename
    assert "singlename" not in params
    with pytest.raises(KeyError):
        del params["end_affector_cog.x"]
    with pytest.raises(KeyError):
        del params["missing.x"]


def test_dir_lists_parameters(params):
    assert "end_affector_cog" in dir(params)
    assert "table" in dir(params)


# Transformations -------------------------------------------------------------


def test_to_si(params):
    si = params.to_si()
    assert si["nacelle_mass"].units == "kg"
    assert si["nacelle_mass"].value == pytest.approx(1.5)
    assert si["arm_reference_angles.1"].units == "rad"
    assert si["max_speed"].units == "rad/s"
    assert si["pure_string_parameter"] == Parameter("string")
    assert params["nacelle_mass"].units == "g", "to_si() must not modify the original"


def test_to_si_with_mixed_units_in_a_group():
    # Regression: 0.1 raised "Units for motor are not consistent".
    params = Parameters({"motor": {"mass": [1, "kg"], "length": [1, "m"]}})
    assert params.to_si().motor.length == Parameter(1, "m")


def test_flatten(params):
    flat = params.flatten()
    assert flat["end_affector_cog.z"] == Parameter(0, "mm")
    assert all(isinstance(value, Parameter) for value in flat.values())
    assert "end_affector_cog__z" in params.flatten(sep="__")


def test_magnitudes(params):
    values = params.to_si().magnitudes()
    assert values["nacelle_radius"] == pytest.approx(0.15)
    assert values["end_affector_cog"]["y"] == pytest.approx(-0.001)
    np.testing.assert_allclose(values["link_lengths"], [0.3, 0.25, 0.12])
    assert values["enabled"] is True


def test_merge_is_recursive_and_does_not_modify_inputs():
    base = Parameters({"arm": {"length": [1, "m"], "mass": [10, "kg"]}, "name": "base"})
    overrides = Parameters({"arm": {"mass": "12 kg"}, "name": "case 1"})
    merged = base.merge(overrides)
    assert merged.arm.length == Parameter(1, "m")
    assert merged.arm.mass == Parameter(12, "kg")
    assert merged.name == Parameter("case 1")
    assert base.arm.mass == Parameter(10, "kg")
    merged.arm["length"] = [2, "m"]
    assert base.arm.length == Parameter(1, "m")


def test_merge_accepts_plain_dicts_and_replaces_leaves_with_groups():
    base = Parameters({"cog": [0, "mm"]})
    merged = base.merge({"cog": {"x": [1, "mm"]}})
    assert merged["cog.x"] == Parameter(1, "mm")


def test_copy_is_independent(params):
    copied = params.copy()
    copied["end_affector_cog.x"] = [1, "m"]
    assert params["end_affector_cog.x"] == Parameter(50, "mm")


def test_deepcopy_and_pickle(params):
    assert copy.deepcopy(params) == params
    assert pickle.loads(pickle.dumps(params)) == params


def test_stack(params):
    assert params.end_affector_cog.stack() == Parameter([50, -1, 0], "mm")
    mixed = Parameters({"x": [50, "mm"], "y": [-0.001, "m"]})
    stacked = mixed.stack()
    assert stacked.units == "mm"
    np.testing.assert_allclose(stacked.value, [50, -1])


def test_stack_errors():
    with pytest.raises(ParameterError, match="numeric parameters"):
        Parameters().stack()
    with pytest.raises(ParameterError, match="numeric parameters"):
        Parameters({"a": "text"}).stack()
    with pytest.raises(ParameterError, match="numeric parameters"):
        Parameters({"a": {"b": 1}}).stack()
    with pytest.raises(DimensionalityError):
        Parameters({"a": [1, "m"], "b": [1, "s"]}).stack()


# Output ---------------------------------------------------------------------------


def test_equality():
    a = Parameters({"x": [1, "m"], "g": {"y": [2, "s"]}})
    assert a == Parameters({"x": [1000, "mm"], "g": {"y": [2, "s"]}})
    assert a != Parameters({"x": [1, "m"], "g": {"y": [3, "s"]}})
    assert a == {"x": Parameter(1, "m"), "g": {"y": Parameter(2, "s")}}


def test_to_dict_and_yaml_round_trip(params, tmp_path):
    assert Parameters(params.to_dict()) == params
    path = tmp_path / "out.yaml"
    text = params.to_yaml(path)
    assert path.read_text(encoding="utf-8") == text
    restored = Parameters.from_yaml(path)
    assert restored == params
    assert restored.flatten().keys() == params.flatten().keys()
    for key, parameter in params.flatten().items():
        assert restored[key].units == parameter.units
        assert restored[key].description == parameter.description


def test_to_yaml_writes_leaves_inline():
    params = Parameters(
        {"a": [[0, 120], "deg"], "b": {"value": [1, 2], "units": "m", "description": "B"}}
    )
    assert params.to_yaml() == (
        "a: [[0, 120], deg]\nb:\n  value: [1, 2]\n  units: m\n  description: B\n"
    )


def test_table():
    params = Parameters(
        {"arm": {"length": [1.23456789, "m"], "angles": [[0, 120], "deg"]}, "name": "RC-100"}
    )
    assert str(params.table(precision=3)) == (
        "+------------+----------+-------+\n"
        "| Parameter  |    Value | Units |\n"
        "+------------+----------+-------+\n"
        "| arm.length |     1.23 | m     |\n"
        "| arm.angles | [0, 120] | deg   |\n"
        "| name       |   RC-100 | -     |\n"
        "+------------+----------+-------+"
    )


def test_table_shows_descriptions_when_present(params):
    table = params.table()
    assert table.field_names == ["Parameter", "Value", "Units", "Description"]
    assert ["payload", "2.5", "kg", "Rated payload"] in table.rows


def test_render_markdown_aligns_columns_and_escapes_pipes():
    params = Parameters({"ratio": 0.5, "mode": "a|b", "stroke": [150, "mm"]})
    assert params.render("markdown") == (
        "| Parameter | Value | Units |\n"
        "| :-------- | ----: | :---- |\n"
        "| ratio     |   0.5 | -     |\n"
        "| mode      |  a\\|b | -     |\n"
        "| stroke    |   150 | mm    |"
    )


def test_render_markdown_keeps_multiline_cells_on_one_row():
    params = Parameters({"x": {"value": 1, "description": "first\nsecond"}})
    assert (
        params.render("markdown").splitlines()[-1]
        == "| x         |     1 | -     | first<br>second |"
    )


def test_render_formats():
    params = Parameters({"stroke": {"value": 150, "units": "mm", "description": "Stroke"}})
    assert params.render() == str(params)
    assert params.render("csv") == "Parameter,Value,Units,Description\nstroke,150,mm,Stroke"
    assert "<td>Stroke</td>" in params.render("html")
    assert "\\begin{tabular}" in params.render("latex")
    assert Parameters.from_yaml(io.StringIO(params.render("yaml"))) == params
    assert Parameters(json.loads(params.render("json"))) == params
    with pytest.raises(ValueError, match="unknown format 'docx'"):
        params.render("docx")


def test_str_repr_and_html():
    params = Parameters({"x": [1, "m"]})
    assert str(params) == str(params.table())
    assert repr(params) == "Parameters({'x': Parameter(1, 'm')})"
    assert "<table>" in params._repr_html_()


def test_subclasses_keep_their_type():
    class Robot(Parameters):
        def reach(self):
            return self["arm.length"]

    robot = Robot({"arm": {"length": [1, "m"]}})
    assert isinstance(robot.to_si(), Robot)
    assert isinstance(robot.merge({}), Robot)
    assert robot.to_si().reach() == Parameter(1, "m")


# Regressions from review -----------------------------------------------------


def test_mapping_with_a_value_key_is_always_a_parameter():
    with pytest.raises(ParameterError, match=r"^x: a parameter mapping needs .*'unit'"):
        Parameters({"x": {"value": 1, "unit": "m"}})


def test_value_is_a_reserved_key():
    with pytest.raises(ParameterError, match="'value' cannot name"):
        Parameters({"value": 1})
    params = Parameters()
    with pytest.raises(ParameterError, match="'value' cannot name"):
        params["s.value"] = [5, "V"]
    assert len(params) == 0


def test_inserted_groups_are_copied():
    original = Parameters({"g": {"y": [1, "m"]}})
    for copy_ in (Parameters(original), Parameters({"sub": original.g})):
        group = copy_["g"] if "g" in copy_ else copy_["sub"]
        group["y"] = [2, "m"]
    assert original["g.y"] == Parameter(1, "m")


def test_duplicate_keys_are_rejected():
    with pytest.raises(ParameterError, match="duplicate key '1'"):
        Parameters({1: 1, "1": 2})
    with pytest.raises(yaml.YAMLError, match="found duplicate key 'a'"):
        Parameters.from_yaml(io.StringIO("a: 1\nb: 2\na: 3\n"))


def test_yaml_merge_keys_still_work():
    params = Parameters.from_yaml(
        io.StringIO("base: &base {x: [1, m], y: [2, m]}\ncase:\n  <<: *base\n  y: [3, m]\n")
    )
    assert params["case"] == Parameters({"x": [1, "m"], "y": [3, "m"]})


def test_yaml_scalars_follow_yaml_1_2():
    params = Parameters.from_yaml(
        io.StringIO("a: on\nb: yes\nc: 1:30\nd: 2024-01-01\ne: 0042\nf: 0x1F\ng: true\nh: ~\n")
    )
    assert params.magnitudes() == {
        "a": "on",
        "b": "yes",
        "c": "1:30",
        "d": "2024-01-01",
        "e": 42,
        "f": 31,
        "g": True,
        "h": None,
    }


def test_text_that_looks_like_numbers_round_trips_through_yaml():
    params = Parameters({"a": {"value": "2E5"}, "b": ["1e3", "a", "b"], "c": "NaN", "d": "0042"})
    restored = Parameters.from_yaml(io.StringIO(params.to_yaml()))
    assert restored == params
    assert restored.magnitudes() == {"a": "2E5", "b": ["1e3", "a", "b"], "c": "NaN", "d": "0042"}


def test_non_finite_values_round_trip_through_yaml_and_json():
    params = Parameters({"a": [float("nan"), "m"], "b": [float("inf"), "s"], "c": -float("inf")})
    for fmt in ("yaml", "json"):
        restored = Parameters.from_yaml(io.StringIO(params.render(fmt)))
        assert np.isnan(restored["a"].value)
        assert restored["b"] == Parameter(float("inf"), "s")
        assert restored["c"] == Parameter(-float("inf"))


def test_render_latex_escapes_special_characters():
    params = Parameters({"arm_length": {"value": 5, "units": "%", "description": "R&D #1"}})
    assert params.render("latex").splitlines()[2] == r"arm\_length & 5 & \% & R\&D \#1 \\"


def test_table_precision_must_be_positive():
    with pytest.raises(ValueError, match="precision must be at least 1"):
        Parameters({"a": 1.5}).table(precision=0)
