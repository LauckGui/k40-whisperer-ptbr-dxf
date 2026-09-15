import math
import unittest

from k40core.model import ArcSegment, CubicBezierSegment, Point
from k40core.tessellation import adaptive_segment_points


class AdaptiveTessellationTests(unittest.TestCase):
    def test_arc_chords_respect_requested_maximum_deviation(self):
        radius = 100.0
        tolerance = 0.05
        arc = ArcSegment(Point(radius, 0), Point(0, radius), Point(0, 0))

        points = adaptive_segment_points(arc, tolerance)

        deviations = []
        for start, end in zip(points, points[1:]):
            chord = math.hypot(end.x-start.x, end.y-start.y)
            deviations.append(radius-math.sqrt(max(0.0, radius*radius-chord*chord/4.0)))
        self.assertLessEqual(max(deviations), tolerance+1e-12)
        self.assertEqual(points[0], arc.start)
        self.assertEqual(points[-1], arc.end)

    def test_tolerance_and_radius_control_segment_count(self):
        small = ArcSegment(Point(10, 0), Point(0, 10), Point(0, 0))
        large = ArcSegment(Point(100, 0), Point(0, 100), Point(0, 0))

        small_count = len(adaptive_segment_points(small, 0.05))
        large_count = len(adaptive_segment_points(large, 0.05))
        loose_count = len(adaptive_segment_points(large, 0.5))

        self.assertGreater(large_count, small_count)
        self.assertLess(loose_count, large_count)

    def test_s_curve_is_not_mistaken_for_a_straight_chord(self):
        curve = CubicBezierSegment(
            Point(0, 0), Point(3, 10), Point(7, -10), Point(10, 0)
        )

        points = adaptive_segment_points(curve, 0.1)

        self.assertGreater(len(points), 2)
        self.assertEqual(points[0], curve.start)
        self.assertEqual(points[-1], curve.end)

    def test_invalid_tolerance_is_rejected(self):
        arc = ArcSegment(Point(1, 0), Point(0, 1), Point(0, 0))

        with self.assertRaises(ValueError):
            adaptive_segment_points(arc, 0.0)


if __name__ == "__main__":
    unittest.main()
