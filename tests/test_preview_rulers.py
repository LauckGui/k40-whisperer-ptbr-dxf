import unittest

from k40core.preview import rectangular_trace, ruler_step, ruler_values


class PreviewRulerTests(unittest.TestCase):
    def test_nice_metric_step(self):
        self.assertEqual(ruler_step(325), 50.0)

    def test_values_include_machine_limit(self):
        self.assertEqual(ruler_values(325), [0.0, 50.0, 100.0, 150.0,
                                             200.0, 250.0, 300.0, 325.0])

    def test_zero_span_is_safe(self):
        self.assertEqual(ruler_values(0), [0.0])

    def test_rectangular_trace_is_closed_and_applies_gap(self):
        trace = rectangular_trace((10.0, 30.0, -20.0, 5.0), gap=2.0)
        self.assertEqual(trace[0], [8.0, 7.0, 1])
        self.assertEqual(trace[-1], trace[0])
        self.assertEqual(trace[2], [32.0, -22.0, 1])


if __name__ == "__main__":
    unittest.main()
