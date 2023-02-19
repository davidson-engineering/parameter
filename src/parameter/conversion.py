from math import pi

TO_SI_FACTOR = {
    'km': 1e3,
    "m": 1,
    "mm": 1 / 1e3,
    'um': 1e-6,
    'nm': 1e-9,
    "deg": pi / 180,
    "rad": 1,
    "g": 1 / 1e3,
    "kg": 1,
    "-": 1,
    "s": 1,
    "min": 60,
    "rev": 2 * pi,
    "hour": 3600,
}

TO_SI_UNITS = {
    'km': 'm',
    "m": "m",
    "mm": "m",
    'um': 'm',
    'nm': 'm',
    "deg": "rad",
    "rad": "rad",
    "g": "kg",
    "kg": "kg",
    "-": "-",
    "s": "s",
    "min": "s",
    "rev": "rad",
    "hour": "s",
}
