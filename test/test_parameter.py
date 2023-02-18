from parameter.parameter import Parameter

def test_parameter():
    param_a = Parameter(1, "m")
    param_b = Parameter(2, "mm")
    param_c = Parameter(3, "mm/s")
    param_d = Parameter(3, "mm/min")
    param_e = Parameter(2, "deg/min")
    param_f = Parameter(100, "rev/min")
    param_g = Parameter(1000, "rev/hour")

    eps = 1e-10

    assert param_a.convert_to_SI().value == 1
    assert param_a.convert_to_SI().units == "m"
    assert param_b.convert_to_SI().value == 0.002
    assert param_b.convert_to_SI().units == "m"
    assert param_c.convert_to_SI().value == 0.003
    assert param_c.convert_to_SI().units == "m/s"
    assert param_d.convert_to_SI().value == 5e-5
    assert param_d.convert_to_SI().units == "m/s"
    assert param_e.convert_to_SI().value - 0.0005817764173314432 < eps
    assert param_e.convert_to_SI().units == "rad/s"
    assert param_f.convert_to_SI().value - 10.471975511965976 < eps
    assert param_f.convert_to_SI().units == "rad/s"
    assert param_g.convert_to_SI().value - 1.7453292519943295 < eps
    assert param_g.convert_to_SI().units == "rad/s"