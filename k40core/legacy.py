"""Adaptadores temporários entre o modelo canônico e estruturas legadas."""

from .model import AffineTransform, JobDocument, Operation
from .arrays import instance_offsets, referenced_bounds
from .tessellation import adaptive_segment_points
from .topology import stitch_line_segments, transform_segment


def vector_lines_in_inches(document: JobDocument, operation: Operation,
                           tolerance_mm: float = 0.0127,
                           include_arrays: bool = True) -> list[list[float]]:
    """Retorna linhas no formato [x0, y0, x1, y1] esperado por ECoord."""
    lines = []
    visible_layers = {layer.id for layer in document.layers if layer.visible}
    grouped_segments = {}
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
    for vector in document.vectors:
        if vector.operation is not operation or not vector.style.visible or vector.layer_id not in visible_layers:
            continue
        already_composed = bool(vector.metadata.get("topology_composed"))
        for offset_x, offset_y in offsets_by_object.get(vector.id, ((0.0, 0.0),)):
            key = (vector.layer_id, vector.style.stroke, offset_x, offset_y)
            target = grouped_segments.setdefault(key, [])
            for path in vector.paths:
                for segment in path.segments:
                    transformed = transform_segment(segment, vector.transform)
                    if offset_x != 0.0 or offset_y != 0.0:
                        transformed = transform_segment(
                            transformed, AffineTransform(e=offset_x, f=offset_y)
                        )
                    if already_composed:
                        points = adaptive_segment_points(transformed, tolerance_mm)
                        lines.extend([
                            start.x/25.4, start.y/25.4,
                            end.x/25.4, end.y/25.4,
                        ] for start, end in zip(points, points[1:]))
                    else:
                        target.append(transformed)

    for segments in grouped_segments.values():
        for path in stitch_line_segments(segments):
            for segment in path.segments:
                points = adaptive_segment_points(segment, tolerance_mm)
                lines.extend([start.x/25.4, start.y/25.4, end.x/25.4, end.y/25.4]
                             for start, end in zip(points, points[1:]))
    return lines
