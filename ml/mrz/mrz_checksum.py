"""ICAO 9303 Checksum Validation and Calculation Engine.
Supports TD1, TD2, TD3 MRZ check digits and composite checksum verification.
"""
from typing import Optional

_WEIGHTS = (7, 3, 1)

def char_value(c: str) -> int:
    """Returns numerical value of MRZ character according to ICAO Doc 9303."""
    if c == "<":
        return 0
    if c.isdigit():
        return int(c)
    if "A" <= c <= "Z":
        return ord(c) - ord("A") + 10
    return -1

def calculate_check_digit(field_val: str) -> int:
    """Computes check digit modulo 10 with 7-3-1 weighting."""
    total = 0
    for i, c in enumerate(field_val):
        v = char_value(c)
        if v < 0:
            return -1
        total += v * _WEIGHTS[i % 3]
    return total % 10

def verify_check_digit(field_val: str, expected_digit: str) -> bool:
    """Verifies that the computed check digit matches the expected character."""
    computed = calculate_check_digit(field_val)
    if computed < 0:
        return False
    exp_val = 0 if expected_digit == "<" else (int(expected_digit) if expected_digit.isdigit() else -1)
    return computed == exp_val
