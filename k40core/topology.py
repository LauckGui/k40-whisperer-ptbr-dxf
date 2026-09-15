"""Topology reconstruction for exploded linework."""

from __future__ import annotations

from collections import defaultdict, deque
import math

from .model import (
    AffineTransform, ArcSegment, CubicBezierSegment, LineSegment, Point,
    SourceReference, VectorObject, VectorPath,
)


def reverse_segment(segment):
    """Reverse a canonical segment without losing its analytic geometry."""
    if isinstance(segment, LineSegment):
        return LineSegment(segment.end, segment.start)
    if isinstance(segment, CubicBezierSegment):
        return CubicBezierSegment(
            segment.end, segment.control2, segment.control1, segment.start
        )
    if isinstance(segment, ArcSegment):
        return ArcSegment(
            segment.end, segment.start, segment.center, not segment.clockwise
        )
    raise TypeError("Tipo de segmento vetorial não suportado.")


def transform_segment(segment, transform):
    """Apply an affine transform while retaining the segment type."""
    if isinstance(segment, LineSegment):
        return LineSegment(transform.apply(segment.start), transform.apply(segment.end))
    if isinstance(segment, CubicBezierSegment):
        return CubicBezierSegment(
            transform.apply(segment.start),
            transform.apply(segment.control1),
            transform.apply(segment.control2),
            transform.apply(segment.end),
        )
    if isinstance(segment, ArcSegment):
        # A circular arc stays circular only under a similarity transform.
        dot = transform.a*transform.c + transform.b*transform.d
        scale_x2 = transform.a*transform.a + transform.b*transform.b
        scale_y2 = transform.c*transform.c + transform.d*transform.d
        if not math.isclose(dot, 0.0, abs_tol=1e-12) or not math.isclose(
            scale_x2, scale_y2, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise ValueError("Uma transformação não uniforme converteria o arco em elipse.")
        determinant = transform.a*transform.d-transform.b*transform.c
        return ArcSegment(
            transform.apply(segment.start), transform.apply(segment.end),
            transform.apply(segment.center),
            segment.clockwise if determinant >= 0 else not segment.clockwise,
        )
    raise TypeError("Tipo de segmento vetorial não suportado.")


def _point_line_distance(point, start, end):
    dx, dy = end.x-start.x, end.y-start.y
    if dx == 0.0 and dy == 0.0:
        return math.hypot(point.x-start.x, point.y-start.y)
    return abs(dy*point.x-dx*point.y+end.x*start.y-end.y*start.x) / math.hypot(dx, dy)


def _rdp(points, tolerance):
    """Iterative Ramer-Douglas-Peucker, preserving both endpoints."""
    if len(points) <= 2:
        return list(points)
    keep = {0, len(points)-1}
    pending = [(0, len(points)-1)]
    while pending:
        start, end = pending.pop()
        farthest_index = None
        farthest_distance = tolerance
        for index in range(start+1, end):
            distance = _point_line_distance(points[index], points[start], points[end])
            if distance > farthest_distance:
                farthest_index = index
                farthest_distance = distance
        if farthest_index is not None:
            keep.add(farthest_index)
            pending.append((start, farthest_index))
            pending.append((farthest_index, end))
    return [points[index] for index in sorted(keep)]


def simplify_vector_path(path, tolerance_mm=0.0127):
    """Simplify a line path without opening a closed contour."""
    if tolerance_mm <= 0 or len(path.segments) <= 1:
        return path
    if not all(isinstance(segment, LineSegment) for segment in path.segments):
        return path
    points = [path.segments[0].start]
    points.extend(segment.end for segment in path.segments)

    if path.closed and points[-1] == points[0]:
        ring = points[:-1]
        if len(ring) <= 3:
            return path
        first = min(range(len(ring)), key=lambda i: (ring[i].x, ring[i].y))
        farthest = max(
            range(len(ring)),
            key=lambda i: math.hypot(ring[i].x-ring[first].x, ring[i].y-ring[first].y),
        )
        if first > farthest:
            first, farthest = farthest, first
        left = _rdp(ring[first:farthest+1], tolerance_mm)
        right = _rdp(ring[farthest:] + ring[:first+1], tolerance_mm)
        simplified = left[:-1] + right
        if simplified[-1] != simplified[0]:
            simplified.append(simplified[0])
    else:
        simplified = _rdp(points, tolerance_mm)

    segments = tuple(
        LineSegment(start, end)
        for start, end in zip(simplified, simplified[1:])
        if start != end
    )
    return VectorPath(segments, closed=path.closed) if segments else path


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

    endpoint_index = defaultdict(set)
    for index, segment in enumerate(segments):
        endpoint_index[cell(segment.start)].add((index, True))
        endpoint_index[cell(segment.end)].add((index, False))
    unused = set(range(len(segments)))

    def consume(index):
        """Remove a segment and both stale endpoint-index entries."""
        unused.remove(index)
        segment = segments[index]
        for endpoint, at_start in ((segment.start, True), (segment.end, False)):
            bucket_cell = cell(endpoint)
            bucket = endpoint_index.get(bucket_cell)
            if bucket is None:
                continue
            bucket.discard((index, at_start))
            if not bucket:
                del endpoint_index[bucket_cell]

    def nearest(point):
        cx, cy = cell(point)
        matches = []
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                for index, at_start in endpoint_index.get((cx+ox, cy+oy), ()):
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
        consume(first_index)
        first = segments[first_index]
        ordered = deque([first])

        while True:
            match = nearest(ordered[-1].end)
            if match is None:
                break
            _, index, at_start = match
            consume(index)
            segment = segments[index]
            ordered.append(segment if at_start else reverse_segment(segment))

        while True:
            match = nearest(ordered[0].start)
            if match is None:
                break
            _, index, at_start = match
            consume(index)
            segment = segments[index]
            ordered.appendleft(reverse_segment(segment) if at_start else segment)

        closed = math.hypot(
            ordered[0].start.x-ordered[-1].end.x,
            ordered[0].start.y-ordered[-1].end.y,
        ) <= tolerance_mm
        paths.append(VectorPath(tuple(ordered), closed=closed))
    return paths


def compose_vector_objects(vectors, tolerance_mm=0.0127,
                           simplify_tolerance_mm=None):
    """Compose compatible objects into topology-aware multi-path objects."""
    source_container = vectors
    groups = {}
    for vector in vectors:
        key = (
            vector.layer_id, vector.operation, vector.style.stroke,
            vector.style.fill, vector.style.stroke_width_mm, vector.style.visible,
        )
        group = groups.setdefault(key, {"prototype": vector, "segments": [], "sources": []})
        group["sources"].append(vector.source)
        for path in vector.paths:
            for segment in path.segments:
                if vector.transform == AffineTransform():
                    group["segments"].append(segment)
                else:
                    group["segments"].append(transform_segment(segment, vector.transform))

    # Importers can hand over their mutable source list. Clearing it here drops
    # thousands of VectorObject/VectorPath containers before the spatial index
    # reaches its peak; segment objects remain referenced by their group.
    if isinstance(source_container, list):
        source_container.clear()

    composed = []
    simplification = tolerance_mm if simplify_tolerance_mm is None else simplify_tolerance_mm
    for group_index, group in enumerate(groups.values()):
        prototype = group["prototype"]
        paths = stitch_line_segments(group["segments"], tolerance_mm)
        paths = tuple(simplify_vector_path(path, simplification) for path in paths)
        source_ids = tuple(source.native_id for source in group["sources"]
                           if source.native_id is not None)
        single_source = len(group["sources"]) == 1
        composed.append(VectorObject(
            id=prototype.id if single_source else "composite:%d" % group_index,
            paths=paths,
            layer_id=prototype.layer_id,
            operation=prototype.operation,
            style=prototype.style,
            transform=AffineTransform(),
            source=prototype.source if single_source else SourceReference(
                entity_type="COMPOSITE",
                layer_name=prototype.source.layer_name,
                attributes={"native_ids": source_ids},
            ),
            metadata={
                "topology_composed": True,
                "source_object_count": len(group["sources"]),
                "source_segment_count": len(group["segments"]),
                "tolerance_mm": tolerance_mm,
                "simplify_tolerance_mm": simplification,
            },
        ))
    return composed
