import unittest

from PIL import Image

from k40core.raster_paths import extract_scanlines


class RasterPathTests(unittest.TestCase):
    def test_extracts_dark_runs_and_metrics_without_per_pixel_python_loop(self):
        image = Image.new("L", (6, 3), 255)
        pixels = image.load()
        for y in range(3):
            pixels[1, y] = 0
            pixels[2, y] = 0
            pixels[4, y] = 0

        result = extract_scanlines(image, dpi=1000.0, raster_step_mils=1)

        self.assertEqual(result.scanline_count, 3)
        self.assertEqual(len(result.ecoords), 12)
        self.assertAlmostEqual(result.length_inches, 0.012)
        self.assertEqual(result.ecoords[0][:2], [0.001, 0.003])
        self.assertEqual(result.ecoords[1][:2], [0.003, 0.003])

    def test_skips_white_rows(self):
        image = Image.new("L", (5, 2), 255)
        image.putpixel((2, 1), 0)

        result = extract_scanlines(image, dpi=1000.0, raster_step_mils=1)

        self.assertEqual(result.scanline_count, 1)
        self.assertEqual(len(result.ecoords), 2)


if __name__ == "__main__":
    unittest.main()
