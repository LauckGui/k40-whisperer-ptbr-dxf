import unittest

from k40core.model import (
    Color, LineSegment, Operation, Point, VectorObject, VectorPath, VectorStyle,
)
from k40core.topology import (
    compose_vector_objects, simplify_vector_path, stitch_line_segments,
)


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

    def test_collinear_segments_are_simplified_without_changing_endpoints(self):
        path = VectorPath(tuple(
            LineSegment(Point(x, 0), Point(x+1, 0)) for x in range(10)
        ))

        simplified = simplify_vector_path(path, tolerance_mm=0.01)

        self.assertEqual(len(simplified.segments), 1)
        self.assertEqual(simplified.segments[0].start, Point(0, 0))
        self.assertEqual(simplified.segments[0].end, Point(10, 0))

    def test_composition_keeps_operations_and_colors_separate(self):
        red = VectorStyle(stroke=Color(255, 0, 0))
        blue = VectorStyle(stroke=Color(0, 0, 255))
        vectors = [
            VectorObject("a", (VectorPath((LineSegment(Point(0, 0), Point(1, 0)),)),),
                         "layer", Operation.VECTOR_CUT, red),
            VectorObject("b", (VectorPath((LineSegment(Point(1, 0), Point(2, 0)),)),),
                         "layer", Operation.VECTOR_CUT, red),
            VectorObject("c", (VectorPath((LineSegment(Point(2, 0), Point(3, 0)),)),),
                         "layer", Operation.VECTOR_ENGRAVE, blue),
        ]

        composed = compose_vector_objects(vectors)

        self.assertEqual(len(composed), 2)
        cut = next(item for item in composed if item.operation is Operation.VECTOR_CUT)
        self.assertEqual(len(cut.paths), 1)
        self.assertEqual(len(cut.paths[0].segments), 1)


if __name__ == "__main__":
    unittest.main()
