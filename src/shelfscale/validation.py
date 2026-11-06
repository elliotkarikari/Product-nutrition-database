"""Numeric boundaries shared by scorers and API input adapters."""

import math


def number(value, name: str, *, positive: bool = False, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number.")
    try:
        value = float(value)
    except OverflowError:
        raise ValueError(f"{name} must be finite.") from None
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    if value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be {'positive' if positive else 'non-negative'}.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} cannot exceed {maximum}.")
    return value
