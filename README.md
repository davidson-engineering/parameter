# Parameter
## A class for handling parameters

- Creates *Parameter* objects, that can be converted to SI units for calculations.
- *Parameter* objects store original values and units.
- *Parameter* objects can be read from a YAML file, or from a dictionary.
- A dataclass can inherit from *Parameters*, allowing for specific parameter names to be ensured.
- Operators such as add, multiply, divide and exponent are supported:
    - Between Parameter objects, and other types of objects that also support these methods.
    - Also on units, such as rad/s, kg/m^2.
    - Note: exponents are not supported (yet) for unit outputs
- See [parameter.conversion.py](src/parameter/conversion.py) for a full list of all possible conversions. Custom conversions are easily added.

## Installation
Option 1: Install as module straight from github using pip
```console
# Install latest version of module
pip install 'parameter @ git+https://github.com/davidson-engineering/parameter.git'

# Alternatively, one can force a specific version to be installed
pip install 'parameter @ git+https://github.com/davidson-engineering/parameter.git@v0.1.0'
```

Option 2: For development, clone from github to folder, make .venv and install using pip
```console
git clone https://github.com/davidson-engineering/parameter.git
cd parameter
python -m .venv .venv
.venv/Scripts/activate.ps1 # If using powershell
source .venv/bin/activate # If using Unix / MacOS
pip install -e .
```

## Simple Example Usage
Some mixed units
```python
from parameter.parameter import Parameter

p_length_large = Parameter(1, "m")
p_length_small = Parameter(2, "mm")
p_speed = Parameter([3,4,5], "mm/s")
p_speed_slow = Parameter(3, "mm/min")
p_torque = Parameter(3, 'N.m')
p_torque_small = Parameter(3, 'N.mm')
p_torque_large = Parameter(3, 'kN.mm')
p_angular_speed = Parameter(2, "deg/min")
p_angular_speed_rpm = Parameter(100, "rev/min")
p_angular_speed_rph = Parameter(1000, "rev/hour")
p_moment_inertia = Parameter(0.1, "kg/m^2")

```

## Read Parameters from YAML
Read a set of several parameters from YAML file, and select a subset
```python
from parameter.parameter import read_parameters_from_yaml, Parameters

# Read in a YAML file containing nested dictionaries of parameters
parameters_dict = read_parameters_from_yaml("path/to/file.yaml")

# Select a set of parameters
parameters_set = parameters["subset_parameters"]

```

## Print out a pretty table
In both original and SI units
```python
# Print out a neat table using PrettyTable
table = parameters.table_pretty
print(table)
+-------------------------+-------+-------+
|        Parameter        | Value | Units |
+-------------------------+-------+-------+
|        singlename       |   1   |   m   |
|       base_zheight      |   0   |   m   |
|       nacelle_mass      |  1500 |   g   |
|      nacelle_radius     |  150  |   mm  |
| arm_reference_angles__0 |   0   |  deg  |
| arm_reference_angles__1 |  120  |  deg  |
| arm_reference_angles__2 |  240  |  deg  |
|       distal_cogs       |  0.5  |   -   |
|   end_affector_cog__x   |   50  |   mm  |
|   end_affector_cog__y   |   -1  |   mm  |
|   end_affector_cog__z   |   0   |   mm  |
+-------------------------+-------+-------+

# Print out the parameters in SI units
table_SI = parameters.si_units.table_pretty
print(table_SI)
+-------------------------+--------+-------+
|        Parameter        | Value  | Units |
+-------------------------+--------+-------+
|        singlename       |   1    |   m   |
|       base_zheight      |   0    |   m   |
|       nacelle_mass      |  1.5   |   kg  |
|      nacelle_radius     |  0.15  |   m   |
| arm_reference_angles__0 |  0.0   |  rad  |
| arm_reference_angles__1 | 2.094  |  rad  |
| arm_reference_angles__2 | 4.189  |  rad  |
|       distal_cogs       |  0.5   |   -   |
|   end_affector_cog__x   |  0.05  |   m   |
|   end_affector_cog__y   | -0.001 |   m   |
|   end_affector_cog__z   |  0.0   |   m   |
+-------------------------+--------+-------+
```

