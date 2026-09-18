"""Helpers for producing lightweight previews without changing job geometry."""

import math


def ruler_step(span, target_intervals=8):
    """Return a readable 1/2/5 ruler interval for a numeric span."""
    span = abs(float(span))
    if span == 0.0:
        return 1.0
    rough = span/max(1, int(target_intervals))
    magnitude = 10.0**math.floor(math.log10(rough))
    normalized = rough/magnitude
    if normalized <= 1.0:
        nice = 1.0
    elif normalized <= 2.0:
        nice = 2.0
    elif normalized <= 5.0:
        nice = 5.0
    else:
        nice = 10.0
    return nice*magnitude


def ruler_values(span, target_intervals=8):
    """Generate major ruler values including both zero and the exact limit."""
    span = max(0.0, float(span))
    step = ruler_step(span, target_intervals)
    values = [0.0]
    value = step
    while value < span-1e-9:
        values.append(value)
        value += step
    if span > 0.0 and abs(values[-1]-span) > 1e-9:
        values.append(span)
    return values


def rectangular_trace(bounds, gap=0.0, loop=1):
    """Return a closed rectangular head-preview path around job bounds."""
    xmin, xmax, ymin, ymax = bounds
    return [
        [xmin-gap, ymax+gap, loop],
        [xmax+gap, ymax+gap, loop],
        [xmax+gap, ymin-gap, loop],
        [xmin-gap, ymin-gap, loop],
        [xmin-gap, ymax+gap, loop],
    ]


def model_origin_canvas(x_left, y_top, x_right, plot_scale,
                        position_x, position_y, home_on_right=False):
    """Map the movable machine/model origin to preview canvas coordinates."""
    x = (x_right-position_x/plot_scale if home_on_right
         else x_left+position_x/plot_scale)
    return x, y_top-position_y/plot_scale


def array_outline_canvas(point_x, point_y, offset_x, offset_y, bounds,
                         area_left, area_top, plot_scale,
                         home_on_right=False):
    """Project a procedural-array outline point onto its preview canvas.

    Model Y grows upwards while Tk canvas Y grows downwards. Machines homed
    on the upper-right also display X from right to left, matching the main
    work-area preview and its ruler.
    """
    model_x = float(point_x) + float(offset_x)
    model_y = float(point_y) + float(offset_y)
    if home_on_right:
        canvas_x = area_left + (bounds.max_x-model_x)/plot_scale
    else:
        canvas_x = area_left + (model_x-bounds.min_x)/plot_scale
    canvas_y = area_top + (bounds.max_y-model_y)/plot_scale
    return canvas_x, canvas_y


def transparent_raster_preview(image, size, alpha=None):
    """Return a black RGBA overlay where white/off and masked pixels are transparent."""
    from PIL import Image, ImageOps, ImageChops

    grayscale = image.convert("L").resize(size, Image.LANCZOS)
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    opacity = ImageOps.invert(grayscale)
    if alpha is None and image.mode == "RGBA":
        alpha = image.getchannel("A")
    if alpha is not None:
        opacity = ImageChops.multiply(opacity, alpha.convert("L").resize(size, Image.LANCZOS))
    overlay.putalpha(opacity)
    return overlay


def iter_preview_polylines(ecoords, transform, minimum_pixels=0.5):
    """Yield continuous, screen-space polylines with subpixel filtering.

    Every source path remains a separate polyline. Its first and last points are
    always retained; only intermediate points closer than ``minimum_pixels`` to
    the last retained point may be omitted.
    """
    current_loop = None
    points = []
    last_retained = None
    pending_endpoint = None
    path_start = None
    farthest_point = None
    farthest_squared = -1.0
    minimum_squared = minimum_pixels * minimum_pixels

    def completed_path():
        result = list(points)
        if len(result) == 2 and farthest_point is not None:
            # A very small closed contour may end exactly at its start. Keep
            # its farthest vertex so it remains visible instead of vanishing.
            if farthest_point != tuple(result[-2:]):
                result.extend(farthest_point)
        if pending_endpoint is not None:
            if not result or tuple(result[-2:]) != pending_endpoint:
                result.extend(pending_endpoint)
        return tuple(result) if len(result) >= 4 else None

    for x, y, loop in ecoords:
        screen_x, screen_y = transform(x, y)
        if loop != current_loop:
            path = completed_path()
            if path is not None:
                yield path
            points = [screen_x, screen_y]
            current_loop = loop
            last_retained = (screen_x, screen_y)
            path_start = last_retained
            farthest_point = last_retained
            farthest_squared = 0.0
            pending_endpoint = None
            continue


        start_dx = screen_x - path_start[0]
        start_dy = screen_y - path_start[1]
        start_distance_squared = start_dx*start_dx + start_dy*start_dy
        if start_distance_squared > farthest_squared:
            farthest_squared = start_distance_squared
            farthest_point = (screen_x, screen_y)

        dx = screen_x - last_retained[0]
        dy = screen_y - last_retained[1]
        if dx*dx + dy*dy >= minimum_squared:
            points.extend((screen_x, screen_y))
            last_retained = (screen_x, screen_y)
            pending_endpoint = None
        else:
            pending_endpoint = (screen_x, screen_y)

    path = completed_path()
    if path is not None:
        yield path
