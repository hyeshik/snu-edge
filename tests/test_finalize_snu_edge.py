import importlib.util
import pathlib
import sys
import unittest
from types import SimpleNamespace


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "finalize_snu_edge.py"


def load_finalizer():
    scripts_dir = str(SCRIPT_PATH.parent)
    sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location("finalize_snu_edge", SCRIPT_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts_dir)


class FinalizeSnuEdgeTests(unittest.TestCase):
    def test_default_kern_scale_matches_width_times_q(self):
        finalizer = load_finalizer()

        self.assertAlmostEqual(finalizer.DEFAULT_KERN_SCALE, 0.774)

    def test_value_record_scales_horizontal_values_only(self):
        finalizer = load_finalizer()
        value = SimpleNamespace(
            XPlacement=-10,
            YPlacement=12,
            XAdvance=100,
            YAdvance=-8,
        )

        changed = finalizer.scale_value_record(value, 0.774)

        self.assertEqual(changed, 2)
        self.assertEqual(value.XPlacement, -8)
        self.assertEqual(value.XAdvance, 77)
        self.assertEqual(value.YPlacement, 12)
        self.assertEqual(value.YAdvance, -8)

    def test_pair_position_format_one_scales_both_records(self):
        finalizer = load_finalizer()
        first = SimpleNamespace(XAdvance=-80)
        second = SimpleNamespace(XPlacement=20)
        subtable = SimpleNamespace(
            Format=1,
            PairSet=[
                SimpleNamespace(
                    PairValueRecord=[
                        SimpleNamespace(Value1=first, Value2=second),
                    ]
                )
            ],
        )

        changed = finalizer.scale_pair_position_subtable(subtable, 0.5)

        self.assertEqual(changed, 2)
        self.assertEqual(first.XAdvance, -40)
        self.assertEqual(second.XPlacement, 10)


if __name__ == "__main__":
    unittest.main()
