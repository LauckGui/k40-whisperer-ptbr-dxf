"""Adaptive conversion of analytic geometry to line segments.

The tolerance is the maximum geometric deviation in millimeters, not a fixed
angular step or a fixed number of segments. This keeps smooth curves compact
while refining only where their curvature requires it.
"""

from __future__ import annotations

import math

from .model import ArcSegment, CubicBezierSegment, LineSegment, Point, VectorSegment


def _midpoint(first: Point, second: Point) -> Point:
    return Point((first.x+second.x)/2.0, (first.y+second.y)/2.0)


def _point_line_distance(point: Point, start: Point, end: Point) -> float:
    dx, dy = end.x-start.x, end.y-start.y
    length = math.hypot(dx, dy)
    if length == 0.0:
        return math.hypot(point.x-start.x, point.y-start.y)
    return abs(dy*point.x-dx*point.y+end.x*start.y-end.y*start.x) / length


def _flatten_cubic(segment: CubicBezierSegment, tolerance_mm: float) -> list[Point]:
    points = [segment.start]
    pending = [(segment.start, segment.control1, segment.control2, segment.end, 0)]
    while pending:
        start, control1, control2, end, depth = pending.pop()
        # Distance of both controls to the chord is a conservative flatness
        # bound and remains safe for S-shaped curves where midpoint-only tests
        # can incorrectly report zero error.
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


def _flatten_arc(segment: ArcSegment, tolerance_mm: float) -> list[Point]:
    radius = math.hypot(segment.start.x-segment.center.x,
                        segment.start.y-segment.center.y)
    if radius == 0.0:
        return [segment.start, segment.end]
    start_angle = math.atan2(segment.start.y-segment.center.y,
                             segment.start.x-segment.center.x)
    end_angle = math.atan2(segment.end.y-segment.center.y,
                           segment.end.x-segment.center.x)
    sweep = end_angle-start_angle
    if segment.clockwise:
        if sweep >= 0.0:
            sweep -= 2.0*math.pi
    elif sweep <= 0.0:
        sweep += 2.0*math.pi

    # Sagitta = r * (1-cos(theta/2)). Solving it for theta gives the
    # longest safe chord for this radius and requested maximum deviation.
    safe_tolerance = min(tolerance_mm, radius*2.0)
    max_angle = 2.0*math.acos(max(-1.0, 1.0-safe_tolerance/radius))
    count = max(1, int(math.ceil(abs(sweep)/max(max_angle, 1e-12))))
    points = [
        Point(segment.center.x+radius*math.cos(start_angle+sweep*index/count),
              segment.center.y+radius*math.sin(start_angle+sweep*index/count))
        for index in range(count+1)
    ]
    points[0] = segment.start
    points[-1] = segment.end
    return points


def adaptive_segment_points(segment: VectorSegment,
                            tolerance_mm: float = 0.0127) -> list[Point]:
    """Return ordered vertices whose chord deviation stays within tolerance."""
    if not math.isfinite(tolerance_mm) or tolerance_mm <= 0.0:
        raise ValueError("A tolerância de discretização precisa ser positiva.")
    if isinstance(segment, LineSegment):
        return [segment.start, segment.end]
    if isinstance(segment, CubicBezierSegment):
        return _flatten_cubic(segment, tolerance_mm)
    if isinstance(segment, ArcSegment):
        return _flatten_arc(segment, tolerance_mm)
    raise TypeError("Tipo de segmento vetorial não suportado para discretização.")


def adaptive_line_segments(segment: VectorSegment,
                           tolerance_mm: float = 0.0127) -> tuple[LineSegment, ...]:
    """Return adaptive chords while retaining exact source endpoints."""
    points = adaptive_segment_points(segment, tolerance_mm)
    return tuple(LineSegment(start, end) for start, end in zip(points, points[1:])
                 if start != end)
