import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "add_italic_cjk_guard.py"


def load_guard_module():
    scripts_dir = str(SCRIPT_PATH.parent)
    sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location("add_italic_cjk_guard", SCRIPT_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts_dir)


class ItalicCjkGuardTests(unittest.TestCase):
    def test_hangul_classifier_covers_jamo_and_syllables_only(self):
        guard = load_guard_module()

        self.assertTrue(guard.is_hangul_codepoint(0x1100))
        self.assertTrue(guard.is_hangul_codepoint(0x3131))
        self.assertTrue(guard.is_hangul_codepoint(ord("한")))
        self.assertFalse(guard.is_hangul_codepoint(ord("A")))
        self.assertFalse(guard.is_hangul_codepoint(ord("漢")))

    def test_guard_uses_minimum_clearance_and_conservative_buckets(self):
        guard = load_guard_module()

        self.assertEqual(
            guard.guard_units(right_overhang=-20, hangul_left_side_bearing=30),
            20,
        )
        self.assertEqual(
            guard.guard_units(right_overhang=45, hangul_left_side_bearing=30),
            45,
        )
        self.assertEqual(
            guard.guard_units(right_overhang=55, hangul_left_side_bearing=20),
            65,
        )

    def test_geometry_buckets_round_toward_more_clearance(self):
        guard = load_guard_module()

        self.assertEqual(guard.round_up(42, 5), 45)
        self.assertEqual(guard.round_up(-3, 5), 0)
        self.assertEqual(guard.round_down(22, 5), 20)
        self.assertEqual(guard.round_down(-3, 5), -5)


if __name__ == "__main__":
    unittest.main()
