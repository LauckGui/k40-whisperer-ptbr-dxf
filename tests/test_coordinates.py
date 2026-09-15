import unittest

from k40core.coordinates import display_y, machine_y


class CoordinateDisplayTests(unittest.TestCase):
    def test_internal_negative_y_is_positive_in_interface(self):
        self.assertEqual(display_y(-20.5), 20.5)

    def test_positive_interface_y_becomes_internal_negative_y(self):
        self.assertEqual(machine_y(20.5), -20.5)

    def test_zero_is_preserved(self):
        self.assertEqual(display_y(0), 0.0)
        self.assertEqual(machine_y(0), 0.0)


if __name__ == "__main__":
    unittest.main()
