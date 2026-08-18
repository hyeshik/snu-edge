import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_v1_reference.py"


def load_reference_builder():
    scripts_dir = str(SCRIPT_PATH.parent)
    sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location("build_v1_reference", SCRIPT_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts_dir)


class BuildV1ReferenceTests(unittest.TestCase):
    def test_reference_family_cannot_collide_with_production(self):
        reference = load_reference_builder()

        self.assertEqual(reference.FAMILY_NAME, "SNU Edge v1 Reference")
        self.assertEqual(reference.POSTSCRIPT_FAMILY_NAME, "SNUEdgev1Reference")

    def test_historic_e_cap_is_confined_to_light_reference(self):
        reference = load_reference_builder()

        self.assertEqual(reference.historic_weight_offset("Light", ord("e"), 14), 10)
        self.assertEqual(reference.historic_weight_offset("Light", ord("a"), 14), 14)
        self.assertEqual(reference.historic_weight_offset("Medium", ord("e"), 14), 14)


if __name__ == "__main__":
    unittest.main()
