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

        self.assertAlmostEqual(finalizer.DEFAULT_KERN_SCALE, 0.8096)

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

    def test_figure_swap_promotes_tabular_outlines_and_metrics(self):
        finalizer = load_finalizer()

        class FakeCharStrings:
            charStringsAreIndexed = True

            def __init__(self, names):
                self.charStrings = {name: index for index, name in enumerate(names)}
                self.charStringsIndex = SimpleNamespace(
                    items=[f"{name}-outline" for name in names]
                )

            def __getitem__(self, name):
                return self.charStringsIndex.items[self.charStrings[name]]

        names = [name for pair in finalizer.FIGURE_SWAP_PAIRS for name in pair]
        char_strings = FakeCharStrings(names)
        metrics = {
            name: (700 if name.endswith((".tf", ".tosf")) else 500, 50)
            for name in names
        }
        font = {
            "CFF ": SimpleNamespace(
                cff=SimpleNamespace(
                    topDictIndex=[SimpleNamespace(CharStrings=char_strings)]
                )
            ),
            "hmtx": SimpleNamespace(metrics=metrics),
        }

        finalizer.swap_figure_outlines_and_metrics(font)

        self.assertEqual(char_strings["zero"], "zero.tf-outline")
        self.assertEqual(char_strings["zero.tf"], "zero-outline")
        self.assertEqual(metrics["zero"], (700, 50))
        self.assertEqual(metrics["zero.tf"], (500, 50))
        self.assertEqual(char_strings["zero.osf"], "zero.tosf-outline")
        self.assertEqual(char_strings["zero.tosf"], "zero.osf-outline")

    def test_numeric_spacing_features_reverse_for_tabular_default(self):
        finalizer = load_finalizer()
        pnum = SimpleNamespace(
            FeatureTag="pnum",
            Feature=SimpleNamespace(LookupListIndex=[10]),
        )
        tnum = SimpleNamespace(
            FeatureTag="tnum",
            Feature=SimpleNamespace(LookupListIndex=[20]),
        )
        font = {
            "GSUB": SimpleNamespace(
                table=SimpleNamespace(
                    FeatureList=SimpleNamespace(FeatureRecord=[pnum, tnum])
                )
            )
        }

        finalizer.swap_numeric_spacing_features(font)

        self.assertEqual(pnum.Feature.LookupListIndex, [20])
        self.assertEqual(tnum.Feature.LookupListIndex, [10])

    def test_figure_positioning_follows_swapped_outline_roles(self):
        finalizer = load_finalizer()
        subtable = SimpleNamespace(
            Format=2,
            Coverage=SimpleNamespace(glyphs=["zero", "A"]),
            ClassDef1=SimpleNamespace(classDefs={"zero": 3}),
            ClassDef2=SimpleNamespace(classDefs={"one": 4}),
        )
        glyph_ids = {"A": 1, "zero.tf": 2, "one.tf": 3}

        finalizer.remap_pair_position_subtable(
            subtable,
            finalizer.FIGURE_SWAP_MAP,
            glyph_ids,
        )

        self.assertEqual(subtable.Coverage.glyphs, ["A", "zero.tf"])
        self.assertEqual(subtable.ClassDef1.classDefs, {"zero.tf": 3})
        self.assertEqual(subtable.ClassDef2.classDefs, {"one.tf": 4})


if __name__ == "__main__":
    unittest.main()
