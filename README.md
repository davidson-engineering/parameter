# Parameter
### A class for handling parameters

- Creates *Parameter* objects, that can be converted to SI units for calculations.
- *Parameter* objects store original values and units.
- *Parameter* objects can be read from a .yml file, or from a dictionary.
- A dataclass can inherit from *Parameters*, allowing for specific parameter names to be ensured.
- Operators multiply ('/'), divide ('.') and exponents('^') are supported.


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
# Read parameters from .yaml file, and print a neat table
```python
    from parameter.parameter import read_parameters_from_yaml, Parameters

    # Read in a .yaml file containing nested dictionaries of parameters
    parameters_dict = read_parameters_from_yaml("path/to/file.yaml")

    # Select a set of parameters
    parameters_set = parameters["subset_parameters"]

    # Print out a neat table using PrettyTable
    table = parameters_set.as_table()
    print(table)

    # Print out the parameters in SI units
    table_SI = parameters_set.to_SI().as_table()
    print(table_SI)

```

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
