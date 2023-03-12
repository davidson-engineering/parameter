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
from typing import Callable
from yaml import safe_load
import operator
from collections import Counter

from prettytable import PrettyTable
import parameter.conversion as convert

FACTORS = convert.TO_SI_FACTOR
UNITS = convert.TO_SI_UNITS
EPS = 1e-10

MULTIPLY = ['.', '*']
DIVIDE = ['/']
POWER = ['^']


def is_iterable(element) -> bool:
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

def cast_to_list(x) -> list: 
    '''
    Cast an object to a list if it is not already a list
    '''
    if isinstance(x, list):
        return x
    elif isinstance(x, str):
        return [x]
    try:
        return list(x)
    except TypeError:
        return [x]

def split_string_with_separators(s: str) -> tuple[list, list]:
    '''
    Split a string into a list of parts, and a list of separators
    '''
    # Define a regular expression to match separators
    sep_pattern = r'[/.^]'
    parts = re.split(sep_pattern, s)
    # Use re.findall to find all occurrences of the separator pattern in the original string
    seps = re.findall(sep_pattern, s)
    return parts, seps

def flatten_list(list_: list) -> list:
    '''
    Flatten a nested list
    '''
    return list(itertools.chain.from_iterable(list_))

import operator

def apply_operator_to_units(unit1: str, unit2: str, op: Callable):
    def split_into_denominator_and_numerator(unit):

        def expand_exponent(base, power):
            try:
                power = int(power)
                return [base for _ in range(power)]
            except ValueError:
                raise ValueError(f"Invalid unit: {unit} - {power} is not a valid exponent")
        
        def group_exponents(parts, seps):
            if '^' in seps:
                for i, sep in enumerate(seps):
                    if sep == '^':
                        parts[i] = expand_exponent(parts[i], parts[i+1])
                        parts.pop(i+1)
                        seps.pop(i)
            return flatten_list(parts), seps
        


        # if unit contains a '(' character, them recursively call split_into_denominator_and_numerator on the contents of the parentheses
        if '(' in unit:
            # Find the index of the first '(' character
            start = unit.find('(')
            # Find the index of the corresponding ')' character
            end = unit.find(')')
            # Split the unit into three parts: the part before the parentheses, the con
            # tents of the parentheses, and the part after the parentheses
            unit_before_parentheses = unit[:start]
            unit_inside_parentheses = unit[start+1:end]
            unit_after_parentheses = unit[end+1:]
            # Split the unit inside the parentheses into numerator and denominator parts
            num_parts_inside_parentheses, denom_parts_inside_parentheses = split_into_denominator_and_numerator(unit_inside_parentheses)
            # If the unit before the parentheses is not empty, multiply the numerator parts by the unit before the parentheses
            if unit_before_parentheses:
                if unit_before_parentheses[-1] in DIVIDE:
                    numerator_parts = denom_parts_inside_parentheses
                    denominator_parts = num_parts_inside_parentheses
                else:
                    numerator_parts = num_parts_inside_parentheses
                    denominator_parts = denom_parts_inside_parentheses
        else:
            denominator_parts = []
            numerator_parts = []

        parts, seps = split_string_with_separators(unit)
        parts, seps = group_exponents(parts, seps)
        if len(seps) == 0:
            return parts, []
        for i, sep in enumerate(seps):
            if sep == '/':
                numerator_parts.append(parts[i])
                denominator_parts.append(parts[i+1])
            elif sep == '.':
                numerator_parts.append(parts[i])
                numerator_parts.append(parts[i+1])
        return numerator_parts, denominator_parts

    unit1_numerator, unit1_denominator = split_into_denominator_and_numerator(unit1)
    unit2_numerator, unit2_denominator = split_into_denominator_and_numerator(unit2)

    if op == operator.mul:
        combined_unit_numerator = unit1_numerator + unit2_numerator
        combined_unit_denominator = unit1_denominator + unit2_denominator
    elif op == operator.truediv:
        combined_unit_numerator = unit1_numerator + unit2_denominator
        combined_unit_denominator = unit1_denominator + unit2_numerator
    elif op == operator.pow:
        raise ValueError("Not supported - Cannot combine units with exponent operator")

    numerator_cancelled, denominator_cancelled = cancel_common_units(combined_unit_numerator, combined_unit_denominator)

    simple_numerator = simplify_unit_list(numerator_cancelled)
    simple_denominator = simplify_unit_list(denominator_cancelled)
    numerator = '.'.join(simple_numerator)
    if simple_denominator:
        denominator = '/' + '/'.join(simple_denominator)
    else:
        denominator = ''
    return numerator+denominator

