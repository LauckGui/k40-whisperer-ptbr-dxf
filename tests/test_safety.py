import unittest

from k40core.model import Bounds
from k40core.safety import WorkAreaError, placed_job_bounds, validate_work_area


class WorkAreaTests(unittest.TestCase):
    def setUp(self):
        self.machine = Bounds(0, -220, 325, 0)

    def test_accepts_job_inside_machine(self):
        validate_work_area(Bounds(10, -100, 110, -10), self.machine)

    def test_rejects_job_larger_than_machine(self):
        with self.assertRaisesRegex(WorkAreaError, "excede"):
            validate_work_area(Bounds(0, -100, 400, 0), self.machine)

    def test_rejects_job_outside_machine(self):
        with self.assertRaisesRegex(WorkAreaError, "fora"):
            validate_work_area(Bounds(-1, -100, 50, 0), self.machine)

    def test_allows_small_numeric_tolerance(self):
        validate_work_area(Bounds(-0.01, -220.01, 325.01, 0.01), self.machine)

    def test_places_job_from_left_home(self):
        self.assertEqual(placed_job_bounds(100, 50, 10, -5), Bounds(10, -55, 110, -5))

    def test_places_job_from_right_home(self):
        self.assertEqual(
            placed_job_bounds(100, 50, 300, -5, home_on_right=True),
            Bounds(200, -55, 300, -5),
        )


if __name__ == "__main__":
    unittest.main()
