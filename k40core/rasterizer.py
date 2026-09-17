"""Rasterization of resolution-independent filled job objects."""

from __future__ import annotations

import math

from .arrays import instance_offsets, referenced_bounds
from .model import Bounds, FillObject, JobDocument, LineSegment


class RasterizationError(ValueError):
    pass


def raster_pixel_count(bounds: Bounds, dpi: float) -> int:
    """Return the pixel count required for physical bounds at the given DPI."""
    if dpi <= 0.0:
        raise RasterizationError("O DPI precisa ser positivo.")
    width = max(1, int(math.ceil(bounds.width / 25.4 * dpi)))
    height = max(1, int(math.ceil(bounds.height / 25.4 * dpi)))
    return width*height


def dpi_for_pixel_budget(bounds: Bounds, requested_dpi: float,
                         maximum_pixels: int) -> float:
    """Lower DPI only when required to keep the working bitmap in budget."""
    if maximum_pixels <= 0:
        raise RasterizationError("O limite de pixels precisa ser positivo.")
    if raster_pixel_count(bounds, requested_dpi) <= maximum_pixels:
        return float(requested_dpi)
    area_inches = bounds.width/25.4 * bounds.height/25.4
    if area_inches <= 0.0:
        raise RasterizationError("O preenchimento não possui uma área rasterizável.")
    # Leave a small margin for ceil() on both dimensions.
    fitted = math.sqrt(maximum_pixels/area_inches)*0.999
    return max(1.0, min(float(requested_dpi), fitted))


def rasterize_fills(document: JobDocument, dpi: float, bounds: Bounds | None = None,
                    maximum_pixels: int = 100_000_000,
                    color_intensities=None, include_arrays: bool = True):
    """Render all raster-engrave fills to a monochrome Pillow image.

    White means laser off and black means laser on, matching the legacy raster
    pipeline. Geometry remains in the document and can be rendered again at a
    different DPI without reimporting.
    """
    from PIL import Image, ImageChops, ImageDraw

    visible_layers = {layer.id for layer in document.layers if layer.visible}
    fills = [item for item in document.fills
             if item.operation.value == "raster_engrave"
             and item.layer_id in visible_layers
             and item.metadata.get("fill_kind", "solid") == "solid"]
    if not fills:
        return None
    base_bounds = Bounds.union(
        [item.bounds for item in document.vectors]
        + [item.bounds for item in document.rasters]
        + [item.bounds for item in document.fills]
    )
    bounds = bounds or (document.bounds if include_arrays else base_bounds)
    if bounds is None or bounds.width <= 0 or bounds.height <= 0:
        raise RasterizationError("O preenchimento não possui uma área rasterizável.")
    if dpi <= 0:
        raise RasterizationError("O DPI precisa ser positivo.")

    width = max(1, int(math.ceil(bounds.width / 25.4 * dpi)))
    height = max(1, int(math.ceil(bounds.height / 25.4 * dpi)))
    pixel_count = width*height
    if pixel_count > maximum_pixels:
        raise RasterizationError(
            "Raster exigiria %d megapixels; reduza a resolução." %
            int(math.ceil(pixel_count / 1_000_000.0))
        )

    output = Image.new("L", (width, height), 255)
    intensity_regions = {}
    object_bounds = {
        item.id: item.bounds
        for item in [*document.vectors, *document.rasters, *document.fills]
    }
    offsets_by_object = {}
    if include_arrays:
        for array in document.arrays:
            offsets = tuple(instance_offsets(array, referenced_bounds(array, object_bounds)))
            for object_id in array.object_ids:
                offsets_by_object[object_id] = offsets

    def resolved_intensity(fill):
        if color_intensities and fill.color is not None:
            key = fill.color.hex_rgb.lower()
            if key in color_intensities:
                value = float(color_intensities[key])
                if not 0.0 <= value <= 1.0:
                    raise RasterizationError("Intensidade mapeada deve estar entre 0 e 1.")
                return value
        return fill.intensity

    def intensity_region(intensity):
        region = intensity_regions.get(intensity)
        if region is None:
            region = Image.new("1", (width, height), 0)
            intensity_regions[intensity] = region
        return region

    def pixel(point, fill, offset_x=0.0, offset_y=0.0):
        transformed = fill.transform.apply(point)
        return (
            (transformed.x + offset_x - bounds.min_x) / 25.4 * dpi,
            (bounds.max_y - transformed.y - offset_y) / 25.4 * dpi,
        )

    for fill in fills:
        intensity = resolved_intensity(fill)
        offsets = offsets_by_object.get(fill.id, ((0.0, 0.0),))
        if fill.fill_rule == "union":
            union_region = intensity_region(intensity)
            union_draw = ImageDraw.Draw(union_region)
            for offset_x, offset_y in offsets:
                for path in fill.paths:
                    vertices = []
                    for segment in path.segments:
                        if not isinstance(segment, LineSegment):
                            raise RasterizationError("Preenchimento precisa estar achatado antes da rasterização.")
                        if not vertices:
                            vertices.append(pixel(segment.start, fill, offset_x, offset_y))
                        vertices.append(pixel(segment.end, fill, offset_x, offset_y))
                    if len(vertices) >= 3:
                        union_draw.polygon(vertices, fill=1)
            continue

        for offset_x, offset_y in offsets:
            region = Image.new("1", (width, height), 0)
            for path in fill.paths:
                vertices = []
                for segment in path.segments:
                    if not isinstance(segment, LineSegment):
                        raise RasterizationError("Preenchimento precisa estar achatado antes da rasterização.")
                    if not vertices:
                        vertices.append(pixel(segment.start, fill, offset_x, offset_y))
                    vertices.append(pixel(segment.end, fill, offset_x, offset_y))
                if len(vertices) < 3:
                    continue
                path_mask = Image.new("1", (width, height), 0)
                ImageDraw.Draw(path_mask).polygon(vertices, fill=1)
                if fill.fill_rule == "even_odd":
                    region = ImageChops.logical_xor(region, path_mask)
                else:
                    region = ImageChops.lighter(region, path_mask)
            combined = intensity_region(intensity)
            intensity_regions[intensity] = ImageChops.lighter(combined, region)

    for intensity, region in intensity_regions.items():
        shade = int(round(255 * (1.0 - intensity)))
        layer = Image.new("L", (width, height), 255)
        layer.paste(shade, mask=region)
        output = ImageChops.darker(output, layer)
    return output
