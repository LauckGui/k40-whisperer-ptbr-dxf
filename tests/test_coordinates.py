import unittest

from k40core.coordinates import display_y, machine_y, origin_for_reference


class CoordinateDisplayTests(unittest.TestCase):
    def test_internal_negative_y_is_positive_in_interface(self):
        self.assertEqual(display_y(-20.5), 20.5)

    def test_positive_interface_y_becomes_internal_negative_y(self):
        self.assertEqual(machine_y(20.5), -20.5)

    def test_zero_is_preserved(self):
        self.assertEqual(display_y(0), 0.0)
        self.assertEqual(machine_y(0), 0.0)

    def test_center_reference_is_placed_at_requested_coordinate(self):
        origin = origin_for_reference(
            target_x=100.0, target_y=80.0,
            offset_x=25.0, offset_y=-15.0,
        )
        self.assertEqual(origin, (75.0, -65.0))
        self.assertEqual(origin[0]+25.0, 100.0)
        self.assertEqual(display_y(origin[1]-15.0), 80.0)

    def test_lower_right_reference_compensates_full_object_size(self):
        origin = origin_for_reference(
            target_x=140.0, target_y=100.0,
            offset_x=50.0, offset_y=-30.0,
        )
        self.assertEqual(origin, (90.0, -70.0))

    def test_right_home_reference_preserves_negative_ui_x(self):
        origin = origin_for_reference(
            target_x=-100.0, target_y=80.0,
            offset_x=25.0, offset_y=-15.0,
            home_on_right=True,
        )
        self.assertEqual(origin, (75.0, -65.0))


if __name__ == "__main__":
    unittest.main()
