"""Procedural instance-array calculations without cloning source geometry."""

from __future__ import annotations

import math

from .model import Bounds, InstanceArray


def referenced_bounds(array: InstanceArray, object_bounds: dict[str, Bounds | None]) -> Bounds:
    if array.reference_bounds is not None:
        return array.reference_bounds
    bounds = Bounds.union(object_bounds.get(object_id) for object_id in array.object_ids)
    if bounds is None:
        raise ValueError("Os objetos do array não possuem geometria mensurável.")
    return bounds


def array_steps(array: InstanceArray, bounds: Bounds) -> tuple[float, float]:
    bounds = array.reference_bounds or bounds
    step_x = bounds.width + array.spacing_mm
    step_y = bounds.height + array.spacing_mm + array.row_adjust_y_mm
    if array.columns > 1 and step_x <= 0.0:
        raise ValueError("O passo horizontal do array precisa ser positivo.")
    if array.rows > 1 and step_y <= 0.0:
        raise ValueError("O passo vertical do array precisa ser positivo.")
    return step_x, step_y


def instance_offsets(array: InstanceArray, bounds: Bounds, include_disabled=False):
    """Yield translations, omitting user-disabled placements by default."""
    step_x, step_y = array_steps(array, bounds)
    disabled = set(array.disabled_indices)
    for row in range(array.rows):
        stagger = array.stagger_x_mm if array.mode == "staggered" and row % 2 else 0.0
        for column in range(array.columns):
            index = row*array.columns + column
            if not include_disabled and index in disabled:
                continue
            yield column*step_x+stagger, row*step_y


def instance_array_bounds(array: InstanceArray,
                          object_bounds: dict[str, Bounds | None]) -> Bounds:
    base = referenced_bounds(array, object_bounds)
    # Disabled slots keep their physical place in the layout. This avoids
    # moving the job origin when the first or outermost piece is ignored.
    offsets = tuple(instance_offsets(array, base, include_disabled=True))
    return Bounds(
        base.min_x + min(item[0] for item in offsets),
        base.min_y + min(item[1] for item in offsets),
        base.max_x + max(item[0] for item in offsets),
        base.max_y + max(item[1] for item in offsets),
    )


def maximum_array_counts(bounds: Bounds, available_width_mm: float,
                         available_height_mm: float, spacing_mm: float,
                         mode: str = "grid", stagger_x_mm: float = 0.0,
                         row_adjust_y_mm: float = 0.0) -> tuple[int, int]:
    """Calculate the largest row/column counts fitting the given rectangle."""
    probe = InstanceArray(
        "probe", ("probe",), spacing_mm=spacing_mm, mode=mode,
        stagger_x_mm=stagger_x_mm, row_adjust_y_mm=row_adjust_y_mm,
    )
    step_x, step_y = array_steps(probe, bounds)
    max_rows = max(1, int(math.floor((available_height_mm-bounds.height)/step_y))+1)

    def columns_for(row_count):
        overhang = (abs(stagger_x_mm)
                    if mode == "staggered" and row_count > 1 else 0.0)
        return max(0, int(math.floor(
            (available_width_mm-bounds.width-overhang)/step_x
        ))+1)

    candidates = [(columns_for(1), 1)]
    if max_rows > 1:
        candidates.append((columns_for(max_rows), max_rows))
    fitting = [item for item in candidates if item[0] > 0]
    return max(fitting, key=lambda item: item[0]*item[1], default=(1, 1))
