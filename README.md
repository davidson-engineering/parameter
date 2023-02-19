# Parameter
## A class for handling parameters

- Creates *Parameter* objects, that can be converted to SI units for calculations.
- *Parameter* objects store original values and units.
- *Parameter* objects can be read from a .yml file, or from a dictionary.
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

## Read parameters from .yaml file, and 
```python
    from parameter.parameter import read_parameters_from_yaml, Parameters

    # Read in a .yaml file containing nested dictionaries of parameters
    parameters_dict = read_parameters_from_yaml("path/to/file.yaml")

    # Select a set of parameters
    parameters_set = parameters["subset_parameters"]

```

## Print out a neat table
```python
    # Print out a neat table using PrettyTable
    table = parameters_set.as_table()
    print(table)

    +------------------------+-------+-------+
    |        Property        | Value | Units |
    +------------------------+-------+-------+
    |      base_zheight      |   0   |   m   |
    |      nacelle_mass      |  1500 |   g   |
    |     nacelle_radius     |  150  |   mm  |
    | arm_reference_angles_0 |   0   |  deg  |
    | arm_reference_angles_1 |  120  |  deg  |
    | arm_reference_angles_2 |  240  |  deg  |
    |      distal_cogs       |  0.5  |   -   |
    |   end_affector_cog_x   |   0   |   mm  |
    |   end_affector_cog_y   |   0   |   mm  |
    |   end_affector_cog_z   |   0   |   mm  |
    +------------------------+-------+-------+

    # Print out the parameters in SI units
    table_SI = parameters_set.to_SI().as_table()
    print(table_SI)

    +------------------------+-------+-------+
    |        Property        | Value | Units |
    +------------------------+-------+-------+
    |      base_zheight      |   0   |   m   |
    |      nacelle_mass      |  1.5  |   kg  |
    |     nacelle_radius     |  0.15 |   m   |
    | arm_reference_angles_0 |  0.0  |  rad  |
    | arm_reference_angles_1 | 2.094 |  rad  |
    | arm_reference_angles_2 | 4.189 |  rad  |
    |      distal_cogs       |  0.5  |   -   |
    |   end_affector_cog_x   |  0.0  |   m   |
    |   end_affector_cog_y   |  0.0  |   m   |
    |   end_affector_cog_z   |  0.0  |   m   |
    +------------------------+-------+-------+
```

## Paramters class can be subclassed by a dataclass
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
    params_subclass_object_si = params_subclass_object.to_SI()
```
