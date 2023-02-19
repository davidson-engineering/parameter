import pytest

from parameter.parameter import Parameter

@pytest.fixture
def test_params():
    return dict(
        a=Parameter(1, "m"),
        b=Parameter(2, "mm"),
        c=Parameter(3, "mm/s"),
        d=Parameter(3, "mm/min"),
        e=Parameter(2, "deg/min"),
        f=Parameter(100, "rev/min"),
        g=Parameter(1000, "rev/hour"),
        h=Parameter(0.1, "kg/mm^3"),
        i=Parameter(0.1, "kg/m^3"),
        j=Parameter(0.1, "N.m"),
        k=Parameter(0.1, "kN.m"),
        l=Parameter(3, "N.mm"),
    )
