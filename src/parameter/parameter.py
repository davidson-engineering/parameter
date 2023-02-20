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
            '''
            Split a string into a list of parts, and a list of separators
            '''
            # Define a regular expression to match separators
            sep_pattern = r'[/.^]'
            parts = re.split(sep_pattern, s)
            # Use re.findall to find all occurrences of the separator pattern in the original string
            seps = re.findall(sep_pattern, s)

            return parts, seps


        def find_indexes_of_char(string_list, char: str):
            return [i for i, s in enumerate(string_list) if char in s]



        def get_SI_factor(units):
            '''Convert the units to SI units'''
            unit_components, separators = split_string_with_separators(units)

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

        param_new = copy.deepcopy(self)
        param_new.value = factor(self.value, get_SI_factor(self.units))
        param_new.units = get_SI_units(self.units)
        return param_new


class Parameters(dict):
    '''
    Parameters class
    '''
    @property
    def table(self):
        table = PrettyTable()
        table.field_names = ["Parameter", "Value", "Units"]
        for key, value in self.items():
            try:
                cell_value = round(value.value, 3)
            except TypeError:
                try:
                    cell_value = [round(v,3) for v in value.value]
                except TypeError:
                    cell_value = value.value

            table.add_row([key, cell_value, value.units])
        return table

    @property
    def si_units(self):
        return Parameters({key: param.si_units for key, param in self.items()})
    
    @property
    def values_only(self):
        return Parameters({k: v.value for k, v in self.items()})

    @property
    def grouped_by_prefix(self):
        '''
        Group parameters by prefix
        '''
        strings = list(self)
        groups = {}
        regex = r"(\w+)__\w+"
        matches = [re.search(regex, string) for string in strings]
        matched_keys = [match.string for match in matches if match is not None]
        groups = [match.group(1) for match in matches if match is not None]

        grouped_dict = {}

        for group in groups:

            group_units = {self[key].units for key in self if key.startswith(group)}
            if len(group_units) > 1:
                logging.error('Units for parameter %s are not consistent, cannot continue safely", group')
                raise ValueError(f"Units for {group} are not consistent")

            grouped_dict[group] = Parameter(self.get_common(group), group_units.pop())

        for key, value in self.items():
            if key not in matched_keys:
                grouped_dict[key] = value


        return Parameters(**grouped_dict)

        
    
    def get_multi(self, inclusions):
        return {inc: self[inc] for inc in inclusions}

    def get_common(self, prefix: str):
        '''
        Get the common value for a parameter
        '''
        if dataclasses.is_dataclass(self):
            return {name: getattr(self, name) for name in self.__dataclass_fields__ if name.startswith(prefix)}
        return [self[name].value
            for name in self
            if name.startswith(prefix)]

def tabulate_object_attrs(obj):
    '''
    Tabulate the attributes of an object
    '''
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

def flatten_dict(d, parent_key='', sep='__'):
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
    return parameters.si_units if convert_to_si else parameters


def dicts_to_parameters(dict_, convert_to_si=False) -> dict | dict[dict]:
    '''Convert a dictionary of dictionaries to a dictionary of Parameters objects'''
    return {k: dict_to_parameters(v, convert_to_si=convert_to_si) for k, v in dict_.items()}


def read_parameters_from_yaml(filepath: str | Path) -> dict | dict[dict]:
    '''Parse a yaml file to a Parameters object'''
    parameters_dict = read_yaml(filepath)
    return dicts_to_parameters(parameters_dict)


def main():
    pass





if __name__ == "__main__":
    main()
