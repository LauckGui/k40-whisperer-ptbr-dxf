"""Non-destructive transforms for the canonical job model.

The UI intentionally exposes only similarity transforms (uniform scale,
rotation and reflection).  This keeps circles/arcs analytic and makes the
same operation safe for vectors, fills and future raster objects.
"""

from __future__ import annotations

from dataclasses import replace
import math

from .model import AffineTransform, Bounds, JobDocument, Point


def compose(after: AffineTransform, before: AffineTransform) -> AffineTransform:
    """Return ``after(before(point))`` in SVG affine-matrix form."""
    return AffineTransform(
        a=after.a*before.a + after.c*before.b,
        b=after.b*before.a + after.d*before.b,
        c=after.a*before.c + after.c*before.d,
        d=after.b*before.c + after.d*before.d,
        e=after.a*before.e + after.c*before.f + after.e,
        f=after.b*before.e + after.d*before.f + after.f,
    )


def around(point: Point, transform: AffineTransform) -> AffineTransform:
    """Move the transform pivot from the origin to ``point``."""
    return compose(
        AffineTransform(e=point.x, f=point.y),
        compose(transform, AffineTransform(e=-point.x, f=-point.y)),
    )


def uniform_scale(scale: float, pivot: Point) -> AffineTransform:
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("A escala precisa ser um número positivo.")
    return around(pivot, AffineTransform(a=scale, d=scale))


def rotation(degrees: float, pivot: Point) -> AffineTransform:
    if not math.isfinite(degrees):
        raise ValueError("O ângulo precisa ser um número válido.")
    radians = math.radians(degrees)
    cosine, sine = math.cos(radians), math.sin(radians)
    return around(pivot, AffineTransform(a=cosine, b=sine, c=-sine, d=cosine))


def reflection(horizontal: bool, pivot: Point) -> AffineTransform:
    """Reflect across the vertical (horizontal=True) or horizontal axis."""
    return around(
        pivot,
        AffineTransform(a=-1.0 if horizontal else 1.0,
                        d=1.0 if horizontal else -1.0),
    )


def editable_bounds(document: JobDocument) -> Bounds | None:
    """Bounds of the source design, excluding procedural array repetitions."""
    return Bounds.union(
        item.bounds for item in [*document.vectors, *document.rasters, *document.fills]
    )


def apply_document_transform(document: JobDocument, transform: AffineTransform) -> None:
    """Apply ``transform`` after every object transform without changing paths.

    Arrays continue to reference the same object IDs, so their setup remains
    procedural and automatically uses the transformed source bounds.
    """
    document.vectors[:] = [
        replace(item, transform=compose(transform, item.transform))
        for item in document.vectors
    ]
    document.rasters[:] = [
        replace(item, transform=compose(transform, item.transform))
        for item in document.rasters
    ]
    document.fills[:] = [
        replace(item, transform=compose(transform, item.transform))
        for item in document.fills
    ]
    document.arrays[:] = [
        replace(
            item,
            reference_bounds=(
                Bounds.from_points(transform.apply(point) for point in (
                    Point(item.reference_bounds.min_x, item.reference_bounds.min_y),
                    Point(item.reference_bounds.min_x, item.reference_bounds.max_y),
                    Point(item.reference_bounds.max_x, item.reference_bounds.min_y),
                    Point(item.reference_bounds.max_x, item.reference_bounds.max_y),
                )) if item.reference_bounds is not None else None
            ),
        )
        for item in document.arrays
    ]
    document.validate()
