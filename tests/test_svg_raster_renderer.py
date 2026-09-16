import os
import tempfile
import unittest
import warnings

from PIL import Image

from svg_reader import SVG_READER


class SvgRasterRendererTests(unittest.TestCase):
    def test_external_image_rasterizes_without_inkscape(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = os.path.join(directory, "art.png")
            svg_path = os.path.join(directory, "art.svg")
            Image.new("RGB", (4, 2), "black").save(image_path)
            with open(svg_path, "w", encoding="utf-8") as stream:
                stream.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" '
                    'xmlns:xlink="http://www.w3.org/1999/xlink" '
                    'width="10mm" height="5mm" viewBox="0 0 10 5">'
                    '<image x="0" y="0" width="10" height="5" '
                    'xlink:href="art.png"/></svg>'
                )
            reader = SVG_READER()
            reader.image_dpi = 254
            reader.parse_svg(svg_path)
            # CairoSVG currently leaves the local resource stream for Python's
            # finalizer; this is harmless but noisy under unittest warnings.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                reader.make_paths()

            self.assertIsNone(reader.inkscape_exe)
            self.assertEqual(reader.raster_PIL.size, (100, 50))
            self.assertEqual(reader.raster_PIL.getpixel((50, 25)), 0)

    def test_svg_content_is_cropped_to_a_shared_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = os.path.join(directory, "art.png")
            svg_path = os.path.join(directory, "art.svg")
            Image.new("RGB", (4, 2), "black").save(image_path)
            with open(svg_path, "w", encoding="utf-8") as stream:
                stream.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" '
                    'xmlns:xlink="http://www.w3.org/1999/xlink" '
                    'width="20mm" height="10mm" viewBox="0 0 20 10">'
                    '<image x="5" y="3" width="4" height="2" '
                    'xlink:href="art.png"/>'
                    '<path d="M5,3 L9,3" stroke="#ff0000" fill="none"/>'
                    '</svg>'
                )
            reader = SVG_READER()
            reader.image_dpi = 254
            reader.parse_svg(svg_path)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                reader.make_paths()

            self.assertEqual(reader.raster_PIL.size, (50, 30))
            self.assertAlmostEqual(reader.Xsize, 5.0)
            self.assertAlmostEqual(reader.Ysize, 3.0)
            self.assertTrue(reader.cut_lines)
            # The guide path remains inside the normalized raster bounds.
            for line in reader.cut_lines:
                self.assertGreaterEqual(min(line[0], line[2]), 0.0)
                self.assertGreaterEqual(min(line[1], line[3]), 0.0)
                self.assertLessEqual(max(line[0], line[2]), reader.Xsize)
                self.assertLessEqual(max(line[1], line[3]), reader.Ysize)


if __name__ == "__main__":
    unittest.main()
