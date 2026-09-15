import unittest

from PIL import Image

from k40core.preview import iter_preview_polylines, transparent_raster_preview


class PreviewTests(unittest.TestCase):
    def test_path_preview_preserves_contours_instead_of_sampling_segments(self):
        ecoords = [
            [0.0, 0.0, 1], [1.0, 1.0, 1], [2.0, 0.0, 1],
            [3.0, 1.0, 1], [4.0, 0.0, 1],
            [10.0, 0.0, 2], [11.0, 1.0, 2], [12.0, 0.0, 2],
        ]

        paths = list(iter_preview_polylines(
            ecoords, transform=lambda x, y: (x, y)
        ))

        self.assertEqual(len(paths), 2)
        first_path = paths[0]
        self.assertEqual(len(first_path), 10)

    def test_subpixel_filter_keeps_path_endpoint(self):
        ecoords = [[0.0, 0.0, 1], [0.1, 0.0, 1], [0.2, 0.0, 1]]

        paths = list(iter_preview_polylines(
            ecoords, transform=lambda x, y: (x, y), minimum_pixels=0.5
        ))

        path = paths[0]
        self.assertEqual(path[:2], (0.0, 0.0))
        self.assertEqual(path[-2:], (0.2, 0.0))

    def test_tiny_closed_contour_does_not_disappear(self):
        ecoords = [
            [0.0, 0.0, 1], [0.1, 0.0, 1],
            [0.1, 0.1, 1], [0.0, 0.0, 1],
        ]

        paths = list(iter_preview_polylines(
            ecoords, transform=lambda x, y: (x, y), minimum_pixels=0.5
        ))

        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0][:2], (0.0, 0.0))
        self.assertEqual(paths[0][-2:], (0.0, 0.0))
        self.assertGreater(len(paths[0]), 4)

    def test_white_raster_background_is_transparent_in_preview(self):
        source = Image.new("L", (2, 1), 255)
        source.putpixel((1, 0), 0)

        preview = transparent_raster_preview(source, (2, 1))

        self.assertEqual(preview.getpixel((0, 0)), (0, 0, 0, 0))
        self.assertEqual(preview.getpixel((1, 0)), (0, 0, 0, 255))


if __name__ == "__main__":
    unittest.main()
