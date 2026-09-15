"""Importação DXF baseada em ezdxf para o modelo canônico."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from k40core.importing import ImportCancelled, check_cancelled, report_progress

from k40core.model import (
    Color,
    FillObject,
    ImportIssue,
    ImportSource,
    IssueSeverity,
    JobDocument,
    Layer,
    LineSegment,
    Operation,
    Point,
    SourceReference,
    Unit,
    VectorObject,
    VectorPath,
    VectorStyle,
)


_FILL_ENTITY_TYPES = {"HATCH", "SOLID", "TRACE"}


def _flatten_entity_paths(entity, tolerance_source):
    """Return one or more WCS point sequences for paths or filled entities."""
    from ezdxf.path import from_hatch, make_path

    entity_type = entity.dxftype()
    if entity_type == "HATCH":
        return [tuple(path.flattening(distance=tolerance_source, segments=4))
                for path in from_hatch(entity)]
    if entity_type in {"SOLID", "TRACE"}:
        vertices = list(entity.wcs_vertices())
        if vertices and vertices[-1] != vertices[0]:
            vertices.append(vertices[0])
        return [tuple(vertices)]
    path = make_path(entity)
    return [tuple(path.flattening(distance=tolerance_source, segments=4))]


class DxfImportError(Exception):
    pass


class DxfProjectionRequired(DxfImportError):
    """Indica que o operador precisa escolher o plano de projeção."""


_ASSUMED_UNIT_CODES = {
    "inches": 1,
    "feet": 2,
    "miles": 3,
    "millimeters": 4,
    "centimeters": 5,
    "meters": 6,
    "kilometers": 7,
    "microinches": 8,
    "mils": 9,
}

_MODEL_UNITS = {
    1: Unit.INCH,
    2: Unit.FOOT,
    4: Unit.MILLIMETER,
    5: Unit.CENTIMETER,
    6: Unit.METER,
}


def _read_document(filename, progress=None, cancelled=None):
    import ezdxf
    from ezdxf import recover

    check_cancelled(cancelled)
    report_progress(progress, "reading", message="Lendo a estrutura do arquivo DXF...")
    try:
        document = ezdxf.readfile(filename)
        report_progress(progress, "reading", 1, 1, "Estrutura DXF carregada.")
        return document, []
    except ezdxf.DXFStructureError:
        document, auditor = recover.readfile(filename)
        report_progress(progress, "reading", 1, 1, "Estrutura DXF recuperada.")
        return document, [str(error) for error in auditor.errors]


def probe_dxf_units(filename):
    from ezdxf import units

    document, _ = _read_document(filename)
    return units.unit_name(document.units)


def _color_from_ezdxf(value) -> Color | None:
    if value is None:
        return None
    if isinstance(value, (tuple, list)) and len(value) >= 3:
        return Color(*value[:3])
    text = str(value).strip().lstrip("#")
    if len(text) >= 6:
        try:
            return Color(int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
        except ValueError:
            pass
    return None


def _is_engraving_blue(color: Color | None) -> bool:
    return color is not None and color.blue >= 128 and color.blue > color.red * 1.35 and color.blue > color.green * 1.2


def _source_insert(entity):
    return getattr(entity, "source_block_reference", None)


def _effective_layer_name(entity) -> str:
    layer_name = str(entity.dxf.get("layer", "0"))
    parent = _source_insert(entity)
    if layer_name == "0" and parent is not None:
        return _effective_layer_name(parent)
    return layer_name


def _layer_properties(document, context, layer_name):
    try:
        layer = document.layers.get(layer_name)
        return layer, context.resolve_layer_properties(layer)
    except Exception:
        return None, None


def _effective_color(entity, document, context, layer_name) -> Color | None:
    if entity.dxf.hasattr("true_color"):
        return _color_from_ezdxf(context.resolve_all(entity).color)
    raw_color = int(entity.dxf.get("color", 256))
    parent = _source_insert(entity)
    if raw_color == 0 and parent is not None:  # BYBLOCK
        return _effective_color(parent, document, context, _effective_layer_name(parent))
    if raw_color == 256:  # BYLAYER
        _, properties = _layer_properties(document, context, layer_name)
        return _color_from_ezdxf(properties.color) if properties is not None else None
    return _color_from_ezdxf(context.resolve_all(entity).color)


def _select_projection(coordinate_ranges, tolerance_source, requested):
    requested = str(requested).lower()
    if requested not in {"auto", "xy", "xz", "yz"}:
        raise ValueError("Plano de projeção deve ser auto, XY, XZ ou YZ.")
    ranges = coordinate_ranges
    if requested != "auto":
        return requested, ranges
    for plane, discarded_axis in (("xy", 2), ("xz", 1), ("yz", 0)):
        low, high = ranges[discarded_axis]
        if high - low <= tolerance_source:
            return plane, ranges
    raise DxfProjectionRequired(
        "A geometria 3D não está contida em um plano XY, XZ ou YZ. "
        "Escolha explicitamente um plano de projeção antes de importar."
    )


def _project_point(point, plane, to_mm):
    axes = {"xy": (0, 1), "xz": (0, 2), "yz": (1, 2)}[plane]
    return Point(float(point[axes[0]]) * to_mm, float(point[axes[1]]) * to_mm)


def import_dxf_document(
    filename,
    tolerance_mm=0.0127,
    assumed_units=None,
    projection_plane="auto",
    progress=None,
    cancelled=None,
    unit_resolver=None,
    projection_resolver=None,
    progress_batch=250,
) -> JobDocument:
    from ezdxf import units
    from ezdxf.addons.drawing.properties import RenderContext
    from ezdxf.disassemble import recursive_decompose

    document, audit_messages = _read_document(filename, progress, cancelled)
    unit_code = document.units
    if unit_code == 0 and assumed_units is None and unit_resolver is not None:
        check_cancelled(cancelled)
        assumed_units = unit_resolver()
        check_cancelled(cancelled)
        if not assumed_units:
            raise ImportCancelled("Importação cancelada durante a escolha de unidades.")
    if unit_code == 0 and assumed_units:
        unit_code = _ASSUMED_UNIT_CODES.get(str(assumed_units).lower(), 0)
    if unit_code == 0:
        raise DxfImportError("O DXF não informa a unidade de medida.")

    try:
        to_mm = units.conversion_factor(unit_code, units.MM)
    except (ValueError, TypeError) as exc:
        raise DxfImportError(f"Unidade DXF não suportada: {units.unit_name(unit_code) or unit_code}.") from exc

    source_unit_name = units.unit_name(unit_code) or str(unit_code)
    result = JobDocument(
        source=ImportSource(
            path=str(Path(filename).resolve()),
            format="dxf",
            importer="ezdxf",
            source_unit=_MODEL_UNITS.get(unit_code, Unit.UNITLESS),
            source_unit_name=source_unit_name,
            metadata={"dxf_version": document.dxfversion, "unit_code": unit_code},
        )
    )
    for message in audit_messages:
        result.issues.append(ImportIssue("dxf.recovered", message))

    context = RenderContext(document)
    layer_ids = {}
    skipped = Counter()
    tolerance_source = tolerance_mm / to_mm

    coordinate_ranges = [[float("inf"), float("-inf")] for _ in range(3)]
    analyzable = 0
    report_progress(progress, "analyzing", message="Analisando entidades e plano do desenho...")
    for index, entity in enumerate(recursive_decompose(document.modelspace())):
        check_cancelled(cancelled)
        entity_type = entity.dxftype()
        flattened_paths = None
        try:
            flattened_paths = _flatten_entity_paths(entity, tolerance_source)
            if not any(len(item) >= 2 for item in flattened_paths):
                continue
            analyzable += 1
            for flattened in flattened_paths:
                for point in flattened:
                    for axis in range(3):
                        value = float(point[axis])
                        coordinate_ranges[axis][0] = min(coordinate_ranges[axis][0], value)
                        coordinate_ranges[axis][1] = max(coordinate_ranges[axis][1], value)
        except (TypeError, ValueError, AttributeError, NotImplementedError):
            pass
        if index % progress_batch == 0:
            report_progress(progress, "analyzing", index, message=f"{index} entidades analisadas...")
        flattened_paths = None
        del entity

    if not analyzable:
        raise DxfImportError("O DXF não contém geometria vetorial utilizável.")
    ranges = tuple((item[0], item[1]) for item in coordinate_ranges)
    try:
        projection, ranges = _select_projection(ranges, tolerance_source, projection_plane)
    except DxfProjectionRequired:
        if projection_resolver is None:
            raise
        check_cancelled(cancelled)
        selected_projection = projection_resolver()
        check_cancelled(cancelled)
        if not selected_projection:
            raise ImportCancelled("Importação cancelada durante a escolha da projeção.")
        projection, ranges = _select_projection(ranges, tolerance_source, selected_projection)
    result.source.metadata["projection_plane"] = projection.upper()
    discarded_axis = {"xy": 2, "xz": 1, "yz": 0}[projection]
    discarded_low, discarded_high = ranges[discarded_axis]
    if projection != "xy" or abs(discarded_low) > tolerance_source or abs(discarded_high) > tolerance_source:
        result.issues.append(
            ImportIssue(
                code="dxf.geometry_projected",
                message="Geometria projetada automaticamente no plano %s." % projection.upper(),
                severity=IssueSeverity.WARNING,
                details={
                    "plane": projection.upper(),
                    "discarded_range": (discarded_low * to_mm, discarded_high * to_mm),
                },
            )
        )

    report_progress(progress, "converting", 0, analyzable, "Convertendo entidades DXF...")
    converted = 0
    for index, entity in enumerate(recursive_decompose(document.modelspace())):
        check_cancelled(cancelled)
        entity_type = entity.dxftype()
        flattened_paths = None
        points = None
        segments = None
        layer_name = _effective_layer_name(entity)
        layer_id = layer_ids.get(layer_name)
        if layer_id is None:
            layer_id = f"layer:{len(layer_ids)}"
            layer_ids[layer_name] = layer_id
            source_layer, layer_properties = _layer_properties(document, context, layer_name)
            result.layers.append(
                Layer(
                    layer_id,
                    layer_name,
                    visible=layer_properties.is_visible if layer_properties is not None else True,
                    locked=source_layer.is_locked() if source_layer is not None else False,
                    metadata={"source_format": "dxf"},
                )
            )

        original = getattr(entity, "source_of_copy", None) or entity
        handle = original.dxf.get("handle", None)
        reference = SourceReference(
            native_id=str(handle) if handle is not None else None,
            entity_type=entity_type,
            layer_name=layer_name,
        )
        try:
            flattened_paths = _flatten_entity_paths(entity, tolerance_source)
            flattened = flattened_paths[0] if flattened_paths else ()
            if entity_type in _FILL_ENTITY_TYPES:
                fill_paths = []
                for source_points in flattened_paths:
                    points = tuple(_project_point(point, projection, to_mm)
                                   for point in source_points)
                    segments = tuple(
                        LineSegment(start, end)
                        for start, end in zip(points, points[1:])
                        if start != end
                    )
                    if segments:
                        fill_paths.append(VectorPath(segments=segments, closed=True))
                if not fill_paths:
                    skipped[entity_type] += 1
                    continue
                color = _effective_color(entity, document, context, layer_name)
                object_id = f"dxf:{handle}:{index}" if handle is not None else f"dxf:index:{index}"
                result.fills.append(FillObject(
                    id=object_id,
                    paths=tuple(fill_paths),
                    layer_id=layer_id,
                    color=color,
                    fill_rule="even_odd" if entity_type == "HATCH" else "union",
                    source=reference,
                    metadata={
                        "source_entity": entity_type,
                        "solid_fill": bool(getattr(entity.dxf, "solid_fill", True)),
                        "pattern_name": getattr(entity.dxf, "pattern_name", None),
                        "flattening_tolerance_mm": tolerance_mm,
                    },
                ))
                converted += 1
                if index % progress_batch == 0:
                    report_progress(
                        progress, "converting", converted, analyzable,
                        message=f"{converted} de {analyzable} objetos convertidos...",
                    )
                flattened_paths = None
                del entity
                continue
            points = tuple(_project_point(point, projection, to_mm) for point in flattened)
            segments = tuple(LineSegment(start, end) for start, end in zip(points, points[1:]) if start != end)
            if not segments:
                skipped[entity_type] += 1
                continue
            properties = context.resolve_all(entity)
            color = _effective_color(entity, document, context, layer_name)
            _, effective_layer = _layer_properties(document, context, layer_name)
            visible = properties.is_visible and (effective_layer is None or effective_layer.is_visible)
            operation = Operation.VECTOR_ENGRAVE if _is_engraving_blue(color) else Operation.VECTOR_CUT
            object_id = f"dxf:{handle}:{index}" if handle is not None else f"dxf:index:{index}"
            result.vectors.append(
                VectorObject(
                    id=object_id,
                    paths=(VectorPath(segments=segments, closed=points[0] == points[-1]),),
                    layer_id=layer_id,
                    operation=operation,
                    style=VectorStyle(stroke=color, visible=visible),
                    source=reference,
                    metadata={"flattening_tolerance_mm": tolerance_mm},
                )
            )
            converted += 1
        except (TypeError, ValueError, AttributeError, NotImplementedError):
            skipped[entity_type] += 1
        if index % progress_batch == 0:
            report_progress(
                progress,
                "converting",
                converted,
                analyzable,
                message=f"{converted} de {analyzable} objetos convertidos...",
            )
        flattened_paths = None
        points = None
        segments = None
        del entity

    for entity_type, count in sorted(skipped.items()):
        result.issues.append(
            ImportIssue(
                code="dxf.entity_skipped",
                message=f"{count} entidade(s) {entity_type} não foram convertidas.",
                severity=IssueSeverity.WARNING,
                source=SourceReference(entity_type=entity_type),
                details={"count": count},
            )
        )
    if not result.vectors and not result.fills:
        raise DxfImportError("O DXF não contém geometria utilizável.")
    result.validate()
    report_progress(progress, "complete", analyzable, analyzable, f"{converted} objetos DXF convertidos.")
    return result
