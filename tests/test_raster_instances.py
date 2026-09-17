import unittest

from PIL import Image, ImageDraw

from k40core.model import (
    Bounds, ImportSource, InstanceArray, JobDocument, Layer, LineSegment,
    Operation, Point, Unit, VectorObject, VectorPath,
)
from k40core.raster_instances import (
    preview_bitmap_offsets, raster_content_bounds, raster_instance_offsets,
    repeat_scanlines,
)
from k40core.raster_paths import RasterScanlines


class RasterInstanceTests(unittest.TestCase):
    def _document(self):
        vector = VectorObject(
            "piece", (VectorPath((LineSegment(Point(0, 0), Point(10, 5)),)),),
            "layer", Operation.VECTOR_CUT,
        )
        return JobDocument(
            ImportSource("part.dxf", "dxf", "test", Unit.MILLIMETER),
            layers=[Layer("layer", "Layer")], vectors=[vector],
            arrays=[InstanceArray("array", ("piece",), columns=3, rows=2,
                                  spacing_mm=2.0)],
        )

    def test_attached_bitmap_uses_procedural_array_offsets(self):
        offsets = raster_instance_offsets(self._document())
        self.assertEqual(offsets, ((0.0, 0.0), (12.0, 0.0), (24.0, 0.0),
                                   (0.0, 7.0), (12.0, 7.0), (24.0, 7.0)))

    def test_disabled_bitmap_placements_are_not_generated(self):
        document = self._document()
        current = document.arrays[0]
        document.arrays[0] = InstanceArray(
            current.id, current.object_ids, columns=3, rows=2,
            spacing_mm=2.0, disabled_indices=(1, 4),
        )
        self.assertEqual(
            raster_instance_offsets(document),
            ((0.0, 0.0), (24.0, 0.0), (0.0, 7.0), (24.0, 7.0)),
        )

    def test_scanline_pixels_are_processed_once_then_instanced(self):
        source = RasterScanlines(
            [[0.0, 1.0, 2], [2.0, 1.0, 2]], 2.0, 1,
            [[0.0, 1.0], [2.0, 1.0]],
        )
        result = repeat_scanlines(source, ((0.0, 0.0), (25.4, 12.7)))
        self.assertEqual(len(result.ecoords), 4)
        self.assertEqual(result.ecoords[2][:2], [1.0, 1.5])
        self.assertNotEqual(result.ecoords[1][2], result.ecoords[2][2])
        self.assertEqual(result.length_inches, 4.0)
        self.assertEqual(result.scanline_count, 2)

    def test_metric_only_scanlines_are_multiplied_without_coordinates(self):
        source = RasterScanlines([], 3.5, 4, [])
        result = repeat_scanlines(source, ((0, 0), (10, 0), (20, 0)))
        self.assertEqual(result.ecoords, [])
        self.assertEqual(result.length_inches, 10.5)
        self.assertEqual(result.scanline_count, 12)

    def test_alpha_mask_controls_effective_raster_bounds(self):
        image = Image.new("RGBA", (100, 80), (255, 255, 255, 0))
        ImageDraw.Draw(image).rectangle((20, 10, 59, 49), fill=(0, 0, 0, 255))

        bounds = raster_content_bounds(
            image, 254.0, Bounds(100, 200, 110, 208),
            vector_offset_x_mm=1.0, vector_offset_y_mm=2.0,
        )

        self.assertEqual(bounds, Bounds(101.0, 201.0, 105.0, 205.0))

    def test_preview_y_is_normalized_from_complete_array_top(self):
        offsets = preview_bitmap_offsets(
            Bounds(0, 0, 10, 10), Bounds(0, 0, 10, 22),
            ((0, 0), (0, 12)),
        )

        self.assertEqual(offsets, ((0, -12), (0, 0)))


if __name__ == "__main__":
    unittest.main()
