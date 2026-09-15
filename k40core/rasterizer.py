"""Rasterization of resolution-independent filled job objects."""

from __future__ import annotations

import math

from .model import Bounds, FillObject, JobDocument, LineSegment


class RasterizationError(ValueError):
    pass


def rasterize_fills(document: JobDocument, dpi: float, bounds: Bounds | None = None,
                    maximum_pixels: int = 100_000_000):
    """Render all raster-engrave fills to a monochrome Pillow image.

    White means laser off and black means laser on, matching the legacy raster
    pipeline. Geometry remains in the document and can be rendered again at a
    different DPI without reimporting.
    """
    from PIL import Image, ImageChops, ImageDraw

    visible_layers = {layer.id for layer in document.layers if layer.visible}
    fills = [item for item in document.fills
             if item.operation.value == "raster_engrave" and item.layer_id in visible_layers]
    if not fills:
        return None
    bounds = bounds or document.bounds
    if bounds is None or bounds.width <= 0 or bounds.height <= 0:
        raise RasterizationError("O preenchimento não possui uma área rasterizável.")
    if dpi <= 0:
        raise RasterizationError("O DPI precisa ser positivo.")

    width = max(1, int(math.ceil(bounds.width / 25.4 * dpi)))
    height = max(1, int(math.ceil(bounds.height / 25.4 * dpi)))
    if width * height > maximum_pixels:
        raise RasterizationError(
            "Raster exigiria %d megapixels; reduza a resolução." %
            int(math.ceil(width * height / 1_000_000.0))
        )

    output = Image.new("L", (width, height), 255)
    union_region = Image.new("1", (width, height), 0)
    union_draw = ImageDraw.Draw(union_region)

    def pixel(point, fill):
        transformed = fill.transform.apply(point)
        return (
            (transformed.x - bounds.min_x) / 25.4 * dpi,
            (bounds.max_y - transformed.y) / 25.4 * dpi,
        )

    for fill in fills:
        if fill.fill_rule == "union":
            for path in fill.paths:
                vertices = []
                for segment in path.segments:
                    if not isinstance(segment, LineSegment):
                        raise RasterizationError("Preenchimento precisa estar achatado antes da rasterização.")
                    if not vertices:
                        vertices.append(pixel(segment.start, fill))
                    vertices.append(pixel(segment.end, fill))
                if len(vertices) >= 3:
                    union_draw.polygon(vertices, fill=1)
            continue

        region = Image.new("1", (width, height), 0)
        for path in fill.paths:
            vertices = []
            for segment in path.segments:
                if not isinstance(segment, LineSegment):
                    raise RasterizationError("Preenchimento precisa estar achatado antes da rasterização.")
                if not vertices:
                    vertices.append(pixel(segment.start, fill))
                vertices.append(pixel(segment.end, fill))
            if len(vertices) < 3:
                continue
            path_mask = Image.new("1", (width, height), 0)
            ImageDraw.Draw(path_mask).polygon(vertices, fill=1)
            if fill.fill_rule == "even_odd":
                region = ImageChops.logical_xor(region, path_mask)
            else:
                region = ImageChops.lighter(region, path_mask)
        output.paste(0, mask=region)

    output.paste(0, mask=union_region)
    return output
