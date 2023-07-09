# Parameter Class
# Author : Matthew Davidson
# 2022/01/23
# Matthew Davidson © 2022

from __future__ import annotations
from dataclasses import dataclass
import dataclasses
import logging
from pathlib import Path
import copy
import re
import itertools
from collections.abc import Iterable
from yaml import safe_load
import operator
from numpy import asarray, ndarray
from prettytable import PrettyTable
import parameter.conversion as convert

FACTORS = convert.TO_SI_FACTOR
UNITS = convert.TO_SI_UNITS
EPS = 1e-10


def is_iterable(element):
    """Check if an element is iterable"""
    if isinstance(element, Iterable):
        return 1
    try:
        iter(element)
    except TypeError:
        return 0
    else:
        return 1


def read_yaml(filepath: str | Path) -> dict:
    """Read a yaml file and return a dictionary"""
    path = Path(filepath)
    if path.root == "\\":
        path = Path.cwd() / path
    with open(path, "r") as file:
        return safe_load(file)


@dataclass
class Parameter:
    value: float | str
    units: str

    def __str__(self):
        return f"{self.value}{self.units}"

    def __repr__(self):
        return f"{self.value}{self.units}"

    def __eq__(self, other):
        if isinstance(other, (int, float)):
            return (self.value - other) < EPS
        try:
            self_si, other_si = self.si_units, other.si_units
        except AttributeError:
            self_si = self.si_units
            other_si = Parameter(other, self_si.units)
        try:
            return (self_si.value - other_si.value) < EPS and self_si.units == other_si.units
        except ValueError: 
            return (self_si.value - other_si.value).all() < EPS and self_si.units == other_si.units

    def __ne__(self, other):
        return not self == other

    def _apply_operator(self, other, op_func):
        if isinstance(other, (int, float)):
            return Parameter(op_func(self.value, other), self.units)
        try:
            self_si, other_si = self.si_units, other.si_units
            if self_si.units != other_si.units and (
                str(self_si.si_units) != "1"
                and self_si.si_units != 1
                or str(other_si.si_units) != "1"
                and other_si.si_units != 1
            ):
                raise ValueError("Cannot operate on parameters with different units.")

        except AttributeError:
            self_si = self.si_units
            other_si = Parameter(other, self_si.units)
        value = op_func(
            self_si.value, other_si.value if isinstance(other, Parameter) else other
        )
        return Parameter(value, self_si.units)

    def __add__(self, other):
        return self._apply_operator(other, operator.add)

    def __sub__(self, other):
        return self._apply_operator(other, operator.sub)

    def __mul__(self, other):
        return self._apply_operator(other, operator.mul)

    def __rmul__(self, other):
        return self._apply_operator(other, operator.mul)

    def __truediv__(self, other):
        return self._apply_operator(other, operator.truediv)

    def __rtruediv__(self, other):
        return self._apply_operator(other, operator.truediv)

    def __floordiv__(self, other):
        return self._apply_operator(other, operator.floordiv)

    def __mod__(self, other):
        return self._apply_operator(other, operator.mod)

    def __pow__(self, other):
        return self._apply_operator(other, operator.pow)

    def __gt__(self, other):
        return self._apply_operator(other, operator.gt)

    def __ge__(self, other):
        return self._apply_operator(other, operator.ge)

    def __lt__(self, other):
        return self._apply_operator(other, operator.lt)

    def __le__(self, other):
        return self._apply_operator(other, operator.le)

    def __abs__(self):
        return Parameter(abs(self.value), self.units)

    def __neg__(self):
        return Parameter(-self.value, self.units)

    def __float__(self):
        return float(self.value)

    def __iter__(self):
        return iter(self.value)

    def to_numpy(self):
        return asarray(self.value)

    def __int__(self):
        return int(self.value)

    @property
    def si_units(self):
        """
        Convert to SI units.

        Parameter
        ------
        parameter : Parameter object

        Returns
        -------
        y : Parameter object (in SI units)

        Raises
        ------
        Exception, message

        Notes
        -----
        """

        def split_string_with_separators(s: str):
            """
            Split a string into a list of parts, and a list of separators
            """
            # Define a regular expression to match separators
            sep_pattern = r"[/.^]"
            parts = re.split(sep_pattern, s)
            # Use re.findall to find all occurrences of the separator pattern in the original string
            seps = re.findall(sep_pattern, s)
            return parts, seps

        def find_indexes_of_char(string_list, char: str):
            return [i for i, s in enumerate(string_list) if char in s]

        def get_SI_factor(units):
            """Convert the units to SI units"""
            unit_components, separators = split_string_with_separators(str(units))

            if len(separators) == 0:
                return FACTORS[unit_components[0]]

            power_idxs = find_indexes_of_char(separators, "^")
            power_factors = [
                FACTORS[unit_components[idx]] ** int(unit_components[idx + 1])
                for idx in power_idxs
            ]

            multiply_idxs = find_indexes_of_char(separators, ".")
            multiply_factors = [
                FACTORS[unit_components[idx]] * FACTORS[unit_components[idx + 1]]
                for idx in multiply_idxs
            ]

            divide_idxs = find_indexes_of_char(separators, "/")
            divide_factors = [
                FACTORS[unit_components[idx]] / FACTORS[unit_components[idx + 1]]
                for idx in divide_idxs
            ]

            product = lambda x: x[0] * product(x[1:]) if x else 1
            return product(power_factors + multiply_factors + divide_factors)

        def get_SI_units(units):
            """Convert the units to SI units"""
            # Split the units by either "/" or "."
            unit_components, separators = split_string_with_separators(str(units))
            separators = [""] + separators

            # Loop over the split components and look up their conversion factors in the mapping
            converted_units = []
            for component, separator in itertools.zip_longest(
                unit_components, separators
            ):
                if component in UNITS:
                    converted_units.append(UNITS[component])
                elif component.isnumeric():
                    if separator == "^":
                        try:
                            exponent = int(component)
                            converted_units.append(str(exponent))
                        except ValueError:
                            raise ValueError(f"Exponent {component} is not an integer")
                else:
                    logging.error(f"Unit {component} not found in UNITS dictionary")
                    raise ValueError(f"Unit {component} not found in UNITS dictionary")

            while len(separators) < len(converted_units):
                separators.append("")

            # Merge the converted units back into the original units with the separator that was used
            return "".join(
                [
                    val
                    for pair in itertools.zip_longest(converted_units, separators[1:])
                    for val in pair
                    if val is not None
                ]
            )

        param_new = copy.deepcopy(self)
        param_new.value = factor(self.value, get_SI_factor(self.units))
        param_new.units = get_SI_units(self.units)
        return param_new


