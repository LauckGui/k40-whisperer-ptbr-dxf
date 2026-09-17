"""Execution planning helpers for procedural arrays.

The controller protocol has no subroutine/loop opcode.  These helpers keep the
source geometry procedural on the host, so it is prepared once and translated
cheaply for each active placement even though every motion still has to be sent
to the controller.
"""

from __future__ import annotations

from .arrays import instance_offsets, referenced_bounds
from .model import Bounds, InstanceArray, JobDocument


def indexed_instance_offsets(array: InstanceArray, bounds: Bounds):
    """Return active placements while retaining their stable grid indices."""
    active_offsets = iter(instance_offsets(array, bounds))
    disabled = set(array.disabled_indices)
    result = []
    for index in range(array.columns * array.rows):
        if index not in disabled:
            result.append((index, *next(active_offsets)))
    return tuple(result)


def document_instance_offsets(document: JobDocument):
    if not document.arrays:
        return ((0, 0.0, 0.0),)
    array = document.arrays[0]
    object_bounds = {
        item.id: item.bounds
        for item in [*document.vectors, *document.rasters, *document.fills]
    }
    return indexed_instance_offsets(array, referenced_bounds(array, object_bounds))


def translate_ecoords(ecoords, dx_inches: float, dy_inches: float):
    """Translate legacy ECoords without mutating the cached base geometry."""
    return [
        [point[0] + dx_inches, point[1] + dy_inches, *point[2:]]
        for point in ecoords
    ]


def split_repeated_ecoords(ecoords, instance_count: int):
    """Split scanlines emitted by repeat_scanlines back into placements."""
    if instance_count < 1:
        raise ValueError("A quantidade de instâncias precisa ser positiva.")
    if len(ecoords) % instance_count:
        raise ValueError("As coordenadas raster não correspondem ao array ativo.")
    size = len(ecoords) // instance_count
    return tuple(ecoords[index * size:(index + 1) * size]
                 for index in range(instance_count))
