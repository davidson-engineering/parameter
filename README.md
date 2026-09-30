# engparams

Engineering parameters with units, for studies, simulations and reports.

- Keep a study's inputs in a readable YAML file, each value in the units it was specified in.
- Load them into nested `Parameters`, convert them to SI and hand plain numbers to your calculation.
- Do unit-safe arithmetic: `Parameter(10, "m") / Parameter(2, "s")` is `5 m/s`, and adding metres to seconds is an error.
- Print parameter tables for reports as text, Markdown, HTML, CSV or LaTeX, from Python or the command line.

Units are handled by [pint](https://pint.readthedocs.io), so every unit pint knows works, and
parameters interoperate with pint quantities and numpy.

## Installation

```console
pip install engparams

# with pydantic support, for validated parameter schemas
pip install "engparams[pydantic]"

# the development version
pip install "engparams @ git+https://github.com/davidson-engineering/parameter.git"
```

Requires Python 3.11 or newer.

## Quick start

Write the parameters in YAML, in whatever units are natural:

```yaml
# robot.yaml
arm:
  length: [1.2, m]
  mass: 18 kg
  joint_angles: [[0, 120, 240], deg]
motor:
  max_speed: 3000 rpm
  torque:
    value: 12
    units: N.m
    description: Continuous torque
payload: [5000, g]
gear_ratio: 50
controller: RC-100
```

Load them, look them up, and convert them:

```pycon
>>> from engparams import Parameter, Parameters
>>> params = Parameters.from_yaml("robot.yaml")
>>> params["arm.length"]
Parameter(1.2, 'm')
>>> params.motor.max_speed
Parameter(3000, 'rpm')
>>> params.motor.torque * params.gear_ratio
Parameter(600, 'N.m')
>>> (params.motor.max_speed / params.gear_ratio).to("deg/s")
Parameter(360.0, 'deg/s')
>>> print(params.to_si())
+------------------+----------------------+-------+-------------------+
| Parameter        |                Value | Units | Description       |
+------------------+----------------------+-------+-------------------+
| arm.length       |                  1.2 | m     |                   |
| arm.mass         |                   18 | kg    |                   |
| arm.joint_angles | [0, 2.0944, 4.18879] | rad   |                   |
| motor.max_speed  |              314.159 | rad/s |                   |
| motor.torque     |                   12 | N.m   | Continuous torque |
| payload          |                    5 | kg    |                   |
| gear_ratio       |                   50 | -     |                   |
| controller       |               RC-100 | -     |                   |
+------------------+----------------------+-------+-------------------+

```

Hand plain SI numbers to a calculation:

```pycon
>>> si = params.to_si().magnitudes()
>>> si["payload"], si["motor"]["torque"]
(5.0, 12)

```

## Parameter files

Each leaf of a parameter file (or of a dict passed to `Parameters`) can be written as:

| Form | Example | Result |
| --- | --- | --- |
| `[value, units]` | `[150, mm]` | `Parameter(150, 'mm')` |
| array and units | `[[0, 120, 240], deg]` | `Parameter([0, 120, 240], 'deg')` |
| number with units | `150 mm` | `Parameter(150, 'mm')` |
| mapping | `{value: 150, units: mm, description: Stroke}` | `Parameter(150, 'mm', description='Stroke')` |
| number or list of numbers | `50` | `Parameter(50, '-')` (dimensionless) |
| anything else | `RC-100`, `"0042"`, `2024-01-01`, `true` | a non-numeric parameter, kept as is |

Nested mappings become groups, and a mapping with a `value` key is a single parameter, so
`value` cannot be used as a name. YAML is read with YAML 1.2 rules: `1e-3` is a number, and
`on`, `yes` and dates are text.

Units are written as pint understands them, with two conventions of their own: `.` multiplies
(`N.m`, `kg.m^2`) and `-` means dimensionless. A product after `/` needs parentheses, as in
`W/(m.K)`, because `W/m.K` would mean W.K/m. Mistakes are reported with their location, so a
typo in a large file is easy to find:

```pycon
>>> Parameters({"motor": {"conductivity": [0.6, "W/m.K"]}})
Traceback (most recent call last):
...
engparams.errors.UnitError: motor.conductivity: invalid units 'W/m.K': ambiguous, put the units after '/' in parentheses, as in 'W/(m.K)'
>>> Parameters({"motor": {"torque": [12, "N.mm."]}})
Traceback (most recent call last):
...
engparams.errors.UnitError: motor.torque: invalid units 'N.mm.': unexpected '.'

```

## Parameter

A `Parameter` is an immutable value with units. It can be a number, a numpy array or, for
bookkeeping, a non-numeric value such as a name or flag.

```pycon
>>> Parameter(10, "m") / Parameter(2, "s")
Parameter(5.0, 'm/s')
>>> Parameter(1, "ft") + Parameter(6, "inch")
Parameter(1.5, 'ft')
>>> Parameter(2, "m") ** 2
Parameter(4, 'm^2')
>>> Parameter(1, "m") + 1
Traceback (most recent call last):
...
pint.errors.DimensionalityError: Cannot convert from 'meter' to 'dimensionless'

```

Comparisons convert units first, and `==` allows for floating point error (see
`Parameter.isclose` for control over the tolerance):

```pycon
>>> Parameter(1, "m") == Parameter(1000, "mm")
True
>>> Parameter(300, "mm") < Parameter(1, "ft")
True
>>> Parameter(0.1, "m") + Parameter(0.2, "m") == Parameter(0.3, "m")
True

```

Convert to any compatible units with `to()`, or to SI with `to_si()`. SI conversion keeps named
SI units, so a torque in `kN.mm` becomes `N.m` rather than `kg.m^2/s^2`:

```pycon
>>> Parameter(1, "mile").to("km")
Parameter(1.609344, 'km')
>>> Parameter(3, "kN.mm").to_si()
Parameter(3.0, 'N.m')
>>> Parameter(0.1, "kg/mm^3").to_si()
Parameter(100000000.0, 'kg/m^3')
>>> Parameter(20, "degC").to_si()
Parameter(293.15, 'K')

```

Parameters work with numpy functions, and with pint quantities through `.quantity`:

```pycon
>>> import numpy as np
>>> np.hypot(Parameter(3, "m"), Parameter(400, "cm"))
Parameter(5.0, 'm')
>>> Parameter([1, 2, 3], "m").to("mm")
Parameter([1000.0, 2000.0, 3000.0], 'mm')
>>> f"{Parameter(3.14159, 'm'):.2f}"
'3.14 m'

```

## Parameters

`Parameters` is a nested mapping of groups and parameters. Items can be read with a dotted
path (`params["arm.length"]`) or as attributes (`params.arm.length`), and set from any of the
forms a parameter file accepts:

```pycon
>>> params["arm.reach"] = "0.9 m"
>>> params.arm.reach
Parameter(0.9, 'm')
>>> "arm.reach" in params
True

```

`merge()` layers overrides onto a copy, which suits studies built from a baseline:

```pycon
>>> heavy = params.merge({"arm": {"mass": [25, "kg"]}, "payload": "8 kg"})
>>> heavy.arm.mass, heavy.arm.length, params.arm.mass
(Parameter(25, 'kg'), Parameter(1.2, 'm'), Parameter(18, 'kg'))

```

`stack()` turns a group into a vector, converting to the units of its first member:

```pycon
>>> cog = Parameters({"x": [50, "mm"], "y": [-0.001, "m"], "z": [0, "mm"]})
>>> cog.stack()
Parameter([50.0, -1.0, 0.0], 'mm')

```

Other methods:

- `flatten()` returns a flat dict of parameters keyed by path.
- `to_dict()` and `to_yaml(path)` write data that `Parameters(...)` and `from_yaml()` read back.
- `copy()` copies the group structure.

## Tables

`print(params)` shows a text table. `render()` produces other formats, with floats shown to
`precision` significant figures:

```pycon
>>> print(params.arm.render("markdown", precision=3))
| Parameter    |         Value | Units |
| :----------- | ------------: | :---- |
| length       |           1.2 | m     |
| mass         |            18 | kg    |
| joint_angles | [0, 120, 240] | deg   |
| reach        |           0.9 | m     |

```

Table formats are `text`, `markdown`, `csv`, `html` and `latex`. The `yaml` and `json` formats
write the parameters losslessly instead. For full control, `params.table()` returns a
[PrettyTable](https://github.com/prettytable/prettytable). In Jupyter, a `Parameters` displays
as an HTML table.

## Validation with pydantic

With the `pydantic` extra, `Parameter` and `Parameters` can be pydantic fields. They accept every
parameter file form, and `Dimension` checks units:

```pycon
>>> from typing import Annotated
>>> from pydantic import BaseModel, ValidationError
>>> from engparams import Dimension
>>> class Arm(BaseModel):
...     length: Annotated[Parameter, Dimension("[length]")]
...     mass: Annotated[Parameter, Dimension("kg")]
>>> Arm(length=[1.2, "m"], mass="18 kg").length
Parameter(1.2, 'm')
>>> try:
...     Arm(length="1.2 s", mass="18 kg")
... except ValidationError as error:
...     print(error.errors()[0]["msg"])
Value error, expected units compatible with '[length]', got 's'

```

`Dimension` also works without pydantic: `Dimension("[length]").validate(parameter)`.

## Command line

The `engparams` command shows a parameter file as a table, optionally in SI units, or converts
it to another format:

```console
$ engparams robot.yaml motor --si
+-----------+---------+-------+-------------------+
| Parameter |   Value | Units | Description       |
+-----------+---------+-------+-------------------+
| max_speed | 314.159 | rad/s |                   |
| torque    |      12 | N.m   | Continuous torque |
+-----------+---------+-------+-------------------+

$ engparams robot.yaml --si --format markdown > parameters.md
```

Formats are `text`, `markdown`, `csv`, `html`, `latex`, `yaml` and `json`.

## Extending

- **Units**: `engparams.define("smoot = 1.7018 * m")` adds a unit using
  [pint's syntax](https://pint.readthedocs.io/en/stable/advanced/defining.html). Parameters use
  pint's application registry (`engparams.ureg`), shared with any other pint code in the program.
- **SI conversion**: non-SI units convert to the first unit in
  `engparams.units.SI_DERIVED_UNITS` with the same dimensionality (`psi` to `Pa`, `kWh` to `J`),
  otherwise to SI base units. Add entries to prefer others.
- **Unit symbols**: `engparams.units.SYMBOLS` overrides how units are written in results.
- **Calculations**: `Parameter.quantity` gives a pint quantity, and `Parameter(quantity)` wraps one
  back up.
- **Schemas**: pydantic models, as above.

## Migrating from 0.1

Version 0.2 renames the package from `parameter` to `engparams` (on PyPI, `parameter` is an
unrelated project) and rebuilds it on pint. The 0.1 unit handling had errors that silently gave
wrong results: comparisons were almost always true, compound units such as `kg/mm^3` converted
by the wrong factor, and products and quotients kept the units of their first operand.

| 0.1 | 0.2 |
| --- | --- |
| `from parameter.parameter import ...` | `from engparams import ...` |
| `param.si_units` | `param.to_si()` |
| `read_parameters_from_yaml(path)` | `Parameters.from_yaml(path)` |
| `dict_to_parameters(d)` | `Parameters(d)` |
| `params.table_pretty` | `params.table()` |
| `params.values_only` | `params.to_si().magnitudes()` |
| flat keys such as `end_affector_cog__x` | nested groups: `params["end_affector_cog.x"]` |
| `group_by_prefix()`, `get_common_value()` | `params.end_affector_cog.stack()` |
| dataclasses inheriting from `Parameters` | pydantic models, or `Parameters(dataclasses.asdict(obj))` for tables |
| `param.value = ...` | parameters are immutable, so assign a new one |

Behaviour changes to be aware of:

- Adding or comparing parameters with incompatible units raises `DimensionalityError`, as does
  adding a plain number to a parameter with units.
- `float(parameter)` needs a dimensionless parameter. Use `parameter.to("m").value` for a
  number in chosen units.
- `str(Parameter(1, "m"))` is `"1 m"`, with a space.

## Development

```console
uv sync
uv run pytest
uv run ruff check && uv run ruff format --check && uv run mypy
```

The examples in this README are run as part of the test suite.

To release, set `__version__` in `src/engparams/__init__.py`, merge to `main`, and publish a
GitHub release tagged with that version (for example `v0.2.0`). The Release workflow tests,
builds and publishes it to PyPI using trusted publishing.
