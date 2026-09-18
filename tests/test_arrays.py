import unittest

from k40core.arrays import instance_offsets, maximum_array_counts
from k40core.legacy import vector_lines_in_inches
from k40core.model import (
    Bounds, FillObject, ImportSource, InstanceArray, JobDocument, Layer, LineSegment,
    Operation, Point, VectorObject, VectorPath,
)
from k40core.rasterizer import (
    dpi_for_pixel_budget, raster_dpi_for_rebuild, raster_pixel_count,
    rasterize_fills,
)


class InstanceArrayTests(unittest.TestCase):
    def test_execution_order_is_explicit_and_validated(self):
        self.assertEqual(
            InstanceArray("array", ("part",)).execution_order,
            "by_process",
        )
        self.assertEqual(
            InstanceArray(
                "array", ("part",), execution_order="by_instance"
            ).execution_order,
            "by_instance",
        )
        with self.assertRaises(ValueError):
            InstanceArray("array", ("part",), execution_order="random")

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

    def test_disabled_instances_are_skipped_but_remain_addressable(self):
        array = InstanceArray(
            "array:1", ("part",), columns=3, rows=2, spacing_mm=2.0,
            disabled_indices=(1, 4),
        )
        bounds = Bounds(0, 0, 10, 5)

        self.assertEqual(list(instance_offsets(array, bounds)), [
            (0.0, 0.0), (24.0, 0.0), (0.0, 7.0), (24.0, 7.0),
        ])
        self.assertEqual(len(list(instance_offsets(
            array, bounds, include_disabled=True
        ))), 6)

    def test_raster_reference_bounds_can_define_larger_piece_spacing(self):
        array = InstanceArray(
            "array:1", ("vector",), columns=2, rows=2, spacing_mm=2.0,
            reference_bounds=Bounds(-3, -1, 17, 7),
        )

        offsets = list(instance_offsets(array, Bounds(0, 0, 10, 5)))

        self.assertEqual(offsets, [
            (0.0, 0.0), (22.0, 0.0), (0.0, 10.0), (22.0, 10.0),
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

    def test_ignored_vector_instance_is_not_exported_and_layout_stays_fixed(self):
        layer = Layer("layer", "Corte")
        vector = VectorObject(
            "part", (VectorPath((LineSegment(Point(0, 0), Point(10, 0)),)),),
            layer.id, Operation.VECTOR_CUT,
        )
        document = JobDocument(
            ImportSource("fixture", "test", "test"), [layer], [vector],
            arrays=[InstanceArray(
                "array:1", (vector.id,), columns=2, spacing_mm=5.0,
                disabled_indices=(0,),
            )],
        )

        lines = vector_lines_in_inches(document, Operation.VECTOR_CUT)

        self.assertEqual(len(lines), 1)
        self.assertAlmostEqual(lines[0][0], 15.0/25.4)
        self.assertEqual(document.bounds, Bounds(0, 0, 25, 0))

    def test_array_repeats_solid_raster_fills(self):
        layer = Layer("layer", "Raster")
        path = VectorPath((
            LineSegment(Point(0, 0), Point(2, 0)),
            LineSegment(Point(2, 0), Point(2, 2)),
            LineSegment(Point(2, 2), Point(0, 2)),
            LineSegment(Point(0, 2), Point(0, 0)),
        ), closed=True)
        fill = FillObject("solid", (path,), layer.id)
        document = JobDocument(
            ImportSource("fixture", "test", "test"), [layer], fills=[fill],
            arrays=[InstanceArray("array:1", (fill.id,), columns=2, rows=1,
                                  spacing_mm=1.0)],
        )

        image = rasterize_fills(document, dpi=25.4)

        self.assertEqual(image.size, (5, 2))
        self.assertEqual(image.getpixel((0, 0)), 0)
        self.assertEqual(image.getpixel((4, 0)), 0)

        source_image = rasterize_fills(document, dpi=25.4, include_arrays=False)
        self.assertEqual(source_image.size, (2, 2))

    def test_large_raster_dpi_is_fitted_to_memory_budget(self):
        bounds = Bounds(0, 0, 500, 286)

        fitted = dpi_for_pixel_budget(bounds, 1000.0, 50_000_000)

        self.assertLess(fitted, 1000.0)
        self.assertLessEqual(raster_pixel_count(bounds, fitted), 50_000_000)
        self.assertEqual(dpi_for_pixel_budget(bounds, 300.0, 50_000_000), 300.0)

    def test_vector_only_array_does_not_require_raster_dpi(self):
        self.assertIsNone(raster_dpi_for_rebuild(False, False))
        self.assertIsNone(raster_dpi_for_rebuild(False, True))

    def test_fill_array_uses_available_dpi_or_safe_default(self):
        self.assertEqual(raster_dpi_for_rebuild(True, False, 600.0, 300.0), 600.0)
        self.assertEqual(raster_dpi_for_rebuild(True, False, 0.0, 300.0), 300.0)
        self.assertEqual(raster_dpi_for_rebuild(True, False), 254.0)
        self.assertIsNone(raster_dpi_for_rebuild(True, True, 600.0, 300.0))


if __name__ == "__main__":
    unittest.main()
