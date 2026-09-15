"""Adaptadores temporários entre o modelo canônico e estruturas legadas."""

import math

from .model import ArcSegment, CubicBezierSegment, JobDocument, LineSegment, Operation, Point
from .topology import stitch_line_segments, transform_segment


def _midpoint(first, second):
    return Point((first.x+second.x)/2.0, (first.y+second.y)/2.0)


def _point_line_distance(point, start, end):
    dx, dy = end.x-start.x, end.y-start.y
    length = math.hypot(dx, dy)
    if length == 0.0:
        return math.hypot(point.x-start.x, point.y-start.y)
    return abs(dy*point.x-dx*point.y+end.x*start.y-end.y*start.x) / length


def _flatten_cubic(segment, tolerance_mm):
    """Iteratively flatten a cubic Bézier, yielding its ordered vertices."""
    points = [segment.start]
    pending = [(segment.start, segment.control1, segment.control2, segment.end, 0)]
    while pending:
        start, control1, control2, end, depth = pending.pop()
        flatness = max(
            _point_line_distance(control1, start, end),
            _point_line_distance(control2, start, end),
        )
        if flatness <= tolerance_mm or depth >= 18:
            points.append(end)
            continue
        p01 = _midpoint(start, control1)
        p12 = _midpoint(control1, control2)
        p23 = _midpoint(control2, end)
        p012 = _midpoint(p01, p12)
        p123 = _midpoint(p12, p23)
        middle = _midpoint(p012, p123)
        pending.append((middle, p123, p23, end, depth+1))
        pending.append((start, p01, p012, middle, depth+1))
    return points


def _flatten_arc(segment, tolerance_mm):
    radius = math.hypot(segment.start.x-segment.center.x, segment.start.y-segment.center.y)
    if radius == 0.0:
        return [segment.start, segment.end]
    start_angle = math.atan2(segment.start.y-segment.center.y, segment.start.x-segment.center.x)
    end_angle = math.atan2(segment.end.y-segment.center.y, segment.end.x-segment.center.x)
    sweep = end_angle-start_angle
    if segment.clockwise:
        if sweep >= 0.0:
            sweep -= 2.0*math.pi
    elif sweep <= 0.0:
        sweep += 2.0*math.pi
    safe_tolerance = min(max(tolerance_mm, 1e-9), radius*2.0)
    max_angle = 2.0*math.acos(max(-1.0, 1.0-safe_tolerance/radius))
    count = max(1, int(math.ceil(abs(sweep)/max(max_angle, 1e-9))))
    return [
        Point(segment.center.x+radius*math.cos(start_angle+sweep*index/count),
              segment.center.y+radius*math.sin(start_angle+sweep*index/count))
        for index in range(count+1)
    ]


def _segment_points(segment, tolerance_mm):
    if isinstance(segment, LineSegment):
        return [segment.start, segment.end]
    if isinstance(segment, CubicBezierSegment):
        return _flatten_cubic(segment, tolerance_mm)
    if isinstance(segment, ArcSegment):
        return _flatten_arc(segment, tolerance_mm)
    raise TypeError("Tipo de segmento vetorial não suportado pelo adaptador legado.")


def vector_lines_in_inches(document: JobDocument, operation: Operation,
                           tolerance_mm: float = 0.0127) -> list[list[float]]:
    """Retorna linhas no formato [x0, y0, x1, y1] esperado por ECoord."""
    lines = []
    visible_layers = {layer.id for layer in document.layers if layer.visible}
    grouped_segments = {}
    for vector in document.vectors:
        if vector.operation is not operation or not vector.style.visible or vector.layer_id not in visible_layers:
            continue
        already_composed = bool(vector.metadata.get("topology_composed"))
        key = (vector.layer_id, vector.style.stroke)
        target = grouped_segments.setdefault(key, [])
        for path in vector.paths:
            for segment in path.segments:
                transformed = transform_segment(segment, vector.transform)
                if already_composed:
                    points = _segment_points(transformed, tolerance_mm)
                    lines.extend([start.x/25.4, start.y/25.4, end.x/25.4, end.y/25.4]
                                 for start, end in zip(points, points[1:]))
                else:
                    target.append(transformed)

    for segments in grouped_segments.values():
        for path in stitch_line_segments(segments):
            for segment in path.segments:
                points = _segment_points(segment, tolerance_mm)
                lines.extend([start.x/25.4, start.y/25.4, end.x/25.4, end.y/25.4]
                             for start, end in zip(points, points[1:]))
    return lines
