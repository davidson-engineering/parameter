import json
import subprocess
import sys

import pytest
import yaml

from engparams.cli import main

ROBOT = """\
motor:
  max_speed: 3000 rpm
  torque: {value: 12, units: N.m, description: Continuous torque}
arm:
  length: [1200, mm]
"""


@pytest.fixture
def robot(tmp_path):
    path = tmp_path / "robot.yaml"
    path.write_text(ROBOT, encoding="utf-8")
    return path


def run(capsys, *args):
    code = main([str(arg) for arg in args])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_text_table(capsys, robot):
    code, out, err = run(capsys, robot, "motor", "--si")
    assert (code, err) == (0, "")
    assert out == (
        "+-----------+---------+-------+-------------------+\n"
        "| Parameter |   Value | Units | Description       |\n"
        "+-----------+---------+-------+-------------------+\n"
        "| max_speed | 314.159 | rad/s |                   |\n"
        "| torque    |      12 | N.m   | Continuous torque |\n"
        "+-----------+---------+-------+-------------------+\n"
    )


def test_single_parameter(capsys, robot):
    code, out, _ = run(capsys, robot, "arm.length", "--si", "--format", "csv")
    assert code == 0
    assert out.splitlines() == ["Parameter,Value,Units", "length,1.2,m"]


def test_precision(capsys, robot):
    _, out, _ = run(capsys, robot, "motor.max_speed", "--si", "-p", "3", "-f", "csv")
    assert out.splitlines()[1] == "max_speed,314,rad/s"


def test_markdown(capsys, robot):
    _, out, _ = run(capsys, robot, "arm", "--format", "markdown")
    assert out.splitlines() == [
        "| Parameter | Value | Units |",
        "| :-------- | ----: | :---- |",
        "| length    |  1200 | mm    |",
    ]


def test_html(capsys, robot):
    code, out, _ = run(capsys, robot, "--format", "html")
    assert code == 0
    assert "<td>motor.max_speed</td>" in out


def test_latex_is_escaped(capsys, robot):
    code, out, _ = run(capsys, robot, "--format", "latex")
    assert code == 0
    assert out.splitlines()[:3] == [
        r"\begin{tabular}{lrll}",
        r"Parameter & Value & Units & Description \\",
        r"motor.max\_speed & 3000 & rpm &  \\",
    ]


def test_precision_must_be_positive(capsys, robot):
    with pytest.raises(SystemExit):
        main([str(robot), "-p", "0"])
    assert "must be at least 1" in capsys.readouterr().err


def test_non_utf8_file(capsys, tmp_path):
    path = tmp_path / "latin1.yaml"
    path.write_bytes("name: caf\xe9".encode("latin-1"))
    code, _, err = run(capsys, path)
    assert code == 1
    assert err.startswith(f"engparams: error: {path} is not UTF-8 text")


def test_yaml_and_json(capsys, robot):
    _, out, _ = run(capsys, robot, "--si", "--format", "yaml")
    assert yaml.safe_load(out)["arm"] == {"length": [1.2, "m"]}
    _, out, _ = run(capsys, robot, "--format", "json")
    assert json.loads(out)["motor"]["torque"] == {
        "value": 12,
        "units": "N.m",
        "description": "Continuous torque",
    }


def test_missing_file(capsys, tmp_path):
    code, out, err = run(capsys, tmp_path / "missing.yaml")
    assert (code, out) == (1, "")
    assert err.startswith("engparams: error: [Errno 2] No such file or directory")


def test_missing_key(capsys, robot):
    code, _, err = run(capsys, robot, "motor.power")
    assert code == 1
    assert err == f"engparams: error: {robot} has no parameter or group 'motor.power'\n"


def test_invalid_file(capsys, tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("arm:\n  length: [1, mx]\n", encoding="utf-8")
    code, _, err = run(capsys, path)
    assert code == 1
    assert err.startswith("engparams: error: arm.length: invalid units 'mx'")


def test_malformed_yaml(capsys, tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("arm: [1, m\n", encoding="utf-8")
    code, _, err = run(capsys, path)
    assert code == 1
    assert err.startswith("engparams: error: while parsing a flow sequence")


def test_module_entry_point(robot):
    result = subprocess.run(
        [sys.executable, "-m", "engparams", str(robot), "arm", "-f", "csv"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.splitlines() == ["Parameter,Value,Units", "length,1200,mm"]
