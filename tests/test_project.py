import os
import tempfile
import unittest

from k40core.model import (
    AffineTransform, ArcSegment, Bounds, Color, FillObject, ImportSource, InstanceArray,
    JobDocument, Layer, LineSegment, Operation, Point, RasterObject, Unit,
    VectorObject, VectorPath, VectorStyle,
)
from k40core.project import ProjectError, load_project, save_project


class ProjectArchiveTests(unittest.TestCase):
    def test_round_trip_preserves_analytic_geometry_arrays_state_and_assets(self):
        document = JobDocument(
            source=ImportSource("part.dxf", "dxf", "test", Unit.MILLIMETER),
            layers=[Layer("layer", "Cut")],
            vectors=[VectorObject(
                "vector", (VectorPath((ArcSegment(
                    Point(0, 0), Point(10, 0), Point(5, 0), clockwise=True
                ),), False),), "layer", Operation.VECTOR_CUT,
                VectorStyle(stroke=Color(255, 0, 0)),
            )],
            arrays=[InstanceArray("array", ("vector",), columns=3, rows=2,
                                  disabled_indices=(1, 4),
                                  execution_order="by_instance",
                                  reference_bounds=Bounds(-2, -3, 12, 8))],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "job.k40p")
            save_project(path, document, {"speed": "12", "coords": [[1, 2, 3]]},
                         {"raster.png": b"PNG"})
            restored, state, assets = load_project(path)
        self.assertIsInstance(restored.vectors[0].paths[0].segments[0], ArcSegment)
        self.assertEqual(restored.arrays[0].columns, 3)
        self.assertEqual(restored.arrays[0].disabled_indices, (1, 4))
        self.assertEqual(restored.arrays[0].execution_order, "by_instance")
        self.assertEqual(restored.arrays[0].reference_bounds, Bounds(-2, -3, 12, 8))
        self.assertEqual(state["coords"], [[1, 2, 3]])
        self.assertEqual(assets["raster.png"], b"PNG")

    def test_round_trip_preserves_fills_and_embedded_rasters(self):
        outline = VectorPath((LineSegment(Point(0, 0), Point(2, 0)),), False)
        document = JobDocument(
            source=ImportSource("image.svg", "svg", "test"),
            layers=[Layer("layer", "Raster")],
            fills=[FillObject("fill", (outline,), "layer", color=Color(0, 255, 0),
                              intensity=0.5)],
            rasters=[RasterObject(
                "raster", "layer", 2, 1, 254, 254, "L", "image/png",
                data=b"embedded", transform=AffineTransform(e=3, f=4),
            )],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "mixed.k40p")
            save_project(path, document, {}, {})
            restored, _, _ = load_project(path)
        self.assertEqual(restored.fills[0].intensity, 0.5)
        self.assertEqual(restored.rasters[0].data, b"embedded")
        self.assertEqual(restored.rasters[0].transform.e, 3)

    def test_invalid_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "invalid.k40p")
            with open(path, "wb") as stream:
                stream.write(b"not a project")
            with self.assertRaises(ProjectError):
                load_project(path)


if __name__ == "__main__":
    unittest.main()