## Parameters class can be subclassed by a dataclass
Allows for easy creation of Parameter type objects with mandatory arguments
```python
from parameter.parameter import Parameter, Parameters

@dataclass
class ParametersSubclass(Parameters):
    param_a: Parameter
    param_b: Parameter
    param_c: Parameter


param_dict = {
    'param_a': Parameter(1, "m"),
    'param_b': Parameter(2, "mm"),
    'param_c': Parameter([3,4,5], "mm/s"),
}

params_subclass_object = ParametersSubclass(**param_dict)

params_subclass_object_si = params_subclass_object.si_units

print(params_subclass_object_si.table_pretty)
+-----------+-----------------------+-------+
| Parameter |         Value         | Units |
+-----------+-----------------------+-------+
|  param_a  |           1           |   m   |
|  param_b  |         0.002         |   m   |
|  param_c  | [0.003, 0.004, 0.005] |  m/s  |
+-----------+-----------------------+-------+
```

## Parameters with common names can be grouped together
Use the '__\*' suffix when specifying a grouped parameter name, where '\*' can be any character(s) of your choice.
Calling the .grouped property on a Parameters object will return a Parameters object, with all the values combined into a single list. Units will be common.
```python
from parameter.parameter import read_parameters_from_yaml, Parameters

parameters = Parameters(read_parameters_from_yaml("test/input_file.yaml")["test_parameters"])

print(parameters.table_pretty)
+-------------------------+-------+-------+
|        Parameter        | Value | Units |
+-------------------------+-------+-------+
|        singlename       |   1   |   m   |
|       base_zheight      |   0   |   m   |
|       nacelle_mass      |  1500 |   g   |
|      nacelle_radius     |  150  |   mm  |
| arm_reference_angles__0 |   0   |  deg  |
| arm_reference_angles__1 |  120  |  deg  |
| arm_reference_angles__2 |  240  |  deg  |
|       distal_cogs       |  0.5  |   -   |
|   end_affector_cog__x   |   50  |   mm  |
|   end_affector_cog__y   |   -1  |   mm  |
|   end_affector_cog__z   |   0   |   mm  |
+-------------------------+-------+-------+

print(parameters.grouped.table_pretty)
+----------------------+---------------+-------+
|      Parameter       |     Value     | Units |
+----------------------+---------------+-------+
| arm_reference_angles | [0, 120, 240] |  deg  |
|   end_affector_cog   |  [50, -1, 0]  |   mm  |
|      singlename      |       1       |   m   |
|     base_zheight     |       0       |   m   |
|     nacelle_mass     |      1500     |   g   |
|    nacelle_radius    |      150      |   mm  |
|     distal_cogs      |      0.5      |   -   |
+----------------------+---------------+-------+
```

### Operators are supported as well
```python
from parameter.parameter import Parameter

p_a = Parameter(1, "m")
p_b = Parameter(25, "mm")
assert p_a + p_b == Parameter(1.025, "m")
assert p_a - p_b == Parameter(0.975, "m")
assert p_a * p_b == Parameter(0.025, "m") # TODO: this should be m^2
assert p_a / p_b == Parameter(40, "m")
assert p_a + p_b == param_b + param_a

p_c = Parameter(300, "mm")
p_d = Parameter(40, "m")
assert p_d > p_c
assert p_c < p_d

p_e = Parameter(12, 'ft')
assert p_e + p_a != Parameter(13, 'ft')
assert p_e + p_a == Parameter(4.6576, 'm')

p_f = Parameter(3.6576, 'mm^3')
p_g = Parameter(3.6576E-9, 'm^3')
assert p_f == p_g # Note small allowance for error of 1E-10 (configurable)

# If operator is applied to an int,
# then Parameter will not be converted to SI automatically
p_h = Parameter(36.487, 'MPa')
assert p_h // 10 == 3
assert p_h.si_units // 1E6 == p_h // 1
```