class Parameters(dict):
    """
    Parameters class
    """

    def __init__(self, *args, **kwargs):
        self.groups = []
        super().__init__(*args, **kwargs)

    @property
    def table(self):
        """
        Return a pretty table of the parameters
        """
        table = PrettyTable()
        table.field_names = ["Parameter", "Value", "Units"]

        for key, value in self.items():
            if isinstance(value, Parameter):
                try:
                    cell_value = round(value.value, 3)
                except TypeError:
                    cell_value = value.value
                cell_units = value.units
            elif isinstance(value, list):
                cell_value = [round(v, 3) for v in value]
                cell_units = "-"
            else:
                cell_value = value
                cell_units = "-"

            table.add_row([key, cell_value, cell_units])

        return table

    @property
    def si_units(self):
        return self.__class__(**{key: param.si_units for key, param in self.items()}).group_by_prefix()

    @property
    def values_only(self):
        """
        Return a dictionary of values in SI units only
        """

        return self.__class__(**{k: v.value for k, v in self.si_units.items()}).group_by_prefix()

    # @property
    # def ungrouped_values_only(self):
    #     """
    #     Return a dictionary of values in SI units only
    #     """
    #     return self.__class__(
    #         **{k: v.value for k, v in self.items() if k not in self.groups}
    #     )
    @property
    def ungrouped_values_only(self):
        """
        Return a dictionary of values in SI units only
        """
        try:
            return self.__class__(
                **{k: v.value for k, v in self.items() if k not in self.groups}
            )
        except AttributeError:
            return self.__class__(**{k: v.value for k, v in self.items()})

    def group_by_prefix(self) -> Parameters:
        """
        Group parameters by prefix
        """
        if dataclasses.is_dataclass(self):
            keys = list(dataclasses.asdict(self))
        else:
            keys = list(self.keys())

        copy_self = copy.deepcopy(self)
        groups = {}
        regex = r"(\w+)__\w+"
        matches = [re.search(regex, key) for key in keys]
        groups = {match.group(1) for match in matches if match is not None}
        copy_self.groups = groups

        for group in groups:
            group_units = set()
            for key in keys:
                if (key.startswith(group) and key != group):
                    try:
                        group_units.add(copy_self[key].units)
                    except AttributeError:
                        group_units.add('-')
            if len(group_units) > 1:
                logging.error(
                    'Units for parameter %s are not consistent, cannot continue safely", group'
                )
                raise ValueError(f"Units for {group} are not consistent")

            copy_self.__setattr__(
                group,
                Parameter(value=self.get_common_value(group), units=group_units.pop()),
            )
        # TODO need to fix bug where dataclass loses repr of parameters
        # return dict_to_parameters(dataclasses.asdict(copy_self), object_type=copy_self.__class__)

        return copy_self

    def get_multi(self, inclusions: list) -> dict:
        """
        Get a dictionary of parameters with multiple values
        """

        return {inc: self[inc] for inc in inclusions}

    def get_common_value(self, prefix: str) -> list:
        """
        Get the common value for a parameter
        """
        if dataclasses.is_dataclass(self):
            return [
                getattr(self, name).value
                for name in self.__dataclass_fields__
                if name.startswith(prefix) and name != prefix
            ]
        try:
            return [v.value for k, v in self.items() if k.startswith(prefix)]
        except AttributeError:
            return [v for k, v in self.items() if k.startswith(prefix)]

    def flatten(self):
        """
        Flatten the parameters into a dictionary
        """
        if dataclasses.is_dataclass(self):
            return self.__class__(**flatten_dict(dataclasses.asdict(self)))
        else:
            return flatten_dict(self)

    def items(self):
        if dataclasses.is_dataclass(self):
            return [(name, getattr(self, name)) for name in self.__dataclass_fields__]
        else:
            return [(key, self[key]) for key in self]

    def __getitem__(self, key):
        if dataclasses.is_dataclass(self):
            return getattr(self, key)
        else:
            return super().__getitem__(key)


