from parameter.parameter import read_parameters_from_yaml, Parameters, Parameter

def test_parameter(test_params):

    eps = 1e-10

    assert test_params['a'].si_units.value == 1
    assert test_params['a'].si_units.units == "m"
    assert test_params['b'].si_units.value == 0.002
    assert test_params['b'].si_units.units == "m"
    assert test_params['c'].si_units.value == 0.003
    assert test_params['c'].si_units.units == "m/s"
    assert test_params['d'].si_units.value == 5e-5
    assert test_params['d'].si_units.units == "m/s"
    assert test_params['e'].si_units.value - 0.0005817764173314432 < eps
    assert test_params['e'].si_units.units == "rad/s"
    assert test_params['f'].si_units.value - 10.471975511965976 < eps
    assert test_params['f'].si_units.units == "rad/s"
    assert test_params['g'].si_units.value - 1.7453292519943295 < eps
    assert test_params['g'].si_units.units == "rad/s"
    assert test_params['h'].si_units.value - 1.0000000000000002e-07 < eps
    assert test_params['h'].si_units.units == "kg/m^3"
    assert test_params['i'].si_units.value == 0.1
    assert test_params['i'].si_units.units == "kg/m^3"
    assert test_params['k'].si_units.value == 100
    assert test_params['k'].si_units.units == "N.m"
    assert test_params['l'].si_units.value == 0.003
    assert test_params['l'].si_units.units == "N.m"

def test_build_from_yaml():
    parameters = Parameters(read_parameters_from_yaml("test/input_file.yaml")["test_parameters"])
    table = parameters.table
    print("Parameters in original units:")
    print(table)
    table_SI = parameters.si_units.table
    print("Parameters in SI units:")
    print(table_SI)

def test_common():
    parameters = Parameters(read_parameters_from_yaml("test/input_file.yaml")["test_parameters"])
    parameters.get_common("end_affector_cog")

def test_as_values():
    parameters = Parameters(read_parameters_from_yaml("test/input_file.yaml")["test_parameters"])
    parameters.values_only

def test_group_by_prefix():
    parameters = Parameters(read_parameters_from_yaml("test/input_file.yaml")["test_parameters"])
    print(parameters.table)
    grouped = parameters.grouped
    print(grouped.table)
    print(grouped.si_units.table)
    print(grouped.si_units.values_only)

def test_dataclass_inheritance():
    from dataclasses import dataclass

    @dataclass
    class ParametersSubclass(Parameters):
        param_a: Parameter
        param_b: Parameter
        param_c: Parameter

    param_dict = {
        'param_a': Parameter(1, "m"),
        'param_b': Parameter(2, "mm"),
        'param_c': Parameter([3,4,5], "mm/s"),
    }

    params_subclass_object = ParametersSubclass(**param_dict)
    params_subclass_object_si = params_subclass_object.si_units
    print(params_subclass_object_si.table)

def test_imperial_units():
    param_a = Parameter(1, "lbf")
    param_b = Parameter(4.4482216152605, "N")
    assert param_a == param_b

    param_a = Parameter(1/4.4482216152605, "lbf")
    param_b = Parameter(1, "N")
    assert param_a == param_b

    param_a = Parameter(1/0.45359237, "lb")
    param_b = Parameter(1/14.5939029372064, "slug")
    assert param_a == param_b

def test_operators():
    p_a = Parameter(1, "m")
    p_b = Parameter(25, "mm")
    p_c = Parameter(300, "mm")
    p_d = Parameter(40, "m")
    p_e = Parameter(12, 'ft')

    assert p_d > p_c
    assert p_c < p_d
    assert p_a + p_b == Parameter(1.025, "m")
    assert p_a - p_b == Parameter(0.975, "m")
    assert p_a * p_b == Parameter(0.025, "m") # TODO: this should be m^2
    assert p_a / p_b == Parameter(40, "m")
    assert p_a + p_b == p_b + p_a
    assert p_e < p_d
    assert p_e > p_a
    assert p_e + p_a != Parameter(13, 'ft')
    assert p_e + p_a == Parameter(4.6576, 'm')


    p_f = Parameter(3.6576, 'mm^3')
    p_g = Parameter(3.6576E-9, 'm^3')
    assert p_f == p_g
    assert p_f // 1 == 3
    assert p_f.si_units // 1 == 0

    p_h = Parameter(36.487, 'MPa')
    assert p_h // 10 == 3
    assert (p_h // 10).si_units == p_h // 10

    p_i = Parameter([1,2,3], "m")
    p_j = Parameter([1000,2000,3000], "mm")
    p_k = Parameter([1000,2000,3000, 4000], "mm")
    assert p_i * 3 == Parameter([3,6,9], "m")
    assert p_i * 3 == Parameter([3000,6000,9000], "mm")
    assert p_j * 3 == Parameter([3,6,9], "m")
    assert p_k * 3 == Parameter([3000,6000,9000], "mm") # TODO should return false


import operator
import pytest

from parameter.parameter import combine_units

def test_combine_units_multiplication():
    assert combine_units('m', 's', operator.mul) == 'm.s'
    assert combine_units('m^2', 's^2', operator.mul) == 'm^2.s^2'
    assert combine_units('m/s', 's', operator.mul) == 'm'
    assert combine_units('m/s', 'm/s^2', operator.mul) == 'm^2/s^3'

def test_combine_units_division():
    assert combine_units('m', 's', operator.truediv) == 'm/s'
    assert combine_units('m/s', 's', operator.truediv) == 'm/s^2'
    assert combine_units('m^2', 's^2', operator.truediv) == 'm^2/s^2'
    assert combine_units('m.s', 'm/s^2', operator.truediv) == 's'

def test_combine_units_exponentiation():
    assert combine_units('m', '2', operator.pow) == 'm^2'
    assert combine_units('m/s', '2', operator.pow) == 'm^2/s^2'
    assert combine_units('m^2', '2', operator.pow) == 'm^4'
    assert combine_units('m.s', '2', operator.pow) == 'm^2.s^2'

def test_combine_units_invalid_operator():
    with pytest.raises(ValueError):
        combine_units('m', 's', lambda x, y: x + y)
