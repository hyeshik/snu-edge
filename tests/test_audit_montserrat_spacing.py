import unittest

from scripts.audit_montserrat_spacing import proportionally_spaced_gap, transformed_gap


class SpacingTransformTest(unittest.TestCase):
    def test_additive_tracking_is_post_scale(self):
        self.assertEqual(transformed_gap(200, 0.86, -5), 167)

    def test_proportional_spacing_preserves_contour_recession(self):
        self.assertAlmostEqual(
            proportionally_spaced_gap(200, 150, 0.86, 0.9),
            159.1,
        )

    def test_unit_spacing_scale_is_affine_width_only(self):
        self.assertEqual(
            proportionally_spaced_gap(200, 150, 0.86, 1),
            172,
        )

if __name__ == "__main__":
    unittest.main()
