"""Adaptadores temporários entre o modelo canônico e estruturas legadas."""

from .model import JobDocument, LineSegment, Operation
from .topology import stitch_line_segments


def vector_lines_in_inches(document: JobDocument, operation: Operation) -> list[list[float]]:
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
                if not isinstance(segment, LineSegment):
                    raise TypeError("O adaptador legado requer segmentos previamente achatados.")
                start = vector.transform.apply(segment.start)
                end = vector.transform.apply(segment.end)
                if already_composed:
                    lines.append([start.x / 25.4, start.y / 25.4,
                                  end.x / 25.4, end.y / 25.4])
                else:
                    target.append(LineSegment(start, end))

    for segments in grouped_segments.values():
        for path in stitch_line_segments(segments):
            for segment in path.segments:
                start = segment.start
                end = segment.end
                lines.append([start.x / 25.4, start.y / 25.4, end.x / 25.4, end.y / 25.4])
    return lines
