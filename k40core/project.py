"""Versioned, self-contained K40 project archives."""

from __future__ import annotations

import base64
import json
import os
import tempfile
import zipfile
from enum import Enum

from .model import (
    AffineTransform, ArcSegment, Bounds, Color, CubicBezierSegment, FillObject,
    ImportIssue, ImportSource, InstanceArray, IssueSeverity, JobDocument, Layer,
    LineSegment, Operation, Point, RasterObject, SourceReference, Unit,
    VectorObject, VectorPath, VectorStyle,
)


SCHEMA_VERSION = 1
MANIFEST_NAME = "manifest.json"


class ProjectError(ValueError):
    pass


def _json_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        return {"$bytes": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    return str(value)


def _json_restore(value):
    if isinstance(value, list):
        return [_json_restore(item) for item in value]
    if isinstance(value, dict):
        if set(value) == {"$bytes"}:
            return base64.b64decode(value["$bytes"])
        return {key: _json_restore(item) for key, item in value.items()}
    return value


def _point(value):
    return [value.x, value.y]


def _read_point(value):
    return Point(float(value[0]), float(value[1]))


def _transform(value):
    return [value.a, value.b, value.c, value.d, value.e, value.f]


def _read_transform(value):
    return AffineTransform(*(float(item) for item in value))


def _color(value):
    return None if value is None else [value.red, value.green, value.blue, value.alpha]


def _read_color(value):
    return None if value is None else Color(*(int(item) for item in value))


def _reference(value):
    return {
        "native_id": value.native_id,
        "entity_type": value.entity_type,
        "layer_name": value.layer_name,
        "attributes": _json_value(value.attributes),
    }


def _read_reference(value):
    value = value or {}
    return SourceReference(
        native_id=value.get("native_id"),
        entity_type=value.get("entity_type"),
        layer_name=value.get("layer_name"),
        attributes=_json_restore(value.get("attributes", {})),
    )


def _segment(value):
    if isinstance(value, LineSegment):
        return {"type": "line", "start": _point(value.start), "end": _point(value.end)}
    if isinstance(value, ArcSegment):
        return {
            "type": "arc", "start": _point(value.start), "end": _point(value.end),
            "center": _point(value.center), "clockwise": value.clockwise,
        }
    if isinstance(value, CubicBezierSegment):
        return {
            "type": "cubic", "start": _point(value.start), "end": _point(value.end),
            "control1": _point(value.control1), "control2": _point(value.control2),
        }
    raise ProjectError("Tipo de segmento não suportado: %s" % type(value).__name__)


def _read_segment(value):
    kind = value.get("type")
    if kind == "line":
        return LineSegment(_read_point(value["start"]), _read_point(value["end"]))
    if kind == "arc":
        return ArcSegment(_read_point(value["start"]), _read_point(value["end"]),
                          _read_point(value["center"]), bool(value.get("clockwise")))
    if kind == "cubic":
        return CubicBezierSegment(
            _read_point(value["start"]), _read_point(value["control1"]),
            _read_point(value["control2"]), _read_point(value["end"]),
        )
    raise ProjectError("Segmento de projeto desconhecido: %r" % kind)


def _path(value):
    return {"closed": value.closed, "segments": [_segment(item) for item in value.segments]}


def _read_path(value):
    return VectorPath(tuple(_read_segment(item) for item in value["segments"]),
                      bool(value.get("closed")))


def document_to_dict(document):
    if document is None:
        return None
    return {
        "schema_version": document.schema_version,
        "unit": document.unit.value,
        "source": {
            "path": document.source.path, "format": document.source.format,
            "importer": document.source.importer,
            "source_unit": document.source.source_unit.value,
            "source_unit_name": document.source.source_unit_name,
            "metadata": _json_value(document.source.metadata),
        },
        "layers": [{
            "id": item.id, "name": item.name, "visible": item.visible,
            "locked": item.locked, "metadata": _json_value(item.metadata),
        } for item in document.layers],
        "vectors": [{
            "id": item.id, "layer_id": item.layer_id, "operation": item.operation.value,
            "paths": [_path(path) for path in item.paths],
            "style": {
                "stroke": _color(item.style.stroke), "fill": _color(item.style.fill),
                "stroke_width_mm": item.style.stroke_width_mm,
                "visible": item.style.visible,
                "metadata": _json_value(item.style.metadata),
            },
            "transform": _transform(item.transform), "source": _reference(item.source),
            "metadata": _json_value(item.metadata),
        } for item in document.vectors],
        "rasters": [{
            "id": item.id, "layer_id": item.layer_id,
            "pixel_width": item.pixel_width, "pixel_height": item.pixel_height,
            "dpi_x": item.dpi_x, "dpi_y": item.dpi_y,
            "color_mode": item.color_mode, "mime_type": item.mime_type,
            "uri": item.uri,
            "data": (base64.b64encode(item.data).decode("ascii") if item.data is not None else None),
            "operation": item.operation.value, "transform": _transform(item.transform),
            "source": _reference(item.source), "metadata": _json_value(item.metadata),
        } for item in document.rasters],
        "fills": [{
            "id": item.id, "layer_id": item.layer_id, "operation": item.operation.value,
            "paths": [_path(path) for path in item.paths], "color": _color(item.color),
            "intensity": item.intensity, "fill_rule": item.fill_rule,
            "transform": _transform(item.transform), "source": _reference(item.source),
            "metadata": _json_value(item.metadata),
        } for item in document.fills],
        "issues": [{
            "code": item.code, "message": item.message, "severity": item.severity.value,
            "source": _reference(item.source), "details": _json_value(item.details),
        } for item in document.issues],
        "arrays": [{
            "id": item.id, "object_ids": list(item.object_ids), "columns": item.columns,
            "rows": item.rows, "spacing_mm": item.spacing_mm, "mode": item.mode,
            "stagger_x_mm": item.stagger_x_mm, "row_adjust_y_mm": item.row_adjust_y_mm,
            "disabled_indices": list(item.disabled_indices),
            "execution_order": item.execution_order,
            "reference_bounds": ([item.reference_bounds.min_x, item.reference_bounds.min_y,
                                  item.reference_bounds.max_x, item.reference_bounds.max_y]
                                 if item.reference_bounds is not None else None),
        } for item in document.arrays],
        "metadata": _json_value(document.metadata),
    }


def document_from_dict(value):
    if value is None:
        return None
    source = value["source"]
    document = JobDocument(
        source=ImportSource(
            path=source["path"], format=source["format"], importer=source["importer"],
            source_unit=Unit(source.get("source_unit", "unitless")),
            source_unit_name=source.get("source_unit_name"),
            metadata=_json_restore(source.get("metadata", {})),
        ),
        layers=[Layer(
            item["id"], item["name"], bool(item.get("visible", True)),
            bool(item.get("locked", False)), _json_restore(item.get("metadata", {})),
        ) for item in value.get("layers", [])],
        vectors=[VectorObject(
            id=item["id"], paths=tuple(_read_path(path) for path in item["paths"]),
            layer_id=item["layer_id"], operation=Operation(item["operation"]),
            style=VectorStyle(
                stroke=_read_color(item["style"].get("stroke")),
                fill=_read_color(item["style"].get("fill")),
                stroke_width_mm=item["style"].get("stroke_width_mm"),
                visible=bool(item["style"].get("visible", True)),
                metadata=_json_restore(item["style"].get("metadata", {})),
            ),
            transform=_read_transform(item["transform"]),
            source=_read_reference(item.get("source")),
            metadata=_json_restore(item.get("metadata", {})),
        ) for item in value.get("vectors", [])],
        rasters=[RasterObject(
            id=item["id"], layer_id=item["layer_id"],
            pixel_width=int(item["pixel_width"]), pixel_height=int(item["pixel_height"]),
            dpi_x=float(item["dpi_x"]), dpi_y=float(item["dpi_y"]),
            color_mode=item["color_mode"], mime_type=item["mime_type"], uri=item.get("uri"),
            data=(base64.b64decode(item["data"]) if item.get("data") is not None else None),
            operation=Operation(item["operation"]), transform=_read_transform(item["transform"]),
            source=_read_reference(item.get("source")),
            metadata=_json_restore(item.get("metadata", {})),
        ) for item in value.get("rasters", [])],
        fills=[FillObject(
            id=item["id"], paths=tuple(_read_path(path) for path in item["paths"]),
            layer_id=item["layer_id"], operation=Operation(item["operation"]),
            color=_read_color(item.get("color")), intensity=float(item.get("intensity", 1.0)),
            fill_rule=item.get("fill_rule", "even_odd"),
            transform=_read_transform(item["transform"]),
            source=_read_reference(item.get("source")),
            metadata=_json_restore(item.get("metadata", {})),
        ) for item in value.get("fills", [])],
        issues=[ImportIssue(
            item["code"], item["message"], IssueSeverity(item.get("severity", "warning")),
            _read_reference(item.get("source")), _json_restore(item.get("details", {})),
        ) for item in value.get("issues", [])],
        arrays=[InstanceArray(
            id=item["id"], object_ids=tuple(item["object_ids"]),
            columns=int(item.get("columns", 1)), rows=int(item.get("rows", 1)),
            spacing_mm=float(item.get("spacing_mm", 0.0)), mode=item.get("mode", "grid"),
            stagger_x_mm=float(item.get("stagger_x_mm", 0.0)),
            row_adjust_y_mm=float(item.get("row_adjust_y_mm", 0.0)),
            disabled_indices=tuple(int(index)
                                   for index in item.get("disabled_indices", [])),
            execution_order=item.get("execution_order", "by_process"),
            reference_bounds=(Bounds(*map(float, item["reference_bounds"]))
                              if item.get("reference_bounds") is not None else None),
        ) for item in value.get("arrays", [])],
        metadata=_json_restore(value.get("metadata", {})),
        schema_version=int(value.get("schema_version", 1)),
        unit=Unit(value.get("unit", "mm")),
    )
    document.validate()
    return document


def save_project(path, document, state, assets=None):
    """Atomically write a compressed project archive."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".k40-project-", suffix=".tmp", dir=directory)
    os.close(descriptor)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "application": "K40 Whisperer PT-BR - DXF refatorado",
        "document": document_to_dict(document),
        "state": _json_value(state),
        "assets": sorted((assets or {}).keys()),
    }
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6) as archive:
            archive.writestr(MANIFEST_NAME, json.dumps(
                manifest, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8"))
            for name, data in (assets or {}).items():
                archive.writestr("assets/" + name, data)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def load_project(path):
    try:
        with zipfile.ZipFile(path, "r") as archive:
            manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
            if manifest.get("schema_version") != SCHEMA_VERSION:
                raise ProjectError("Versão de projeto não suportada.")
            assets = {}
            for name in manifest.get("assets", []):
                assets[name] = archive.read("assets/" + name)
    except (KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        raise ProjectError("Arquivo de projeto inválido.") from exc
    state = _json_restore(manifest.get("state", {}))
    if not isinstance(state, dict):
        raise ProjectError("Estado de projeto inválido.")
    return document_from_dict(manifest.get("document")), state, assets
