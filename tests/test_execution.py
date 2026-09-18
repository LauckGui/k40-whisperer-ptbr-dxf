import unittest

from k40core.execution import (
    document_instance_offsets, indexed_instance_offsets, split_repeated_ecoords,
    origin_ordered_instance_offsets, standalone_egv_jobs, translate_ecoords,
)
from k40core.model import (
    Bounds, ImportSource, InstanceArray, JobDocument, Layer, LineSegment,
    Operation, Point, VectorObject, VectorPath,
)


class ArrayExecutionTests(unittest.TestCase):
    def test_indexed_offsets_keep_grid_identity_when_a_piece_is_disabled(self):
        array = InstanceArray(
            "array", ("part",), columns=3, rows=1, spacing_mm=2,
            disabled_indices=(1,), execution_order="by_instance",
        )

        self.assertEqual(indexed_instance_offsets(array, Bounds(0, 0, 10, 5)), (
            (0, 0.0, 0.0), (2, 24.0, 0.0),
        ))

    def test_document_offsets_use_procedural_reference_bounds(self):
        layer = Layer("layer", "Cut")
        vector = VectorObject(
            "part", (VectorPath((LineSegment(Point(0, 0), Point(10, 0)),)),),
            layer.id, Operation.VECTOR_CUT,
        )
        document = JobDocument(
            ImportSource("fixture", "test", "test"), [layer], [vector],
            arrays=[InstanceArray(
                "array", (vector.id,), columns=2, spacing_mm=1,
                reference_bounds=Bounds(-2, -3, 12, 7),
            )],
        )

        self.assertEqual(document_instance_offsets(document), (
            (0, 0.0, 0.0), (1, 15.0, 0.0),
        ))

    def test_execution_starts_at_upper_machine_origin(self):
        layer = Layer("layer", "Cut")
        vector = VectorObject(
            "part", (VectorPath((LineSegment(Point(0, 0), Point(10, 0)),)),),
            layer.id, Operation.VECTOR_CUT,
        )
        document = JobDocument(
            ImportSource("fixture", "test", "test"), [layer], [vector],
            arrays=[InstanceArray(
                "array", (vector.id,), columns=3, rows=2, spacing_mm=1,
                disabled_indices=(4,), reference_bounds=Bounds(0, 0, 10, 5),
            )],
        )

        self.assertEqual(
            [item[0] for item in origin_ordered_instance_offsets(document)],
            [3, 5, 0, 1, 2],
        )
        self.assertEqual(
            [item[0] for item in origin_ordered_instance_offsets(
                document, home_on_right=True
            )],
            [5, 3, 2, 1, 0],
        )

    def test_translate_does_not_mutate_cached_base(self):
        base = [[1.0, 2.0, 4], [3.0, 5.0, 4]]

        translated = translate_ecoords(base, 10.0, -2.0)

        self.assertEqual(translated, [[11.0, 0.0, 4], [13.0, 3.0, 4]])
        self.assertEqual(base, [[1.0, 2.0, 4], [3.0, 5.0, 4]])

    def test_raster_chunks_are_recovered_without_copying_pixels(self):
        repeated = [[0, 0, 1], [1, 0, 1], [2, 0, 2], [3, 0, 2]]

        chunks = split_repeated_ecoords(repeated, 2)

        self.assertEqual(chunks, (
            [[0, 0, 1], [1, 0, 1]], [[2, 0, 2], [3, 0, 2]],
        ))
        with self.assertRaises(ValueError):
            split_repeated_ecoords(repeated, 3)

    def test_piece_operations_remain_independent_egv_jobs(self):
        raster = [ord("V"), ord("F"), ord("N"), ord("S"), ord("E")]
        vector = [ord("C"), ord("F"), ord("N"), ord("S"), ord("E")]

        jobs = standalone_egv_jobs(((raster, 1), (vector, 2)))

        self.assertEqual(len(jobs), 3)
        self.assertTrue(all(job[0] == ord("I") for job in jobs))
        self.assertTrue(all(job[-4:] == [ord("F"), ord("N"), ord("S"), ord("E")]
                            for job in jobs))
        self.assertEqual(raster[-4], ord("F"))
        self.assertIsNot(jobs[1], jobs[2])


if __name__ == "__main__":
    unittest.main()
