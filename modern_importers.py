"""Adaptadores modernos de geometria para o K40 Whisperer.

Todos os vetores retornam segmentos [x0, y0, x1, y1] em polegadas.
Azul é gravação; as demais cores são corte, preservando a convenção atual.
"""

from dataclasses import dataclass, field
import math
import os
import subprocess
import tempfile

from k40core.importers.dxf import DxfImportError, import_dxf_document, probe_dxf_units as _probe_dxf_units
from k40core.legacy import vector_lines_in_inches
from k40core.model import Operation


class ModernImporterFallback(Exception):
    """Indica que o leitor legado deve ser usado sem interromper a abertura."""


@dataclass
class ImportResult:
    cut: list = field(default_factory=list)
    engrave: list = field(default_factory=list)
    bounds: tuple = (0.0, 0.0, 0.0, 0.0)
    warnings: list = field(default_factory=list)
    importer: str = ""
    document: object = None


def _is_blue(color):
    if color is None:
        return False
    text = str(color).lower().strip()
    named = {"blue", "#00f", "#0000ff", "#0000ffff", "rgb(0,0,255)"}
    if text in named:
        return True
    if text.startswith("#") and len(text) >= 7:
        try:
            red, green, blue = int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16)
            return blue >= 128 and blue > red * 1.35 and blue > green * 1.2
        except ValueError:
            pass
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        red, green, blue = color[:3]
        return blue >= 128 and blue > red * 1.35 and blue > green * 1.2
    return False


def _append_polyline(points, target, scale=1.0):
    previous = None
    for point in points:
        current = (float(point[0]) * scale, float(point[1]) * scale)
        if previous is not None and current != previous:
            target.append([previous[0], previous[1], current[0], current[1]])
        previous = current


def _bounds(cut, engrave):
    lines = cut + engrave
    if not lines:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [value for line in lines for value in (line[0], line[2])]
    ys = [value for line in lines for value in (line[1], line[3])]
    return (min(xs), max(xs), min(ys), max(ys))


def probe_dxf_units(filename):
    return _probe_dxf_units(filename)


def import_dxf(filename, tolerance_inches=0.0005, assumed_units=None):
    document = import_dxf_document(
        filename,
        tolerance_mm=tolerance_inches * 25.4,
        assumed_units=assumed_units,
    )

    result = ImportResult(
        cut=vector_lines_in_inches(document, Operation.VECTOR_CUT),
        engrave=vector_lines_in_inches(document, Operation.VECTOR_ENGRAVE),
        warnings=[issue.message for issue in document.issues],
        importer=document.source.importer,
        document=document,
    )
    if not result.cut and not result.engrave:
        raise DxfImportError("O DXF não contém geometria visível para corte ou gravação.")
    result.bounds = _bounds(result.cut, result.engrave)
    return result


