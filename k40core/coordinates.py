"""Conversions between internal machine coordinates and operator-facing values."""


def display_y(machine_y):
    """Show distance below machine origin as a positive value."""
    return -float(machine_y)


def machine_y(display_value):
    """Convert positive downward UI distance to the internal negative Y axis."""
    return -float(display_value)
