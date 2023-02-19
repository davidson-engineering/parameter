# Parameter
### A class for handling parameters

- Creates *Parameter* objects, that can be converted to SI units for calculations.
- *Parameter* objects store original values and units.
- *Parameter* objects can be read from a .yml file, or from a dictionary.
- A dataclass can inherit from *Parameters*, allowing for specific parameter names to be ensured.


```
    param_a = Parameter(1, "m")
    param_b = Parameter(2, "mm")
    param_c = Parameter([3,4,5], "mm/s")
    param_d = Parameter(3, "mm/min")
    param_e = Parameter(2, "deg/min")
    param_f = Parameter(100, "rev/min")
    param_g = Parameter(1000, "rev/hour")

```
# Read parameters from .yaml file, and print a neat table
```
    from parameter.parameter import parse_yaml_to_parameters, Parameters

    # Read in a .yaml file containing nested dictionaries of parameters
    parameters_dict = parse_yaml_to_parameters("path/to/file.yaml")

    # Select a set of parameters
    parameters_set = parameters["subset_parameters"]

    # Print out a neat table using PrettyTable
    table = parameters_set.as_table()
    print(table)

    # Print out the parameters in SI units
    table_SI = parameters_set.to_SI().as_table()
    print(table_SI)

```

```
    @dataclass
    class ParametersSubclass(Parameters):
        param_a: Parameter
        param_b: Parameter
        param_c: Parameter


     dict = {
        param_a: Parameter(1, "m"),
        param_b: Parameter(2, "mm"),
        param_c: Parameter([3,4,5], "mm/s"),
     }
```
