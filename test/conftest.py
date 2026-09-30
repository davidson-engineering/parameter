from pathlib import Path

import pytest

from engparams import Parameters

DATA = Path(__file__).parent / "input_file.yaml"


@pytest.fixture
def params() -> Parameters:
    return Parameters.from_yaml(DATA)["test_parameters"]
