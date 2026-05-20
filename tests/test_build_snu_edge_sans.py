import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_snu_edge_sans.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_snu_edge_sans", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildSnuEdgeSansTests(unittest.TestCase):
    def test_download_url_and_defaults_match_project_contract(self):
        builder = load_builder()

        self.assertEqual(
            builder.DEFAULT_SOURCE_ZIP_URL,
            "https://campaign.naver.com/nanumsquare_neo/download/NaverNanumSquare.zip",
        )
        self.assertEqual(builder.DEFAULT_GLYPH_X_SCALE, 0.96)
        self.assertEqual(builder.DEFAULT_SPACING_SCALE, 0.86)
        self.assertEqual(builder.DEFAULT_ITALIC_ANGLE, 10.0)

    def test_style_matrix_uses_nanumsquare_masters_and_synthetic_steps(self):
        builder = load_builder()
        specs = {spec.style: spec for spec in builder.STYLE_SPECS}

        self.assertEqual(
            list(specs),
            ["Thin", "Light", "Regular", "Medium", "SemiBold", "Bold", "ExtraBlack", "Black"],
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
        self.assertEqual(specs["ExtraBlack"].source_label, "ExtraBold")
        self.assertEqual(specs["Black"].source_label, "ExtraBold")
        self.assertEqual(specs["Black"].synthetic_weight_steps, 1)

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
            x_scale=builder.DEFAULT_GLYPH_X_SCALE,
            spacing_scale=builder.DEFAULT_SPACING_SCALE,
        )

        self.assertEqual(metrics.advance_width, 866)
        self.assertAlmostEqual(metrics.left_side_bearing, 53.32)
        self.assertAlmostEqual(metrics.right_side_bearing, 14.62)
        self.assertAlmostEqual(metrics.outline_width, 797.76)
        self.assertEqual(builder.derive_synthetic_weight_width([44, 70, 99, 128]), 14)

    def test_light_lowercase_e_caps_synthetic_weight_to_preserve_counter_shape(self):
        builder = load_builder()

        self.assertEqual(
            builder.synthetic_weight_offset_for_codepoint("Light", ord("e"), 14),
            10,
        )
        self.assertEqual(
            builder.synthetic_weight_offset_for_codepoint("Light", ord("a"), 14),
            14,
        )
        self.assertEqual(
            builder.synthetic_weight_offset_for_codepoint("Medium", ord("e"), 14),
            14,
        )

    def test_italic_slants_non_cjk_and_keeps_cjk_upright(self):
        builder = load_builder()

        self.assertTrue(builder.should_slant_codepoint(ord("A")))
        self.assertTrue(builder.should_slant_codepoint(ord("Ω")))
        self.assertFalse(builder.should_slant_codepoint(0xAC00))
        self.assertFalse(builder.should_slant_codepoint(0xFF21))
        self.assertAlmostEqual(builder.italic_slope(), 0.1763269807)


if __name__ == "__main__":
    unittest.main()