def _distance_to_chord(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    if dx == 0.0 and dy == 0.0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    return abs(dy * point[0] - dx * point[1] + end[0] * start[1] - end[1] * start[0]) / math.hypot(dx, dy)


def _adaptive_curve_points(point_at, start_t, end_t, tolerance, depth=0):
    start = point_at(start_t)
    end = point_at(end_t)
    middle_t = (start_t + end_t) / 2.0
    middle = point_at(middle_t)
    if depth >= 16 or _distance_to_chord(middle, start, end) <= tolerance:
        return [start, end]
    left = _adaptive_curve_points(point_at, start_t, middle_t, tolerance, depth + 1)
    right = _adaptive_curve_points(point_at, middle_t, end_t, tolerance, depth + 1)
    return left[:-1] + right


def import_3dm(filename, tolerance_inches=0.0005):
    import rhino3dm

    model = rhino3dm.File3dm.Read(filename)
    if model is None:
        raise ValueError("O arquivo 3DM não pôde ser lido.")
    source_units = model.Settings.ModelUnitSystem
    to_inches = rhino3dm.UnitSystem.UnitScale(source_units, rhino3dm.UnitSystem.Inches)
    tolerance_source = tolerance_inches / to_inches
    result = ImportResult(importer="rhino3dm")
    skipped = set()

    def add_curve(curve, target):
        try:
            ok, polyline = curve.TryGetPolyline()
        except TypeError:
            ok, polyline = False, None
        if ok:
            _append_polyline(((p.X, p.Y) for p in polyline), target, to_inches)
            return
        domain = curve.Domain
        points = _adaptive_curve_points(
            lambda t: (curve.PointAt(t).X, curve.PointAt(t).Y),
            domain.T0, domain.T1, tolerance_source,
        )
        _append_polyline(points, target, to_inches)

    for item in model.Objects:
        geometry = item.Geometry
        try:
            color = item.Attributes.DrawColor(model)
        except Exception:
            color = item.Attributes.ObjectColor
        target = result.engrave if _is_blue(color) else result.cut
        if isinstance(geometry, rhino3dm.Curve):
            add_curve(geometry, target)
        elif isinstance(geometry, rhino3dm.Brep):
            for edge in geometry.Edges:
                add_curve(edge, target)
        else:
            skipped.add(type(geometry).__name__)

    if skipped:
        result.warnings.append("Objetos 3DM não convertidos: " + ", ".join(sorted(skipped)))
    if not result.cut and not result.engrave:
        raise ValueError("O arquivo 3DM não contém curvas 2D utilizáveis.")
    result.bounds = _bounds(result.cut, result.engrave)
    return result


def import_svg(filename, tolerance_inches=0.0005):
    from svgelements import SVG, Shape

    drawing = SVG.parse(filename, reify=True, ppi=96.0)
    unsupported = {"Image", "Text"}
    present = {type(element).__name__ for element in drawing.elements()}
    if present & unsupported:
        raise ModernImporterFallback("O SVG contém texto ou imagem; usando o leitor compatível.")

    result = ImportResult(importer="svgelements")
    tolerance_px = tolerance_inches * 96.0
    for element in drawing.elements():
        if not isinstance(element, Shape):
            continue
        try:
            path = element.as_path()
        except AttributeError:
            try:
                from svgelements import Path
                path = Path(element)
            except Exception:
                continue
        target = result.engrave if _is_blue(getattr(element, "stroke", None)) else result.cut
        for segment in path:
            if type(segment).__name__ in {"Move", "Close"}:
                continue
            try:
                points = _adaptive_curve_points(
                    lambda t, s=segment: (s.point(t).x, s.point(t).y), 0.0, 1.0, tolerance_px
                )
                _append_polyline(points, target, 1.0 / 96.0)
            except Exception:
                raise ModernImporterFallback("Uma curva SVG não pôde ser convertida com segurança.")

    if not result.cut and not result.engrave:
        raise ModernImporterFallback("O SVG não contém vetores compatíveis com o leitor moderno.")
    result.bounds = _bounds(result.cut, result.engrave)
    return result


def find_dwg_converter(project_dir):
    candidates = [
        os.path.join(project_dir, "tools", "libredwg", "dwg2dxf.exe"),
        "dwg2dxf.exe",
        "dwg2dxf",
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
        from shutil import which
        resolved = which(candidate)
        if resolved:
            return resolved
    return None


def import_dwg(filename, project_dir, tolerance_inches=0.0005, assumed_units=None):
    converter = find_dwg_converter(project_dir)
    if converter is None:
        raise RuntimeError("O conversor LibreDWG não está instalado.")
    with tempfile.TemporaryDirectory(prefix="k40_dwg_") as temp_dir:
        output = os.path.join(temp_dir, os.path.splitext(os.path.basename(filename))[0] + ".dxf")
        process = subprocess.run(
            [converter, "--as", "r2018", "-y", "-o", output, filename],
            cwd=temp_dir, capture_output=True, text=True, errors="replace", timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if process.returncode != 0 or not os.path.isfile(output):
            detail = (process.stderr or process.stdout).strip()
            raise RuntimeError("O LibreDWG não conseguiu converter o arquivo. " + detail)
        result = import_dxf(output, tolerance_inches, assumed_units)
        result.importer = "LibreDWG + ezdxf"
        return result
