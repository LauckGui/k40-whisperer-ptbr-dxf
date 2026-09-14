import unittest

from k40core.model import (
    AffineTransform,
    ImportSource,
    JobDocument,
    Layer,
    LineSegment,
    Operation,
    Point,
    RasterObject,
    SourceReference,
    Unit,
    VectorObject,
    VectorPath,
)


class JobModelTests(unittest.TestCase):
    def test_document_bounds_combine_vector_and_raster(self):
        layer = Layer("layer:0", "Principal")
        vector = VectorObject(
            id="vector:1",
            layer_id=layer.id,
            operation=Operation.VECTOR_CUT,
            paths=(VectorPath((LineSegment(Point(1, 2), Point(11, 7)),)),),
        )
        raster = RasterObject(
            id="raster:1",
            layer_id=layer.id,
            pixel_width=100,
            pixel_height=50,
            dpi_x=254,
            dpi_y=254,
            color_mode="L",
            mime_type="image/png",
            uri="image.png",
            transform=AffineTransform(e=20, f=30),
        )
        document = JobDocument(ImportSource("job.test", "test", "fixture"), [layer], [vector], [raster])

        document.validate()

        self.assertEqual((raster.physical_width_mm, raster.physical_height_mm), (10.0, 5.0))
        self.assertEqual(document.bounds, document.bounds.__class__(1, 2, 30, 35))

    def test_validation_rejects_unknown_layer(self):
        vector = VectorObject(
            id="vector:1",
            layer_id="missing",
            paths=(VectorPath((LineSegment(Point(0, 0), Point(1, 1)),)),),
        )
        document = JobDocument(ImportSource("job.test", "test", "fixture"), vectors=[vector])

        with self.assertRaisesRegex(ValueError, "camada inexistente"):
            document.validate()

    def test_operation_query_supports_vector_and_raster(self):
        layer = Layer("layer:0", "Principal")
        raster = RasterObject(
            "raster:1", layer.id, 1, 1, 96, 96, "RGBA", "image/png", data=b"x"
        )
        document = JobDocument(ImportSource("job.test", "test", "fixture"), [layer], rasters=[raster])

        self.assertEqual(document.objects_for_operation(Operation.RASTER_ENGRAVE), [raster])


if __name__ == "__main__":
    unittest.main()
