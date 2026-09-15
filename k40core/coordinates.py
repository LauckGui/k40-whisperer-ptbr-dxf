"""Conversions between internal machine coordinates and operator-facing values."""


def display_y(machine_y):
    """Show distance below machine origin as a positive value."""
    return -float(machine_y)


def machine_y(display_value):
    """Convert positive downward UI distance to the internal negative Y axis."""
    return -float(display_value)


def origin_for_reference(target_x, target_y, offset_x, offset_y,
                         home_on_right=False):
    """Resolve job origin so the selected reference lands on a UI target.

    ``target_y`` is positive downward as presented to the operator. X remains
    negative when the machine is configured with its home on the right.
    Offsets and returned coordinates use the internal machine coordinate system.
    """
    anchor_x = -float(target_x) if home_on_right else float(target_x)
    anchor_y = machine_y(target_y)
    return anchor_x-float(offset_x), anchor_y-float(offset_y)
