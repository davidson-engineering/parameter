from parameter.parameter import read_parameters_from_yaml, Parameters

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
    grouped = parameters.grouped_by_prefix
    print(grouped.table)
    print(grouped.si_units.table)
    print(grouped.si_units.values_only)