# Parameter
### A class for handling parameters

- Creates *Parameter* objects, that can be converted to SI units for calculations.
- *Parameter* objects store original values and units.
- Objects can be read from a yaml file, or from a dictionary.


```
    param_a = Parameter(1, "m")
    param_b = Parameter(2, "mm")
    param_c = Parameter([3,4,5], "mm/s")
    param_d = Parameter(3, "mm/min")
    param_e = Parameter(2, "deg/min")
    param_f = Parameter(100, "rev/min")
    param_g = Parameter(1000, "rev/hour")

```
