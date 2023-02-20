# Parameter
## A class for handling parameters

- Creates *Parameter* objects, that can be converted to SI units for calculations.
- *Parameter* objects store original values and units.
- *Parameter* objects can be read from a YAML file, or from a dictionary.
- A dataclass can inherit from *Parameters*, allowing for specific parameter names to be ensured.
- Operators multiply ('/'), divide ('.') and exponents('^') are supported.

## Example Usage
```python
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

## Read a set of several parameters from YAML file, and select a subset
```python
from parameter.parameter import read_parameters_from_yaml, Parameters

    # Read in a YAML file containing nested dictionaries of parameters
parameters_dict = read_parameters_from_yaml("path/to/file.yaml")

# Select a set of parameters
parameters_set = parameters["subset_parameters"]

```

## Print out a neat table, in both original and SI units
```python
# Print out a neat table using PrettyTable
table = parameters_set.table
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
table_SI = parameters_set.si_units.table
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
```python
@dataclass
class ParametersSubclass(Parameters):
    param_a: Parameter
    param_b: Parameter
    param_c: Parameter


    param_dict = {
    param_a: Parameter(1, "m"),
    param_b: Parameter(2, "mm"),
    param_c: Parameter([3,4,5], "mm/s"),
    }

params_subclass_object = ParameterSubclass(**param_dict)
params_subclass_object_si = params_subclass_object.si_units
```

## Parameters with common names can be grouped together with their values in one list
Use the '__*' suffix when specifying a parameter name, where '*' can be any character(s) of your choice.

```python
parameters = Parameters(read_parameters_from_yaml("test/input_file.yaml")["test_parameters"])
parameters.table

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
parameters.grouped.table
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