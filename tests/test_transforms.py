import unittest

from k40core.model import (
    ArcSegment, Bounds, FillObject, ImportSource, InstanceArray, JobDocument,
    Layer, LineSegment, Operation, Point, VectorObject, VectorPath,
)
from k40core.transforms import (
    apply_document_transform, editable_bounds, reflection, rotation, uniform_scale,
)


class DocumentTransformTests(unittest.TestCase):
    def setUp(self):
        self.layer = Layer("layer:0", "Principal")
        self.vector = VectorObject(
            "vector:1", (VectorPath((ArcSegment(
                Point(10, 0), Point(0, 10), Point(0, 0)
            ),)),), self.layer.id, Operation.VECTOR_CUT,
        )
        self.fill = FillObject(
            "fill:1", (VectorPath((
                LineSegment(Point(0, 0), Point(10, 0)),
                LineSegment(Point(10, 0), Point(0, 10)),
                LineSegment(Point(0, 10), Point(0, 0)),
            ), closed=True),), self.layer.id,
        )
        self.document = JobDocument(
            ImportSource("fixture.dxf", "dxf", "test"), [self.layer],
            [self.vector], fills=[self.fill],
            arrays=[InstanceArray("array:1", ("vector:1", "fill:1"), columns=2)],
        )

    def test_uniform_scale_preserves_arc_and_recomputes_array_bounds(self):
        before = self.document.bounds
        pivot = Point(0, 0)
        apply_document_transform(self.document, uniform_scale(2.0, pivot))

        self.assertIsInstance(self.document.vectors[0].paths[0].segments[0], ArcSegment)
        self.assertEqual(editable_bounds(self.document), Bounds(-20, -20, 20, 20))
        self.assertEqual(self.document.bounds, Bounds(-20, -20, 60, 20))
        self.assertGreater(self.document.bounds.width, before.width)

    def test_rotation_and_reflection_keep_object_ids_and_array_links(self):
        pivot = Point(5, 5)
        before = editable_bounds(self.document)
        apply_document_transform(self.document, rotation(90, pivot))
        apply_document_transform(self.document, reflection(True, pivot))

        self.assertEqual(self.document.arrays[0].object_ids, ("vector:1", "fill:1"))
        self.assertEqual(self.document.vectors[0].id, "vector:1")
        after = editable_bounds(self.document)
        self.assertAlmostEqual((before.min_x+before.max_x)/2.0,
                               (after.min_x+after.max_x)/2.0)
        self.assertAlmostEqual((before.min_y+before.max_y)/2.0,
                               (after.min_y+after.max_y)/2.0)
        self.document.validate()

    def test_invalid_scale_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "escala"):
            uniform_scale(0.0, Point(0, 0))

    def test_array_raster_reference_bounds_follow_vector_transform(self):
        current = self.document.arrays[0]
        self.document.arrays[0] = InstanceArray(
            current.id, current.object_ids, columns=2,
            reference_bounds=Bounds(-5, -2, 15, 12),
        )

        apply_document_transform(
            self.document, uniform_scale(2.0, Point(0, 0))
        )

        self.assertEqual(
            self.document.arrays[0].reference_bounds,
            Bounds(-10, -4, 30, 24),
        )


if __name__ == "__main__":
    unittest.main()
