import unittest

from k40core.arrays import instance_offsets, maximum_array_counts
from k40core.legacy import vector_lines_in_inches
from k40core.model import (
    Bounds, ImportSource, InstanceArray, JobDocument, Layer, LineSegment,
    Operation, Point, VectorObject, VectorPath,
)


class InstanceArrayTests(unittest.TestCase):
    def test_grid_offsets_include_original_without_cloning_geometry(self):
        array = InstanceArray("array:1", ("part",), columns=3, rows=2,
                              spacing_mm=2.0)
        bounds = Bounds(0, 0, 10, 5)

        offsets = list(instance_offsets(array, bounds))

        self.assertEqual(offsets, [
            (0.0, 0.0), (12.0, 0.0), (24.0, 0.0),
            (0.0, 7.0), (12.0, 7.0), (24.0, 7.0),
        ])

    def test_staggered_rows_apply_custom_x_and_y_adjustment(self):
        array = InstanceArray(
            "array:1", ("part",), columns=2, rows=3, spacing_mm=2.0,
            mode="staggered", stagger_x_mm=6.0, row_adjust_y_mm=-1.0,
        )

        offsets = list(instance_offsets(array, Bounds(0, 0, 10, 5)))

        self.assertEqual(offsets, [
            (0.0, 0.0), (12.0, 0.0),
            (6.0, 6.0), (18.0, 6.0),
            (0.0, 12.0), (12.0, 12.0),
        ])

    def test_fill_available_area_respects_staggered_overhang(self):
        counts = maximum_array_counts(
            Bounds(0, 0, 10, 10), 35, 32, 1,
            mode="staggered", stagger_x_mm=5.5,
        )

        self.assertEqual(counts, (2, 3))
        negative_counts = maximum_array_counts(
            Bounds(0, 0, 10, 10), 35, 32, 1,
            mode="staggered", stagger_x_mm=-5.5,
        )
        self.assertEqual(negative_counts, counts)

    def test_fill_prefers_single_row_if_stagger_overhang_cannot_fit(self):
        counts = maximum_array_counts(
            Bounds(0, 0, 10, 10), 35, 100, 1,
            mode="staggered", stagger_x_mm=40,
        )

        self.assertEqual(counts, (3, 1))

    def test_legacy_expands_instances_but_document_keeps_one_vector(self):
        layer = Layer("layer", "Corte")
        vector = VectorObject(
            "part", (VectorPath((LineSegment(Point(0, 0), Point(10, 0)),)),),
            layer.id, Operation.VECTOR_CUT,
        )
        document = JobDocument(
            ImportSource("fixture", "test", "test"), [layer], [vector],
            arrays=[InstanceArray("array:1", (vector.id,), columns=2, rows=1,
                                  spacing_mm=5.0)],
        )

        lines = vector_lines_in_inches(document, Operation.VECTOR_CUT)

        self.assertEqual(len(document.vectors), 1)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(lines[1][0], 15.0/25.4)
        self.assertEqual(document.bounds, Bounds(0, 0, 25, 0))


if __name__ == "__main__":
    unittest.main()
