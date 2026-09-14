"""Adaptadores temporários entre o modelo canônico e estruturas legadas."""

from .model import JobDocument, LineSegment, Operation


def vector_lines_in_inches(document: JobDocument, operation: Operation) -> list[list[float]]:
    """Retorna linhas no formato [x0, y0, x1, y1] esperado por ECoord."""
    lines = []
    for vector in document.vectors:
        if vector.operation is not operation:
            continue
        for path in vector.paths:
            for segment in path.segments:
                if not isinstance(segment, LineSegment):
                    raise TypeError("O adaptador legado requer segmentos previamente achatados.")
                start = vector.transform.apply(segment.start)
                end = vector.transform.apply(segment.end)
                lines.append([start.x / 25.4, start.y / 25.4, end.x / 25.4, end.y / 25.4])
    return lines
