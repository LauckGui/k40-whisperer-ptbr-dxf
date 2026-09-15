"""Topology reconstruction for exploded linework."""

from __future__ import annotations

from collections import defaultdict, deque
import math

from .model import LineSegment, VectorPath


def stitch_line_segments(segments, tolerance_mm=0.0127):
    """Join endpoint-connected lines into reversible open or closed paths.

    The spatial hash keeps lookup near-linear. At ambiguous branches the
    nearest unused endpoint is selected; source geometry is never modified.
    """
    segments = tuple(segments)
    if not segments:
        return []
    if tolerance_mm <= 0:
        raise ValueError("A tolerância topológica precisa ser positiva.")

    def cell(point):
        return (math.floor(point.x / tolerance_mm), math.floor(point.y / tolerance_mm))

    endpoint_index = defaultdict(list)
    for index, segment in enumerate(segments):
        endpoint_index[cell(segment.start)].append((index, True))
        endpoint_index[cell(segment.end)].append((index, False))
    unused = set(range(len(segments)))

    def nearest(point):
        cx, cy = cell(point)
        matches = []
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                for index, at_start in endpoint_index.get((cx+ox, cy+oy), ()):
                    if index not in unused:
                        continue
                    endpoint = segments[index].start if at_start else segments[index].end
                    distance = math.hypot(endpoint.x-point.x, endpoint.y-point.y)
                    if distance <= tolerance_mm:
                        matches.append((distance, index, at_start))
        return min(matches, default=None)

    paths = []
    seed_index = 0
    while unused:
        while seed_index not in unused:
            seed_index += 1
        first_index = seed_index
        unused.remove(first_index)
        first = segments[first_index]
        ordered = deque([first])

        while True:
            match = nearest(ordered[-1].end)
            if match is None:
                break
            _, index, at_start = match
            unused.remove(index)
            segment = segments[index]
            ordered.append(segment if at_start else LineSegment(segment.end, segment.start))

        while True:
            match = nearest(ordered[0].start)
            if match is None:
                break
            _, index, at_start = match
            unused.remove(index)
            segment = segments[index]
            ordered.appendleft(LineSegment(segment.end, segment.start) if at_start else segment)

        closed = math.hypot(
            ordered[0].start.x-ordered[-1].end.x,
            ordered[0].start.y-ordered[-1].end.y,
        ) <= tolerance_mm
        paths.append(VectorPath(tuple(ordered), closed=closed))
    return paths