def tabulate_object_attrs(obj):
    """
    Tabulate the attributes of an object
    """
    table = PrettyTable()
    table.field_names = ["Property", "Value"]

    def tabulate_nested_dict(d, prefix):
        for key, value in d.items():
            if type(value) == dict:
                tabulate_nested_dict(value, prefix + key + ".")
            else:
                table.add_row([prefix + key, value])

    for attr in ["value", "units"]:
        tabulate_nested_dict(getattr(obj, attr), f"{attr}.")
    return table


def factor(data, factor):
    """Factor data by a factor"""
    if isinstance(data, ndarray):
        return data * factor
    if isinstance(data, str):
        return data
    if is_iterable(data):
        return [d * factor for d in data]
    return data * factor


def flatten_dict(d, parent_key="", sep="__"):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + str(k) if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def dict_to_parameters(
    d,
    parent_key="",
    sep="__",
    convert_to_si=False,
    object_type=Parameters,
    group_by_prefix=False,
):
    """Convert a dictionary to a Parameters object"""
    flattened_dict = flatten_dict(d, parent_key=parent_key, sep=str(sep))
    parameter_kvpairs = {}
    for key, val in flattened_dict.items():
        try:
            parameter_kvpairs[key] = Parameter(*val)
        except TypeError:
            try:
                parameter_kvpairs[key] = Parameter(**val)
            except TypeError:
                parameter_kvpairs[key] = Parameter(val, units="-")

    parameters = object_type(
        **parameter_kvpairs
    )

    if group_by_prefix:
        parameters = parameters.group_by_prefix()
    return parameters.si_units if convert_to_si else parameters


def dicts_to_parameters(dict_, convert_to_si=False) -> dict | dict[dict]:
    """Convert a dictionary of dictionaries to a dictionary of Parameters objects"""
    return {
        k: dict_to_parameters(v, convert_to_si=convert_to_si) for k, v in dict_.items()
    }


def read_parameters_from_yaml(
    filepath: str | Path,
    group_by_prefix=False,
    convert_to_si=False,
    object_type=Parameters,
) -> dict | dict[dict]:
    """Parse a yaml file to a Parameters object"""
    parameters_dict = read_yaml(filepath)
    return dict_to_parameters(
        parameters_dict,
        group_by_prefix=group_by_prefix,
        convert_to_si=convert_to_si,
        object_type=object_type,
    )


def read_set_of_parameters_from_yaml(filepath: str | Path) -> dict | dict[dict]:
    """Parse a yaml file to a Parameters object"""
    parameters_dict = read_yaml(filepath)
    return dicts_to_parameters(parameters_dict)


def main():
    pass


if __name__ == "__main__":
    main()
