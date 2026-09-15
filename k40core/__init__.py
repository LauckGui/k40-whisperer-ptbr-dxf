"""Núcleo independente de interface e hardware do K40 Whisperer."""

from .model import (
    AffineTransform,
    ArcSegment,
    Bounds,
    Color,
    CubicBezierSegment,
    FillObject,
    ImportIssue,
    ImportSource,
    InstanceArray,
    IssueSeverity,
    JobDocument,
    Layer,
    LineSegment,
    Operation,
    Point,
    RasterObject,
    SourceReference,
    Unit,
    VectorObject,
    VectorPath,
    VectorStyle,
)
from .rasterizer import RasterizationError, rasterize_fills
from .tessellation import adaptive_line_segments, adaptive_segment_points
from .topology import compose_vector_objects, simplify_vector_path, stitch_line_segments

__all__ = [name for name in globals() if not name.startswith("_")]
