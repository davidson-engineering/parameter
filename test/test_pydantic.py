from typing import Annotated

import pytest

from parameter import Dimension, Parameter, ParameterError, Parameters, UnitError

pydantic = pytest.importorskip("pydantic")


class Motor(pydantic.BaseModel):
    torque: Annotated[Parameter, Dimension("N.m")]
    speed: Annotated[Parameter, Dimension("rad/s")]
    model: Parameter = Parameter("unknown")


class Robot(pydantic.BaseModel):
    motor: Motor
    extras: Parameters = Parameters()


def test_fields_accept_every_leaf_form():
    motor = Motor(torque=[12, "N.m"], speed="3000 rpm", model="M-1")
    assert motor.torque == Parameter(12, "N.m")
    assert motor.speed == Parameter(3000, "rpm")
    assert motor.model == Parameter("M-1")
    assert Motor(torque={"value": 1, "units": "kN.m"}, speed=Parameter(1, "rad/s")).torque == (
        Parameter(1000, "N.m")
    )


def test_dimension_errors_are_validation_errors_with_locations():
    with pytest.raises(pydantic.ValidationError) as error:
        Robot(motor={"torque": [12, "N"], "speed": "1 rad/s"})
    [detail] = error.value.errors()
    assert detail["loc"] == ("motor", "torque")
    assert "expected units compatible with 'N.m', got 'N'" in detail["msg"]


def test_invalid_units_are_validation_errors():
    with pytest.raises(pydantic.ValidationError, match="invalid units 'kgm'"):
        Motor(torque=[12, "kgm"], speed="1 rad/s")


def test_parameters_fields():
    robot = Robot(motor=Motor(torque="1 N.m", speed="1 rpm"), extras={"arm": {"length": "1 m"}})
    assert robot.extras["arm.length"] == Parameter(1, "m")


def test_json_round_trip():
    robot = Robot(
        motor=Motor(torque="12 N.m", speed="3000 rpm"),
        extras={"arm": {"length": {"value": 1, "units": "m", "description": "Reach"}}},
    )
    data = robot.model_dump(mode="json")
    assert data["motor"] == {"torque": [12, "N.m"], "speed": [3000, "rpm"], "model": "unknown"}
    assert data["extras"] == {"arm": {"length": {"value": 1, "units": "m", "description": "Reach"}}}
    assert Robot.model_validate_json(robot.model_dump_json()) == robot


def test_python_dump_keeps_parameters():
    motor = Motor(torque="12 N.m", speed="3000 rpm")
    assert isinstance(motor.model_dump()["torque"], Parameter)


def test_dimension_without_pydantic():
    assert Dimension("[length]").validate(Parameter(1, "ft")) == Parameter(1, "ft")
    with pytest.raises(ParameterError, match="expected units compatible"):
        Dimension("[length]").validate(Parameter(1, "s"))
    with pytest.raises(UnitError):
        Dimension("[lenght")


def test_json_schema():
    schema = Robot.model_json_schema()
    torque = schema["$defs"]["Motor"]["properties"]["torque"]
    assert torque["anyOf"][1]["required"] == ["value"]
    assert schema["properties"]["extras"]["type"] == "object"


def test_optional_fields_with_dimensions():
    class Tool(pydantic.BaseModel):
        offset: Annotated[Parameter, Dimension("[length]")] | None = None

    assert Tool().offset is None
    assert Tool(offset="5 mm").offset == Parameter(5, "mm")


def test_dimension_rejects_text_clearly():
    with pytest.raises(ParameterError, match="expected a number with units compatible with 'm'"):
        Dimension("m").validate(Parameter("abc"))
    with pytest.raises(ParameterError, match="Dimension checks Parameter values"):
        Dimension("m").validate(Parameters())  # type: ignore[arg-type]
