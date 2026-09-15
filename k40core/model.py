"""Modelo canônico de trabalhos.

O núcleo usa milímetros para toda geometria. Importadores devem guardar a
unidade e os identificadores originais em ``ImportSource``/``SourceReference``.
As classes não dependem de Tkinter, Pillow, ezdxf ou de uma controladora.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence, Union


class Unit(str, Enum):
    MILLIMETER = "mm"
    CENTIMETER = "cm"
    METER = "m"
    INCH = "in"
    FOOT = "ft"
    PIXEL = "px"
    UNITLESS = "unitless"

    @property
    def millimeters(self) -> Optional[float]:
        return {
            Unit.MILLIMETER: 1.0,
            Unit.CENTIMETER: 10.0,
            Unit.METER: 1000.0,
            Unit.INCH: 25.4,
            Unit.FOOT: 304.8,
        }.get(self)


class Operation(str, Enum):
    UNASSIGNED = "unassigned"
    VECTOR_CUT = "vector_cut"
    VECTOR_ENGRAVE = "vector_engrave"
    RASTER_ENGRAVE = "raster_engrave"
    SCORE = "score"


class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.x) or not math.isfinite(self.y):
            raise ValueError("Coordenadas devem ser finitas.")


@dataclass(frozen=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def __post_init__(self) -> None:
        values = (self.min_x, self.min_y, self.max_x, self.max_y)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Limites devem ser finitos.")
        if self.max_x < self.min_x or self.max_y < self.min_y:
            raise ValueError("Limites máximos não podem ser menores que os mínimos.")

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @classmethod
    def from_points(cls, points: Iterable[Point]) -> Optional["Bounds"]:
        materialized = tuple(points)
        if not materialized:
            return None
        return cls(
            min(point.x for point in materialized),
            min(point.y for point in materialized),
            max(point.x for point in materialized),
            max(point.y for point in materialized),
        )

    @classmethod
    def union(cls, bounds: Iterable[Optional["Bounds"]]) -> Optional["Bounds"]:
        present = tuple(item for item in bounds if item is not None)
        if not present:
            return None
        return cls(
            min(item.min_x for item in present),
            min(item.min_y for item in present),
            max(item.max_x for item in present),
            max(item.max_y for item in present),
        )


@dataclass(frozen=True)
class AffineTransform:
    """Transformação afim 2D no formato SVG: a, b, c, d, e, f."""

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0

    def apply(self, point: Point) -> Point:
        return Point(
            self.a * point.x + self.c * point.y + self.e,
            self.b * point.x + self.d * point.y + self.f,
        )


@dataclass(frozen=True)
class Color:
    red: int
    green: int
    blue: int
    alpha: int = 255

    def __post_init__(self) -> None:
        if not all(0 <= value <= 255 for value in (self.red, self.green, self.blue, self.alpha)):
            raise ValueError("Canais de cor devem estar entre 0 e 255.")

    @property
    def hex_rgb(self) -> str:
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"


@dataclass(frozen=True)
class LineSegment:
    start: Point
    end: Point

    @property
    def points(self) -> tuple[Point, ...]:
        return (self.start, self.end)


@dataclass(frozen=True)
class ArcSegment:
    start: Point
    end: Point
    center: Point
    clockwise: bool = False

    @property
    def points(self) -> tuple[Point, ...]:
        # Envelope conservador do círculo que contém o arco. Continua seguro
        # sob transformações afins, ainda que possa superestimar arcos parciais.
        radius = math.hypot(self.start.x - self.center.x, self.start.y - self.center.y)
        return (
            self.start,
            self.end,
            Point(self.center.x - radius, self.center.y - radius),
            Point(self.center.x - radius, self.center.y + radius),
            Point(self.center.x + radius, self.center.y - radius),
            Point(self.center.x + radius, self.center.y + radius),
        )


@dataclass(frozen=True)
class CubicBezierSegment:
    start: Point
    control1: Point
    control2: Point
    end: Point

    @property
    def points(self) -> tuple[Point, ...]:
        return (self.start, self.control1, self.control2, self.end)


VectorSegment = Union[LineSegment, ArcSegment, CubicBezierSegment]


@dataclass(frozen=True)
class VectorPath:
    segments: tuple[VectorSegment, ...]
    closed: bool = False

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("Um caminho vetorial precisa ter ao menos um segmento.")

    @property
    def bounds(self) -> Bounds:
        result = Bounds.from_points(point for segment in self.segments for point in segment.points)
        assert result is not None
        return result


@dataclass(frozen=True)
class VectorStyle:
    stroke: Optional[Color] = None
    fill: Optional[Color] = None
    stroke_width_mm: Optional[float] = None
    visible: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceReference:
    native_id: Optional[str] = None
    entity_type: Optional[str] = None
    layer_name: Optional[str] = None
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Layer:
    id: str
    name: str
    visible: bool = True
    locked: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorObject:
    id: str
    paths: tuple[VectorPath, ...]
    layer_id: str
    operation: Operation = Operation.UNASSIGNED
    style: VectorStyle = field(default_factory=VectorStyle)
    transform: AffineTransform = field(default_factory=AffineTransform)
    source: SourceReference = field(default_factory=SourceReference)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def bounds(self) -> Optional[Bounds]:
        transformed = []
        for path in self.paths:
            transformed.extend(self.transform.apply(point) for segment in path.segments for point in segment.points)
        return Bounds.from_points(transformed)


@dataclass(frozen=True)
class RasterObject:
    """Imagem posicionada fisicamente, sem dependência do decodificador.

    ``data`` pode conter o arquivo original para documentos autocontidos. Quando
    ausente, ``uri`` identifica a fonte. A transformação opera sobre um retângulo
    em milímetros calculado a partir de pixels e DPI.
    """

    id: str
    layer_id: str
    pixel_width: int
    pixel_height: int
    dpi_x: float
    dpi_y: float
    color_mode: str
    mime_type: str
    uri: Optional[str] = None
    data: Optional[bytes] = None
    operation: Operation = Operation.RASTER_ENGRAVE
    transform: AffineTransform = field(default_factory=AffineTransform)
    source: SourceReference = field(default_factory=SourceReference)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.pixel_width <= 0 or self.pixel_height <= 0:
            raise ValueError("Dimensões raster devem ser positivas.")
        if self.dpi_x <= 0 or self.dpi_y <= 0:
            raise ValueError("DPI deve ser positivo.")
        if self.uri is None and self.data is None:
            raise ValueError("Raster precisa de URI ou dados incorporados.")

    @property
    def physical_width_mm(self) -> float:
        return self.pixel_width / self.dpi_x * 25.4

    @property
    def physical_height_mm(self) -> float:
        return self.pixel_height / self.dpi_y * 25.4

    @property
    def bounds(self) -> Bounds:
        corners = (
            Point(0.0, 0.0),
            Point(self.physical_width_mm, 0.0),
            Point(0.0, self.physical_height_mm),
            Point(self.physical_width_mm, self.physical_height_mm),
        )
        result = Bounds.from_points(self.transform.apply(point) for point in corners)
        assert result is not None
        return result


@dataclass(frozen=True)
class FillObject:
    """Resolution-independent filled regions such as DXF HATCH/SOLID."""

    id: str
    paths: tuple[VectorPath, ...]
    layer_id: str
    operation: Operation = Operation.RASTER_ENGRAVE
    color: Optional[Color] = None
    fill_rule: str = "even_odd"
    transform: AffineTransform = field(default_factory=AffineTransform)
    source: SourceReference = field(default_factory=SourceReference)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.paths:
            raise ValueError("Um preenchimento precisa ter ao menos um contorno.")
        if self.fill_rule not in {"even_odd", "nonzero", "union"}:
            raise ValueError("Regra de preenchimento inválida.")

    @property
    def bounds(self) -> Optional[Bounds]:
        points = (
            self.transform.apply(point)
            for path in self.paths
            for segment in path.segments
            for point in segment.points
        )
        return Bounds.from_points(points)


@dataclass(frozen=True)
class ImportSource:
    path: str
    format: str
    importer: str
    source_unit: Unit = Unit.UNITLESS
    source_unit_name: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ImportIssue:
    code: str
    message: str
    severity: IssueSeverity = IssueSeverity.WARNING
    source: SourceReference = field(default_factory=SourceReference)
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class JobDocument:
    source: ImportSource
    layers: list[Layer] = field(default_factory=list)
    vectors: list[VectorObject] = field(default_factory=list)
    rasters: list[RasterObject] = field(default_factory=list)
    fills: list[FillObject] = field(default_factory=list)
    issues: list[ImportIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1
    unit: Unit = Unit.MILLIMETER

    @property
    def bounds(self) -> Optional[Bounds]:
        return Bounds.union(
            [item.bounds for item in self.vectors]
            + [item.bounds for item in self.rasters]
            + [item.bounds for item in self.fills]
        )

    def validate(self) -> None:
        if self.schema_version < 1:
            raise ValueError("Versão de schema inválida.")
        if self.unit is not Unit.MILLIMETER:
            raise ValueError("O modelo canônico deve usar milímetros.")
        layer_ids = [layer.id for layer in self.layers]
        if len(layer_ids) != len(set(layer_ids)):
            raise ValueError("IDs de camada duplicados.")
        object_ids = (
            [item.id for item in self.vectors]
            + [item.id for item in self.rasters]
            + [item.id for item in self.fills]
        )
        if len(object_ids) != len(set(object_ids)):
            raise ValueError("IDs de objeto duplicados.")
        known_layers = set(layer_ids)
        for item in [*self.vectors, *self.rasters, *self.fills]:
            if item.layer_id not in known_layers:
                raise ValueError(f"Objeto {item.id!r} referencia uma camada inexistente.")

    def objects_for_operation(self, operation: Operation) -> list[Union[VectorObject, RasterObject, FillObject]]:
        return [item for item in [*self.vectors, *self.rasters, *self.fills] if item.operation is operation]
