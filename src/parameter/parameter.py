# Parameter Class
# Author : Matthew Davidson
# 2022/01/23
# Matthew Davidson © 2022

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import copy
import re
import itertools
from collections.abc import Iterable

from prettytable import PrettyTable
from yaml import safe_load

import parameter.conversion as convert

FACTORS = convert.TO_SI_FACTOR
UNITS = convert.TO_SI_UNITS

def is_iterable(element):
    '''Check if an element is iterable'''
    if isinstance(element, Iterable):
        return 1
    try:
        iter(element)
    except TypeError:
        return 0
    else:
        return 1

def read_yaml(filepath: str | Path) -> dict:
    '''Read a yaml file and return a dictionary'''
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

    def convert_to_SI(self):
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
        param_new = copy.deepcopy(self)

        def multiply_factor(unit_components):
            if len(unit_components) == 1:
                return FACTORS[unit_components[0]]
            elif len(unit_components) >= 2:
                product = lambda x: x[0] * product(x[1:]) if x else 1
                factors = tuple(
                    FACTORS[component] for component in unit_components
                )
                return product(factors)

            else:
                raise ValueError("Invalid units")

        def divide_factor(unit_components):
            '''Divide the units by "/"'''
            if len(unit_components) == 1:
                return unit_components[0]
            elif len(unit_components) >= 2:
                divided = unit_components[0]
                for component in unit_components[1:]:
                    divided /= component
                return divided

            else:
                raise ValueError("Invalid units")

        def split_multiply_factors(unit_components):
            '''Split the units by "."'''
            factors = []
            for component in unit_components:
                if component != "":
                    multiply_factor_components = component.split(".")
                    factors.append(multiply_factor(multiply_factor_components))
            return factors

        def get_SI_factor(units):
            '''Convert the units to SI units'''
            divide_factor_components = units.split("/")
            split_mutliply_factors = split_multiply_factors(divide_factor_components)
            return divide_factor(split_mutliply_factors)

        def get_SI_units(units):
            '''Convert the units to SI units'''
            # Split the units by either "/" or "."
            split_units = re.split(r"([./])", units)

            # Loop over the split components and look up their conversion factors in the mapping
            converted_units = []
            separators = []
            for component in split_units:
                if component in UNITS:
                    converted_units.append(UNITS[component])
                elif component in ["/", "."]:
                    separators.append(component)

            # Merge the converted units back into the original units with the separator that was used
            return "".join(
                [
                    val
                    for pair in itertools.zip_longest(converted_units, separators)
                    for val in pair
                    if val is not None
                ]
            )

        param_new.value = factor(self.value, get_SI_factor(self.units))
        param_new.units = get_SI_units(self.units)
        return param_new


class Parameters(dict):
    '''
    Parameters class
    '''
    def as_table(self):
        table = PrettyTable()
        table.field_names = ["Property", "Value", "Units"]
        for key, value in self.items():
            table.add_row([key, round(value.value, 3), value.units])
        return table

    def to_SI(self):
        return Parameters({key: param.convert_to_SI() for key, param in self.items()})

def tabulate_object_attrs(obj):
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
    '''Factor data by a factor'''
    return [d * factor for d in data] if is_iterable(data) else data * factor

def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + str(k) if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def dict_to_parameters(d, convert_to_si=False):
    '''Convert a dictionary to a Parameters object'''
    flattened_dict = flatten_dict(d)
    parameters = Parameters({key: Parameter(*val) for key, val in flattened_dict.items()})
    return parameters.to_SI() if convert_to_si else parameters


def dicts_to_parameters(dict_, convert_to_si=False) -> dict | dict[dict]:
    '''Convert a dictionary of dictionaries to a dictionary of Parameters objects'''
    return {k: dict_to_parameters(v, convert_to_si=convert_to_si) for k, v in dict_.items()}


def parse_yaml_to_parameters(filepath: str | Path) -> dict | dict[dict]:
    '''Parse a yaml file to a Parameters object'''
    parameters_dict = read_yaml(filepath)
    return dicts_to_parameters(parameters_dict)


def main():
    pass





if __name__ == "__main__":
    main()
