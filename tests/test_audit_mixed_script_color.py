import unittest

from scripts.audit_mixed_script_color import (
    RunMeasurement,
    aggregate,
    corpus_runs,
    union_length,
)


class MixedScriptColorAuditTest(unittest.TestCase):
    def test_union_length_merges_overlapping_ink_intervals(self):
        self.assertEqual(union_length([(0, 4), (3, 6), (8, 10)]), 8)

    def test_aggregate_weights_run_metrics_by_advance(self):
        runs = [
            RunMeasurement("a", 1, 0.2, 0.1, 1),
            RunMeasurement("bb", 2, 0.2, 0.5, 2),
        ]

        measured = aggregate(runs)

        self.assertAlmostEqual(measured["ink_density"], 0.4 / 3)
        self.assertAlmostEqual(measured["horizontal_whitespace"], 0.6 / 3)

    def test_long_corpus_keeps_both_scripts_substantial(self):
        korean = "".join(corpus_runs("ko")).replace(" ", "")
        latin = "".join(corpus_runs("latin")).replace(" ", "")

        self.assertGreater(len(korean), 800)
        self.assertGreater(len(latin), 300)


if __name__ == "__main__":
    unittest.main()
