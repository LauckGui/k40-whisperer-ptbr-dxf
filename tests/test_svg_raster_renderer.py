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


if __name__ == "__main__":
    unittest.main()
