"""Helpers for producing lightweight previews without changing job geometry."""


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
