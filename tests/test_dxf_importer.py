import os
import tempfile
import unittest

import ezdxf

from k40core.importing import ImportCancelled
from k40core.importers.dxf import (
    DxfImportError,
    DxfProjectionRequired,
    _color_from_ezdxf,
    import_dxf_document,
)
from k40core.legacy import vector_lines_in_inches
from k40core.model import Operation, Unit
from modern_importers import import_dxf


class DxfImporterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _path(self, name="fixture.dxf"):
        return os.path.join(self.temp_dir.name, name)

    def test_import_preserves_layers_source_and_converts_to_millimeters(self):
        path = self._path()
        drawing = ezdxf.new("R2010", setup=True)
        drawing.units = ezdxf.units.IN
        drawing.layers.add("Corte")
        drawing.layers.add("Gravacao")
        modelspace = drawing.modelspace()
        cut = modelspace.add_line((0, 0), (1, 0), dxfattribs={"layer": "Corte", "color": 1})
        engrave = modelspace.add_line((0, 1), (1, 1), dxfattribs={"layer": "Gravacao", "color": 5})
        drawing.saveas(path)

        document = import_dxf_document(path)

        self.assertEqual(document.unit, Unit.MILLIMETER)
        self.assertEqual(document.source.source_unit, Unit.INCH)
        self.assertEqual({layer.name for layer in document.layers}, {"Corte", "Gravacao"})
        self.assertEqual(len(document.objects_for_operation(Operation.VECTOR_CUT)), 1)
        self.assertEqual(len(document.objects_for_operation(Operation.VECTOR_ENGRAVE)), 1)
        self.assertEqual(document.vectors[0].source.native_id, cut.dxf.handle)
        self.assertEqual(document.vectors[1].source.native_id, engrave.dxf.handle)
        self.assertAlmostEqual(document.bounds.max_x, 25.4)
        self.assertAlmostEqual(document.bounds.max_y, 25.4)

    def test_legacy_adapter_returns_inches_without_losing_operation(self):
        path = self._path()
        drawing = ezdxf.new("R2010", setup=True)
        drawing.units = ezdxf.units.MM
        drawing.modelspace().add_line((0, 0), (25.4, 0), dxfattribs={"color": 1})
        drawing.saveas(path)

        modern = import_dxf(path)

        self.assertIsNotNone(modern.document)
        self.assertEqual(modern.cut, [[0.0, 0.0, 1.0, 0.0]])
        self.assertEqual(modern.engrave, [])
        self.assertEqual(modern.bounds, (0.0, 1.0, 0.0, 0.0))

    def test_unitless_dxf_requires_explicit_assumption(self):
        path = self._path()
        drawing = ezdxf.new("R2010")
        drawing.units = 0
        drawing.modelspace().add_line((0, 0), (10, 0))
        drawing.saveas(path)

        with self.assertRaisesRegex(DxfImportError, "não informa"):
            import_dxf_document(path)

        document = import_dxf_document(path, assumed_units="Millimeters")
        self.assertAlmostEqual(document.bounds.max_x, 10.0)

    def test_unsupported_entities_generate_structured_issue(self):
        path = self._path()
        drawing = ezdxf.new("R2010")
        drawing.units = ezdxf.units.MM
        modelspace = drawing.modelspace()
        modelspace.add_line((0, 0), (1, 0))
        modelspace.add_point((2, 2))
        drawing.saveas(path)

        document = import_dxf_document(path)

        issue = next(item for item in document.issues if item.code == "dxf.entity_skipped")
        self.assertEqual(issue.source.entity_type, "POINT")
        self.assertEqual(issue.details["count"], 1)

    def test_circle_with_negative_extrusion_is_converted_from_ocs_to_wcs(self):
        path = self._path()
        drawing = ezdxf.new("R12")
        drawing.units = ezdxf.units.MM
        drawing.modelspace().add_circle(
            center=(-57.0, 5.0),
            radius=60.0,
            dxfattribs={"extrusion": (0.0, 0.0, -1.0)},
        )
        drawing.saveas(path)

        document = import_dxf_document(path, assumed_units="Millimeters")
        circle = next(item for item in document.vectors if item.source.entity_type == "CIRCLE")

        self.assertAlmostEqual((circle.bounds.min_x + circle.bounds.max_x) / 2.0, 57.0)
        self.assertAlmostEqual((circle.bounds.min_y + circle.bounds.max_y) / 2.0, 5.0)
        self.assertAlmostEqual(circle.bounds.width, 120.0, places=2)

    def test_non_planar_geometry_is_rejected(self):
        path = self._path()
        drawing = ezdxf.new("R2010")
        drawing.units = ezdxf.units.MM
        drawing.modelspace().add_line((0, 0, 0), (10, 10, 5))
        drawing.saveas(path)

        with self.assertRaisesRegex(DxfProjectionRequired, "geometria 3D"):
            import_dxf_document(path)

    def test_xz_drawing_is_detected_and_projected(self):
        path = self._path()
        drawing = ezdxf.new("R2010")
        drawing.units = ezdxf.units.MM
        drawing.modelspace().add_line((0, 7, 0), (10, 7, 5))
        drawing.saveas(path)

        document = import_dxf_document(path)

        self.assertEqual(document.source.metadata["projection_plane"], "XZ")
        self.assertEqual(document.bounds.min_x, 0.0)
        self.assertEqual(document.bounds.max_x, 10.0)
        self.assertEqual(document.bounds.min_y, 0.0)
        self.assertEqual(document.bounds.max_y, 5.0)
        self.assertEqual(document.issues[0].code, "dxf.geometry_projected")

    def test_non_planar_geometry_accepts_explicit_xy_projection(self):
        path = self._path()
        drawing = ezdxf.new("R2010")
        drawing.units = ezdxf.units.MM
        drawing.modelspace().add_line((0, 0, 0), (10, 10, 5))
        drawing.saveas(path)

        document = import_dxf_document(path, projection_plane="xy")

        self.assertEqual(document.source.metadata["projection_plane"], "XY")
        self.assertEqual(document.bounds.max_x, 10.0)
        self.assertEqual(document.bounds.max_y, 10.0)
        self.assertEqual(document.issues[0].code, "dxf.geometry_projected")

    def test_hidden_layer_is_preserved_but_not_sent_to_legacy_output(self):
        path = self._path()
        drawing = ezdxf.new("R2010", setup=True)
        drawing.units = ezdxf.units.MM
        hidden = drawing.layers.add("Oculta", color=1)
        hidden.off()
        drawing.modelspace().add_line((0, 0), (10, 0), dxfattribs={"layer": "Oculta"})
        drawing.saveas(path)

        document = import_dxf_document(path)

        self.assertFalse(document.layers[0].visible)
        self.assertFalse(document.vectors[0].style.visible)
        self.assertEqual(vector_lines_in_inches(document, Operation.VECTOR_CUT), [])

        with self.assertRaisesRegex(DxfImportError, "geometria visível"):
            import_dxf(path)

    def test_insert_inherits_layer_and_byblock_color(self):
        path = self._path()
        drawing = ezdxf.new("R2010", setup=True)
        drawing.units = ezdxf.units.MM
        drawing.layers.add("Gravacao", color=5)
        block = drawing.blocks.new("Peca")
        block.add_line((0, 0), (10, 0), dxfattribs={"layer": "0", "color": 0})
        drawing.modelspace().add_blockref(
            "Peca", (20, 30), dxfattribs={"layer": "Gravacao", "color": 256}
        )
        drawing.saveas(path)

        document = import_dxf_document(path)
        vector = document.vectors[0]

        self.assertEqual(document.layers[0].name, "Gravacao")
        self.assertEqual(vector.source.layer_name, "Gravacao")
        self.assertEqual(vector.operation, Operation.VECTOR_ENGRAVE)
        self.assertEqual(vector.style.stroke.hex_rgb, "#0000ff")

    def test_tuple_colors_are_supported(self):
        self.assertEqual(_color_from_ezdxf((0, 0, 255)).hex_rgb, "#0000ff")

    def test_true_color_takes_precedence_over_layer_color(self):
        path = self._path()
        drawing = ezdxf.new("R2010", setup=True)
        drawing.units = ezdxf.units.MM
        drawing.layers.add("Vermelha", color=1)
        drawing.modelspace().add_line(
            (0, 0), (10, 0),
            dxfattribs={"layer": "Vermelha", "color": 256, "true_color": 0x0000FF},
        )
        drawing.saveas(path)

        document = import_dxf_document(path)

        self.assertEqual(document.vectors[0].operation, Operation.VECTOR_ENGRAVE)
        self.assertEqual(document.vectors[0].style.stroke.hex_rgb, "#0000ff")

    def test_unit_resolver_and_progress_callbacks(self):
        path = self._path()
        drawing = ezdxf.new("R12")
        drawing.modelspace().add_line((0, 0), (10, 0))
        drawing.saveas(path)
        events = []

        document = import_dxf_document(
            path,
            unit_resolver=lambda: "Millimeters",
            progress=events.append,
        )

        self.assertEqual(document.bounds.max_x, 10.0)
        phases = [event.phase for event in events]
        self.assertIn("reading", phases)
        self.assertIn("analyzing", phases)
        conversion = next(event for event in events if event.phase == "converting" and event.total)
        self.assertEqual(conversion.completed, 0)
        self.assertEqual(conversion.total, 1)
        self.assertEqual(events[-1].phase, "complete")
        self.assertEqual(events[-1].completed, events[-1].total)

    def test_cooperative_cancellation_stops_before_conversion(self):
        path = self._path()
        drawing = ezdxf.new("R2010")
        drawing.units = ezdxf.units.MM
        drawing.modelspace().add_line((0, 0), (10, 0))
        drawing.saveas(path)
        state = {"cancelled": False}

        def progress(event):
            if event.phase == "analyzing":
                state["cancelled"] = True

        with self.assertRaises(ImportCancelled):
            import_dxf_document(
                path,
                progress=progress,
                cancelled=lambda: state["cancelled"],
            )

    def test_solid_is_imported_as_fill_instead_of_vector_edges(self):
        path = self._path()
        drawing = ezdxf.new("R2010")
        drawing.units = ezdxf.units.MM
        drawing.modelspace().add_solid([(0, 0), (10, 0), (0, 10), (10, 10)])
        drawing.saveas(path)

        document = import_dxf_document(path)

        self.assertEqual(document.vectors, [])
        self.assertEqual(len(document.fills), 1)
        self.assertEqual(document.fills[0].source.entity_type, "SOLID")
        self.assertEqual(document.fills[0].operation, Operation.RASTER_ENGRAVE)

    def test_hatch_with_hole_rasterizes_without_inkscape(self):
        path = self._path()
        drawing = ezdxf.new("R2010")
        drawing.units = ezdxf.units.MM
        hatch = drawing.modelspace().add_hatch(color=1)
        hatch.paths.add_polyline_path(
            [(0, 0), (10, 0), (10, 10), (0, 10)], is_closed=True,
        )
        hatch.paths.add_polyline_path(
            [(3, 3), (7, 3), (7, 7), (3, 7)], is_closed=True,
        )
        drawing.saveas(path)

        result = import_dxf(path, raster_dpi=254)

        self.assertEqual(len(result.document.fills), 1)
        self.assertIsNotNone(result.raster_image)
        self.assertEqual(result.raster_image.getpixel((10, 10)), 0)
        self.assertEqual(result.raster_image.getpixel((50, 50)), 255)


if __name__ == "__main__":
    unittest.main()
