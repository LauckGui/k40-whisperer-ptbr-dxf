import unittest

from k40core.model import LineSegment, Point
from k40core.topology import stitch_line_segments


class TopologyTests(unittest.TestCase):
    def test_unordered_reversed_square_becomes_one_closed_path(self):
        segments = [
            LineSegment(Point(10, 10), Point(10, 0)),
            LineSegment(Point(0, 0), Point(10, 0)),
            LineSegment(Point(0, 10), Point(0, 0)),
            LineSegment(Point(10, 10), Point(0, 10)),
        ]

        paths = stitch_line_segments(segments)

        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].closed)
        self.assertEqual(len(paths[0].segments), 4)

    def test_small_export_gap_is_joined_but_larger_gap_is_not(self):
        segments = [
            LineSegment(Point(0, 0), Point(1, 0)),
            LineSegment(Point(1.01, 0), Point(2, 0)),
            LineSegment(Point(3, 0), Point(4, 0)),
        ]

        paths = stitch_line_segments(segments, tolerance_mm=0.02)

        self.assertEqual([len(path.segments) for path in paths], [2, 1])


if __name__ == "__main__":
    unittest.main()
