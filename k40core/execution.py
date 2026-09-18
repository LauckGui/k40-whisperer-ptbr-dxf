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


def origin_ordered_instance_offsets(document: JobDocument,
                                    home_on_right: bool = False):
    """Order active placements from the machine-side top corner.

    Model Y grows upward, while the K40 work-area origin is on the upper edge.
    Raw row order therefore starts at the physically farthest row.  Execution
    reverses that vertical order and traverses each row away from the selected
    upper-left/upper-right home without changing stable grid indices.
    """
    placements = document_instance_offsets(document)
    if not document.arrays or len(placements) < 2:
        return placements
    array = document.arrays[0]
    object_bounds = {
        item.id: item.bounds
        for item in [*document.vectors, *document.rasters, *document.fills]
    }
    bounds = referenced_bounds(array, object_bounds)
    all_offsets = tuple(instance_offsets(array, bounds, include_disabled=True))
    top = max(bounds.max_y + dy for dx, dy in all_offsets)
    if home_on_right:
        side = max(bounds.max_x + dx for dx, dy in all_offsets)
    else:
        side = min(bounds.min_x + dx for dx, dy in all_offsets)

    def order_key(placement):
        index, dx, dy = placement
        row_distance = top - (bounds.max_y + dy)
        edge = bounds.max_x + dx if home_on_right else bounds.min_x + dx
        return row_distance, abs(edge-side), index

    return tuple(sorted(placements, key=order_key))


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


def standalone_egv_jobs(chunks):
    """Wrap operation chunks as independent controller jobs.

    Raster mode can leave controller-side stepping state active until the
    terminating ``F`` command is processed.  Replacing that terminator with
    ``@`` is safe when joining the traditional, single raster operation, but
    not when alternating raster and vector operations for every array item.
    Keeping every chunk self-contained prevents a residual raster step from
    shifting the following vector operation and accumulating between pieces.
    """
    jobs = []
    for chunk, passes in chunks:
        for unused in range(max(0, int(float(passes)))):
            jobs.append([ord("I"), *chunk])
    return jobs
