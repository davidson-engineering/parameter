from math import pi

DIMENSIONLESS = (1, '1', '-')

TO_SI_FACTOR = {
    '1': 1,
    1: 1,
    'km': 1e3,
    "m": 1,
    "mm": 1 / 1e3,
    'cm': 1 / 1e2,
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
    "N": 1,
    "kN": 1e3,
    "inch": 0.0254,
    "ft": 0.3048,
    "mile": 1609.344,
    "lbf": 4.4482216152605,
    "kip": 4448.2216152605,
    "psi": 6894.757293168361,
    "ksi": 6894757.293168361,
    "gal": 0.003785411784,
    "l": 0.001,
    'ml': 1e-6,
    'bar': 1e5,
    'kbar': 1e8,
    'Mbar': 1e11,
    'Gbar': 1e14,
    'Pa': 1,
    'kPa': 1e3,
    'MPa': 1e6,
    'GPa': 1e9,
    'TPa': 1e12,
    'lb': 0.45359237,
    'oz': 0.028349523125,
    'slug': 14.5939029372064,
    'stone': 6.35029318,
    'tonne': 1000,
    'ton': 907.18474,
    'kton': 907184.74,
    'long_ton': 1016.0469088,
    'short_ton': 907.18474,
}

TO_SI_UNITS = {
    '1': '1',
    1: 1,
    'km': 'm',
    "m": "m",
    "mm": "m",
    'cm': 'm',
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
    "N": "N",
    "kN": "N",
    "inch": "m",
    "ft": "m",
    "mile": "m",
    "lbf": "N",
    "kip": "N",
    "psi": "N/m^2",
    "ksi": "N/m^2",
    "gal": "m^3",
    "l": "m^3",
    'ml': 'm^3',
    'bar': 'Pa',
    'kbar': 'Pa',
    'Mbar': 'Pa',
    'Gbar': 'Pa',
    'Pa': 'Pa',
    'kPa': 'Pa',
    'MPa': 'Pa',
    'GPa': 'Pa',
    'TPa': 'Pa',
    'lb': 'kg',
    'oz': 'kg',
    'slug': 'kg',
    'stone': 'kg',
    'tonne': 'kg',
    'ton': 'kg',
    'kton': 'kg',
    'long_ton': 'kg',
    'short_ton': 'kg',
}
