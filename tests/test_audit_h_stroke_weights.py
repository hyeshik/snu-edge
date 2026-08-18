import unittest

import numpy as np

from scripts.audit_h_stroke_weights import (
    StrokeMeasurement,
    find_matching_weight,
    measure_h,
)


class HStrokeMeasurementTest(unittest.TestCase):
    def test_measures_crossbar_and_vertical_stem_independently(self):
        glyph = np.zeros((20, 16), dtype=float)
        glyph[:, 1:4] = 1
        glyph[:, 12:15] = 1
        glyph[8:12, 1:15] = 1

        measured = measure_h(glyph)

        self.assertEqual(measured.crossbar, 4)
        self.assertEqual(measured.crossbar_span, 4)
        self.assertEqual(measured.vertical_stem, 3)

    def test_binary_search_returns_nearest_integer_weight(self):
        def measurement_at(weight):
            return StrokeMeasurement(weight / 10, 0, 0)

        self.assertEqual(find_matching_weight(measurement_at, 42.31), 423)


if __name__ == "__main__":
    unittest.main()
