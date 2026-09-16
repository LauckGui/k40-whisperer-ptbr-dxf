import unittest

from PIL import Image

from k40core.model import Color, FillObject, ImportSource, JobDocument, Layer, LineSegment, Point, VectorPath
from k40core.raster_processing import color_intensities_from_document, prepare_grayscale


class RasterProcessingTests(unittest.TestCase):
    def test_transparency_is_laser_off_white(self):
        image = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
        image.putpixel((1, 0), (0, 0, 0, 255))

        prepared = prepare_grayscale(image)

        self.assertEqual(prepared.mode, "L")
        self.assertEqual(prepared.getpixel((0, 0)), 255)
        self.assertEqual(prepared.getpixel((1, 0)), 0)

    def test_gamma_and_inversion_are_applied(self):
        image = Image.new("L", (1, 1), 64)
        lighter = prepare_grayscale(image, gamma=2.0)
        inverted = prepare_grayscale(image, invert=True)

        self.assertGreater(lighter.getpixel((0, 0)), 64)
        self.assertEqual(inverted.getpixel((0, 0)), 191)

    def test_fill_colors_map_to_perceived_darkness(self):
        layer = Layer("layer:0", "Principal")
        path = VectorPath((
            LineSegment(Point(0, 0), Point(1, 0)),
            LineSegment(Point(1, 0), Point(0, 0)),
        ))
        document = JobDocument(
            ImportSource("fixture", "test", "fixture"), [layer],
            fills=[
                FillObject("black", (path,), layer.id, color=Color(0, 0, 0)),
                FillObject("white", (path,), layer.id, color=Color(255, 255, 255)),
                FillObject("green", (path,), layer.id, color=Color(0, 255, 0)),
            ],
        )

        levels = color_intensities_from_document(document)

        self.assertEqual(levels["#000000"], 1.0)
        self.assertEqual(levels["#ffffff"], 0.0)
        self.assertAlmostEqual(levels["#00ff00"], 0.413, places=3)


if __name__ == "__main__":
    unittest.main()
