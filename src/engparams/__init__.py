"""Engineering parameters with units: load, convert, calculate and tabulate."""

from pint import DimensionalityError

from engparams.collection import Parameters
from engparams.errors import ParameterError, UnitError
from engparams.parameter import Dimension, Parameter
from engparams.units import define, ureg

__version__ = "0.2.0"

__all__ = [
    "Dimension",
    "DimensionalityError",
    "Parameter",
    "ParameterError",
    "Parameters",
    "UnitError",
    "define",
    "ureg",
]