def simplify_unit_list(units: str) -> str:

    simplified_units = []

    for unit, count in Counter(units).items():
        if count == 1:
            # If the unit has an exponent of 1, don't include the exponent
            simplified_units.append(unit)
        else:
            # If the unit has an exponent greater than 1, include the exponent
            simplified_units.append(f"{unit}^{count}")

    # Combine the simplified units into a single string
    if not simplified_units:
        return ""
    else:
        return simplified_units

def cancel_common_units(numerator: list, denominator: list):
    num_counter = Counter(numerator)
    den_counter = Counter(denominator)
    for unit, count in num_counter.items():
        if unit in denominator:
            if count > den_counter[unit]:
                num_counter[unit] -= den_counter[unit]
                den_counter[unit] = 0
            else:
                den_counter[unit] -= num_counter[unit]
                num_counter[unit] = 0
    numerator_cancelled = [[unit for _ in range(count)] for unit, count in num_counter.items() if count > 0]
    denominator_cancelled = [[unit for _ in range(count)] for unit, count in den_counter.items() if count > 0]
    return flatten_list(numerator_cancelled), flatten_list(denominator_cancelled)



@dataclass
class Parameter:

    value: float | str
    units: str

    def __str__(self):
        return f"{self.value}{self.units}"

    def __repr__(self):
        return f"{self.value}{self.units}"

    def __eq__(self, other: float | list | Parameter) -> bool:
        if isinstance(other, (int, float)):
            return all(v - other for v in self) < EPS
        try:
            self_si, other_si = self.si_units, other.si_units
        except AttributeError:
            self_si = self.si_units
            other_si = Parameter(other, self_si.units)
        return (
            all(
                abs(v_self - v_other) < EPS
                for v_self, v_other in zip(self_si, other_si)
            )
            and self_si.units == other_si.units
        )

    def __ne__(self, other: float | list | Parameter) -> bool:
        return not self == other
    
    def _apply_operator(self, other: float | list | Parameter, op_func: Callable) -> Parameter:
        if isinstance(other, (int, float)):
            value = [op_func(v, other) for v in self]
            return Parameter(value, self.units)
        try:
            self_si, other_si = self.si_units, other.si_units
            if self_si.units != other_si.units:
                logging.warning(f"Operator {op_func} being applied to Parameters with different units.")
        except AttributeError:
            self_si = self.si_units
            other_si = Parameter(other, self_si.units)
        if isinstance(self_si.value, list):
            if isinstance(other_si.value, list):
                assert len(self_si.value) == len(other_si.value), "Lists must be the same length"
                value = [op_func(self_si.value[i], other_si.value[i]) for i in range(len(self_si.value))]
            else:
                value = [op_func(self_si.value[i], other_si.value) for i in range(len(self_si.value))]
        else:
            value = op_func(self_si.value, other_si.value if isinstance(other, Parameter) else other)
        units = combine_units(self_si.units, other_si.units, op_func)
        return Parameter(value, self_si.units)

    def __add__(self, other: float | list | Parameter) -> Parameter:
        return self._apply_operator(other, operator.add)

    def __sub__(self, other: float | list | Parameter) -> Parameter:
        return self._apply_operator(other, operator.sub)

    def __mul__(self, other: float | list | Parameter) -> Parameter:
        return self._apply_operator(other, operator.mul)

    def __truediv__(self, other: float | list | Parameter) -> Parameter:
        return self._apply_operator(other, operator.truediv)

    def __floordiv__(self, other: float | list | Parameter) -> Parameter:
        return self._apply_operator(other, operator.floordiv)
    
    def __mod__(self, other: float | list | Parameter) -> Parameter:
        return self._apply_operator(other, operator.mod)
    
    def __pow__(self, other: float | list | Parameter) -> Parameter:
        return self._apply_operator(other, operator.pow)

    def __gt__(self, other: float | list | Parameter) -> Parameter:
        return self._apply_operator(other, operator.gt)
    
    def __ge__(self, other: float | list | Parameter) -> Parameter:
        return self._apply_operator(other, operator.ge)
    
    def __lt__(self, other: float | list | Parameter) -> Parameter:
        return self._apply_operator(other, operator.lt)
    
    def __le__(self, other: float | list | Parameter) -> Parameter:
        return self._apply_operator(other, operator.le)
    
    def __abs__(self) -> Parameter:
        return Parameter(abs(self.value), self.units)
    
    def __neg__(self) -> Parameter:
        return Parameter(-self.value, self.units)

    def __float__(self) -> float:
        return float(self.value)

    def __iter__(self) -> Iterable:
        return iter(cast_to_list(self.value))

    def __len__(self) -> int:
        return len(cast_to_list(self.value))


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


        def find_indexes_of_char(string_list: list, char: str):
            return [i for i, s in enumerate(string_list) if char in s]



        def get_SI_factor(units: str) -> float:
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

        
        def get_SI_units(units: str) -> str:
            '''Convert the units to SI units'''
            # Split the units by either "/" or "."
            unit_components, separators = split_string_with_separators(units)
            separators = [''] + separators

            # Loop over the split components and look up their conversion factors in the mapping
            converted_units = []
            for component, separator in itertools.zip_longest(unit_components, separators):
                if component in UNITS:
                    converted_units.append(UNITS[component])
                if separator == '^':
                    try:
                        exponent = int(component)
                        converted_units.append(str(exponent))
                    except ValueError:
                        raise ValueError(f"Exponent {component} is not an integer")
                else:
                    logging.error(f"Unit {component} not found in UNITS dictionary")

            while len(separators) < len(converted_units):
                separators.append('')

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
    '''
    Parameters class
    '''
    @property
    def table(self) -> PrettyTable:
        '''
        Return a pretty table of the parameters
        '''
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
                cell_units = '-'
            else:
                cell_value = value
                cell_units = '-'
            
            table.add_row([key, cell_value, cell_units])
            
        return table


    @property
    def si_units(self) -> Parameters:
        return Parameters({key: param.si_units for key, param in self.items()})
    
    @property
    def values_only(self) -> Parameters:
        '''
        Return a dictionary of values in SI units only
        '''
        return Parameters({k: v.value for k, v in self.si_units.items()})

    @property
    def grouped(self) -> Parameters:
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
    
    def get_multi(self, inclusions: list) -> dict:
        return {inc: self[inc] for inc in inclusions}

    def get_common(self, prefix: str) -> list:
        '''
        Get the common value for a parameter
        '''
        if dataclasses.is_dataclass(self):
            return {name: getattr(self, name) for name in self.__dataclass_fields__ if name.startswith(prefix)}
        return [v.value
            for k,v in self.items()
            if k.startswith(prefix)]

    def items(self) -> list:
        if dataclasses.is_dataclass(self):
            return [(name, getattr(self, name)) for name in self.__dataclass_fields__]
        else:
            return [(key, self[key]) for key in self]

def tabulate_object_attrs(obj: object) -> PrettyTable:
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

def factor(data: float | Iterable, factor: float) -> list:
    '''Factor data by a factor'''
    return [d * factor for d in data] if is_iterable(data) else data * factor

def flatten_dict(d:dict, parent_key:str='', sep:str='__') -> dict:
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + str(k) if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def dict_to_parameters(d:dict, convert_to_si=False) -> Parameters:
    '''Convert a dictionary to a Parameters object'''
    flattened_dict = flatten_dict(d)
    parameters = Parameters({key: Parameter(*val) for key, val in flattened_dict.items()})
    return parameters.si_units if convert_to_si else parameters


def dicts_to_parameters(d: dict, convert_to_si: bool=False) -> dict[Parameters]:
    '''Convert a dictionary of dictionaries to a dictionary of Parameters objects'''
    return {k: dict_to_parameters(v, convert_to_si=convert_to_si) for k, v in d.items()}


def read_parameters_from_yaml(filepath: str | Path) -> Parameters:
    '''Parse a yaml file to a Parameters object'''
    parameters_dict = read_yaml(filepath)
    return dicts_to_parameters(parameters_dict)


def main():
    pass


if __name__ == "__main__":
    main()
