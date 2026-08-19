import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_snu_edge.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_snu_edge", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildSnuEdgeTests(unittest.TestCase):
    def test_download_url_and_defaults_match_project_contract(self):
        builder = load_builder()

        self.assertEqual(builder.FAMILY_NAME, "SNU Edge")
        self.assertEqual(builder.POSTSCRIPT_FAMILY_NAME, "SNUEdge")
        self.assertEqual(builder.VERSION, "0.303")
        self.assertEqual(
            builder.DEFAULT_SOURCE_ZIP_URL,
            "https://campaign.naver.com/nanumsquare_neo/download/NaverNanumSquare.zip",
        )
        self.assertEqual(builder.DEFAULT_CJK_GLYPH_X_SCALE, 0.96)
        self.assertEqual(builder.DEFAULT_CJK_SPACING_SCALE, 0.86)
        self.assertEqual(builder.DEFAULT_LATIN_GLYPH_X_SCALE, 0.86)
        self.assertEqual(builder.DEFAULT_LATIN_SPACING_RATIO, 0.90)
        self.assertEqual(builder.DEFAULT_LATIN_Y_SCALE, 1.028)
        self.assertEqual(builder.DEFAULT_LATIN_Y_SHIFT, -26)

    def test_style_matrix_uses_nanumsquare_masters_and_synthetic_steps(self):
        builder = load_builder()
        specs = {spec.style: spec for spec in builder.STYLE_SPECS}

        self.assertEqual(
            list(specs),
            ["Thin", "Light", "Regular", "Medium", "SemiBold", "Bold", "ExtraBold", "Black"],
        )
        self.assertEqual(specs["Thin"].source_label, "Light")
        self.assertEqual(specs["Light"].source_label, "Light")
        self.assertEqual(specs["Light"].synthetic_weight_steps, 1)
        self.assertEqual(specs["Regular"].source_label, "Regular")
        self.assertEqual(specs["Medium"].source_label, "Regular")
        self.assertEqual(specs["Medium"].synthetic_weight_steps, 1)
        self.assertEqual(specs["SemiBold"].source_label, "Bold")
        self.assertEqual(specs["Bold"].source_label, "Bold")
        self.assertEqual(specs["Bold"].synthetic_weight_steps, 1)
        self.assertEqual(specs["ExtraBold"].source_label, "ExtraBold")
        self.assertEqual(specs["Black"].source_label, "ExtraBold")
        self.assertEqual(specs["Black"].synthetic_weight_steps, 1)
        self.assertEqual(
            [spec.latin_weight for spec in specs.values()],
            [285, 367, 434, 495, 545, 603, 652, 711],
        )

    def test_master_classifier_supports_legacy_and_neo_filenames(self):
        builder = load_builder()

        cases = {
            "NanumSquareL.otf": "Light",
            "NanumSquareR.otf": "Regular",
            "NanumSquareB.otf": "Bold",
            "NanumSquareEB.otf": "ExtraBold",
            "NanumSquareNeo-aLt.ttf": "Light",
            "NanumSquareNeo-bRg.ttf": "Regular",
            "NanumSquareNeo-cBd.ttf": "Bold",
            "NanumSquareNeo-dEb.ttf": "ExtraBold",
            "NanumSquareNeo-eHv.ttf": None,
        }

        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(builder.classify_master(pathlib.Path(filename)), expected)

    def test_parser_maps_source_url_to_download_argument(self):
        builder = load_builder()

        args = builder.build_parser().parse_args([])
        self.assertEqual(args.source_zip_url, builder.DEFAULT_SOURCE_ZIP_URL)

        args = builder.build_parser().parse_args(
            ["--source-url", "https://example.test/NaverNanumSquare.zip"]
        )
        self.assertEqual(
            args.source_zip_url,
            "https://example.test/NaverNanumSquare.zip",
        )

    def test_source_discovery_prefers_expected_masters(self):
        builder = load_builder()
        paths = [
            pathlib.Path("NanumSquareNeo-eHv.ttf"),
            pathlib.Path("NanumSquareNeo-dEb.ttf"),
            pathlib.Path("NanumSquareNeo-bRg.ttf"),
            pathlib.Path("NanumSquareNeo-aLt.ttf"),
            pathlib.Path("NanumSquareNeo-cBd.ttf"),
        ]

        masters = builder.discover_master_paths(paths)

        self.assertEqual(masters["Light"].name, "NanumSquareNeo-aLt.ttf")
        self.assertEqual(masters["Regular"].name, "NanumSquareNeo-bRg.ttf")
        self.assertEqual(masters["Bold"].name, "NanumSquareNeo-cBd.ttf")
        self.assertEqual(masters["ExtraBold"].name, "NanumSquareNeo-dEb.ttf")

    def test_source_discovery_prefers_primary_masters_over_ac_variants(self):
        builder = load_builder()
        paths = [
            pathlib.Path("NanumSquareOTF_acL.otf"),
            pathlib.Path("NanumSquareOTF_acR.otf"),
            pathlib.Path("NanumSquareOTF_acB.otf"),
            pathlib.Path("NanumSquareOTF_acEB.otf"),
            pathlib.Path("NanumSquareL.otf"),
            pathlib.Path("NanumSquareR.otf"),
            pathlib.Path("NanumSquareB.otf"),
            pathlib.Path("NanumSquareEB.otf"),
        ]

        masters = builder.discover_master_paths(paths)

        self.assertEqual(masters["Light"].name, "NanumSquareL.otf")
        self.assertEqual(masters["Regular"].name, "NanumSquareR.otf")
        self.assertEqual(masters["Bold"].name, "NanumSquareB.otf")
        self.assertEqual(masters["ExtraBold"].name, "NanumSquareEB.otf")

    def test_metric_and_weight_helpers_match_current_design(self):
        builder = load_builder()

        metrics = builder.adjusted_glyph_metrics(
            xmin=62,
            xmax=893,
            left_side_bearing=62,
            right_side_bearing=17,
            x_scale=builder.DEFAULT_CJK_GLYPH_X_SCALE,
            spacing_scale=builder.DEFAULT_CJK_SPACING_SCALE,
        )

        self.assertEqual(metrics.advance_width, 866)
        self.assertAlmostEqual(metrics.left_side_bearing, 53.32)
        self.assertAlmostEqual(metrics.right_side_bearing, 14.62)
        self.assertAlmostEqual(metrics.outline_width, 797.76)
        self.assertEqual(builder.derive_synthetic_weight_width([44, 70, 99, 128]), 14)

    def test_latin_spacing_scales_with_transformed_width(self):
        builder = load_builder()

        metrics = builder.adjusted_glyph_metrics(
            xmin=50,
            xmax=650,
            left_side_bearing=50,
            right_side_bearing=50,
            x_scale=builder.DEFAULT_LATIN_GLYPH_X_SCALE,
            spacing_scale=(
                builder.DEFAULT_LATIN_GLYPH_X_SCALE
                * builder.DEFAULT_LATIN_SPACING_RATIO
            ),
        )

        self.assertEqual(metrics.advance_width, 593)
        self.assertAlmostEqual(metrics.left_side_bearing, 38.7)
        self.assertAlmostEqual(metrics.right_side_bearing, 38.7)

    def test_latin_outline_overlaps_are_removed_after_unlinking_references(self):
        builder = load_builder()

        class FakeGlyph:
            references = (("component", (1, 0, 0, 1, 0, 0)),)

            def __init__(self):
                self.events = []

            def unlinkRef(self):
                self.events.append("unlink")
                self.references = ()

            def selfIntersects(self):
                self.events.append("inspect")
                return True

            def removeOverlap(self):
                self.events.append("remove")

        glyph = FakeGlyph()

        self.assertTrue(builder.normalize_latin_outline(glyph))
        self.assertEqual(glyph.events, ["unlink", "inspect", "remove"])

    def test_tabular_figures_share_one_centered_advance(self):
        builder = load_builder()

        class FakeGlyph:
            def __init__(self, width, left_side_bearing):
                self.width = width
                self.left_side_bearing = left_side_bearing

        font = {
            name: FakeGlyph(580 + index % 13, 40)
            for index, name in enumerate(builder.TABULAR_FIGURE_NAMES)
        }

        target_width = builder.normalize_tabular_figure_widths(font)

        self.assertEqual(target_width, 592)
        self.assertEqual({glyph.width for glyph in font.values()}, {592})
        self.assertEqual(font[builder.TABULAR_FIGURE_NAMES[0]].left_side_bearing, 46)
        self.assertEqual(font[builder.TABULAR_FIGURE_NAMES[13]].left_side_bearing, 46)

    def test_obsolete_nanum_latin_exceptions_are_removed(self):
        builder = load_builder()

        self.assertFalse(hasattr(builder, "SYNTHETIC_WEIGHT_CODEPOINT_CAPS"))
        self.assertFalse(hasattr(builder, "synthetic_weight_offset_for_codepoint"))
        self.assertFalse(hasattr(builder, "slant_non_cjk_glyphs"))


if __name__ == "__main__":
    unittest.main()
