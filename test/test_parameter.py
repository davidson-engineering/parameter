from parameter.parameter import read_parameters_from_yaml, Parameters

def test_parameter(test_params):

    eps = 1e-10

    assert test_params['a'].convert_to_SI().value == 1
    assert test_params['a'].convert_to_SI().units == "m"
    assert test_params['b'].convert_to_SI().value == 0.002
    assert test_params['b'].convert_to_SI().units == "m"
    assert test_params['c'].convert_to_SI().value == 0.003
    assert test_params['c'].convert_to_SI().units == "m/s"
    assert test_params['d'].convert_to_SI().value == 5e-5
    assert test_params['d'].convert_to_SI().units == "m/s"
    assert test_params['e'].convert_to_SI().value - 0.0005817764173314432 < eps
    assert test_params['e'].convert_to_SI().units == "rad/s"
    assert test_params['f'].convert_to_SI().value - 10.471975511965976 < eps
    assert test_params['f'].convert_to_SI().units == "rad/s"
    assert test_params['g'].convert_to_SI().value - 1.7453292519943295 < eps
    assert test_params['g'].convert_to_SI().units == "rad/s"
    assert test_params['h'].convert_to_SI().value - 1.0000000000000002e-07 < eps
    assert test_params['h'].convert_to_SI().units == "kg/m^3"
    assert test_params['i'].convert_to_SI().value == 0.1
    assert test_params['i'].convert_to_SI().units == "kg/m^3"
    assert test_params['k'].convert_to_SI().value == 100
    assert test_params['k'].convert_to_SI().units == "N.m"
    assert test_params['l'].convert_to_SI().value == 0.003
    assert test_params['l'].convert_to_SI().units == "N.m"

def test_build_from_yaml():
    parameters = Parameters(read_parameters_from_yaml("test/input_file.yaml")["test_parameters"])
    table = parameters.as_table()
    print("")
    print(table)
    table_SI = parameters.to_SI().as_table()
    print(table_SI)

def test_common():
    parameters = Parameters(read_parameters_from_yaml("test/input_file.yaml")["test_parameters"])
    parameters.get_common("end_affector_cog")

def test_as_values():
    parameters = Parameters(read_parameters_from_yaml("test/input_file.yaml")["test_parameters"])
    parameters.as_values()

def test_group_by_prefix():
    parameters = Parameters(read_parameters_from_yaml("test/input_file.yaml")["test_parameters"])
    grouped = parameters.group_by_prefix()
    print(grouped)