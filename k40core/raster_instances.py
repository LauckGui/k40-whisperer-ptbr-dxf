"""Procedural repetition helpers for attached raster images.

The source bitmap is intentionally kept once.  Arrays repeat its generated
scanlines and preview placement, avoiding a potentially enormous composed
bitmap for grayscale jobs.
"""

from __future__ import annotations

from .arrays import instance_offsets, referenced_bounds
from .model import Bounds, JobDocument
from .raster_paths import RasterScanlines


def raster_instance_offsets(document: JobDocument | None) -> tuple[tuple[float, float], ...]:
    """Return active array translations for a source bitmap tied to the job."""
    if document is None or not document.arrays:
        return ((0.0, 0.0),)
    array = document.arrays[0]
    object_bounds = {
        item.id: item.bounds
        for item in [*document.vectors, *document.rasters, *document.fills]
    }
    bounds = referenced_bounds(array, object_bounds)
    return tuple(instance_offsets(array, bounds))


attached_raster_offsets = raster_instance_offsets


def raster_content_bounds(image, dpi: float, vector_bounds: Bounds,
                          vector_offset_x_mm: float = 0.0,
                          vector_offset_y_mm: float = 0.0,
                          white_is_empty: bool = False) -> Bounds | None:
    """Map the non-transparent/non-white pixel box into model millimetres."""
    if dpi <= 0.0:
        raise ValueError("O DPI precisa ser positivo.")
    if "A" in image.getbands():
        pixel_bounds = image.getchannel("A").getbbox()
    elif white_is_empty:
        from PIL import ImageOps
        pixel_bounds = ImageOps.invert(image.convert("L")).getbbox()
    else:
        pixel_bounds = (0, 0, image.width, image.height)
    if pixel_bounds is None:
        return None
    mm_per_pixel = 25.4/dpi
    left, top, right, bottom = pixel_bounds
    canvas_height_mm = image.height*mm_per_pixel
    local = Bounds(
        left*mm_per_pixel,
        canvas_height_mm-bottom*mm_per_pixel,
        right*mm_per_pixel,
        canvas_height_mm-top*mm_per_pixel,
    )
    return Bounds(
        vector_bounds.min_x + local.min_x-vector_offset_x_mm,
        vector_bounds.min_y + local.min_y-vector_offset_y_mm,
        vector_bounds.min_x + local.max_x-vector_offset_x_mm,
        vector_bounds.min_y + local.max_y-vector_offset_y_mm,
    )


def preview_bitmap_offsets(canvas_bounds: Bounds, overall_bounds: Bounds,
                           instance_offsets_mm):
    """Offsets from the preview's top-left model origin for bitmap canvases."""
    return tuple(
        (canvas_bounds.min_x+dx-overall_bounds.min_x,
         canvas_bounds.max_y+dy-overall_bounds.max_y)
        for dx, dy in instance_offsets_mm
    )


def repeat_scanlines(scanlines: RasterScanlines,
                     offsets_mm) -> RasterScanlines:
    """Instance one bitmap's scanlines without replicating its pixels."""
    offsets = tuple(offsets_mm) or ((0.0, 0.0),)
    if len(offsets) == 1 and offsets[0] == (0.0, 0.0):
        return scanlines

    repeated = []
    hull = []
    maximum_loop = max((int(point[2]) for point in scanlines.ecoords), default=0) + 1
    for instance_index, (offset_x_mm, offset_y_mm) in enumerate(offsets):
        dx = float(offset_x_mm) / 25.4
        dy = float(offset_y_mm) / 25.4
        loop_offset = instance_index * maximum_loop
        repeated.extend([
            point[0] + dx, point[1] + dy, int(point[2]) + loop_offset,
            *point[3:],
        ] for point in scanlines.ecoords)
        hull.extend([point[0] + dx, point[1] + dy] for point in scanlines.hull_points)
    return RasterScanlines(
        repeated,
        scanlines.length_inches * len(offsets),
        scanlines.scanline_count * len(offsets),
        hull,
    )
