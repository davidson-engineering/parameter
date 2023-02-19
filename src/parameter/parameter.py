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


        def split_string_with_separators(s):
            # Define a regular expression to match separators
            sep_pattern = r'[/.^]'

            # Use re.split to split the string on the separator pattern
            parts = re.split(sep_pattern, s)

            # Use re.findall to find all occurrences of the separator pattern in the original string
            seps = re.findall(sep_pattern, s)

            # Return the parts and separators as a tuple
            return parts, seps


        def find_indexes_of_char(string_list, char: str):
            return [i for i, s in enumerate(string_list) if char in s]


        def get_factors(unit_components, separators):
            '''
            Get the conversion factors for the units
            '''

            if len(separators) == 0:
                return FACTORS[unit_components[0]]

            power_idxs = find_indexes_of_char(separators, "^")
            power_factors = [FACTORS[unit_components[idx]] ** int(unit_components[idx+1]) for idx in power_idxs]

            multiply_idxs = find_indexes_of_char(separators, ".")
            multiply_factors = [FACTORS[unit_components[idx]] * FACTORS[unit_components[idx+1]] for idx in multiply_idxs]

            divide_idxs = find_indexes_of_char(separators, "/")
            divide_factors = [FACTORS[unit_components[idx]] / FACTORS[unit_components[idx+1]] for idx in divide_idxs]
            
            product = lambda x: x[0] * product(x[1:]) if x else 1
            return product(power_factors + multiply_factors + divide_factors)


        def get_SI_factor(units):
            '''Convert the units to SI units'''
            unit_components, separators = split_string_with_separators(units)
            return get_factors(unit_components, separators)

        
        def get_SI_units(units):
            '''Convert the units to SI units'''
            # Split the units by either "/" or "."
            unit_components, separators = split_string_with_separators(units)

            # Loop over the split components and look up their conversion factors in the mapping
            converted_units = []
            for component in unit_components:
                try:
                    exponent = int(component)
                    converted_units.append(str(exponent))
                except ValueError:
                    pass
                if component in UNITS:
                    converted_units.append(UNITS[component])
                else:
                    logging.error(f"Unit {component} not found in UNITS dictionary")

            while len(separators) < len(converted_units):
                separators.append('')

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

    def as_values(self):
        return Parameters({k: v.value for k, v in self.items()})

    def as_values(self):
        return Parameters({k: v.value for k, v in self.items()})

    def group_by_prefix(self):
        prefix_dict = {}
        for key, value in self.items():
            for prefix in prefix_dict:
                if key.startswith(prefix) or prefix.startswith(key):
                    prefix_dict[prefix].append(value)
                    prefix_dict[key] = prefix_dict.pop(prefix)
                    break
            else:
                prefix_dict[key] = [value]
        for prefix, values in prefix_dict.items():
            if len(values) == 1:
                prefix_dict[prefix] = values[0]
        return Parameters(prefix_dict)

    def get_multi(self, inclusions):
        return {inc: self[inc] for inc in inclusions}

    def get_common(self, prefix: str):
        if dataclasses.is_dataclass(self):
            return {name: getattr(self, name) for name in self.__dataclass_fields__ if name.startswith(prefix)}
        return [self[name].value
            for name in self
            if name.startswith(prefix)] 

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

def flatten_dict(d, parent_key='', sep='_'):
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
