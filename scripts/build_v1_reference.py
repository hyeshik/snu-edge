#!/usr/bin/env fontforge -lang=py -script
from __future__ import annotations

import argparse
import math
from pathlib import Path

from build_snu_edge import (
    DEFAULT_DOWNLOAD_DIR,
    DEFAULT_SOURCE_DIR,
    DEFAULT_SOURCE_ZIP_URL,
    STYLE_SPECS,
    adjust_glyph,
    derive_synthetic_weight_width_from_sources,
    ensure_source_fonts,
    flatten_cid_font,
    is_cjk_codepoint,
    open_source_font,
    postscript_style_name,
    selected_style_specs,
    style_name,
    suppress_c_stderr,
)


FAMILY_NAME = "SNU Edge v1 Reference"
POSTSCRIPT_FAMILY_NAME = "SNUEdgev1Reference"
VERSION = "002.000"
DEFAULT_OUTPUT_DIR = "proof/generated/v1_otf"
GLYPH_X_SCALE = 0.96
SPACING_SCALE = 0.86
ITALIC_ANGLE = 10.0


def historic_weight_offset(style: str, codepoint: int, offset_width: int) -> int:
    if style == "Light" and codepoint == ord("e"):
        return min(offset_width, 10)
    return offset_width


def apply_historic_synthetic_weight(
    font, style: str, offset_width: int, quiet: bool
) -> int:
    if not offset_width:
        return 0

    changed = 0
    with suppress_c_stderr(quiet):
        for glyph in list(font.glyphs()):
            if glyph.unicode < 0:
                continue
            glyph_offset = historic_weight_offset(style, glyph.unicode, offset_width)
            if glyph.references:
                glyph.unlinkRef()
            glyph.changeWeight(glyph_offset, "auto", 0, 0, "auto")
            changed += 1
    return changed


def adjust_encoded_glyphs(font) -> int:
    changed = 0
    for glyph in list(font.glyphs()):
        if glyph.unicode >= 0 and adjust_glyph(
            glyph,
            x_scale=GLYPH_X_SCALE,
            spacing_scale=SPACING_SCALE,
        ):
            changed += 1
    return changed


def slant_non_cjk_glyphs(font) -> tuple[int, int]:
    slope = math.tan(math.radians(ITALIC_ANGLE))
    slanted = 0
    upright = 0
    for glyph in list(font.glyphs()):
        if glyph.unicode < 0 or is_cjk_codepoint(glyph.unicode):
            upright += 1
            continue
        if glyph.references:
            glyph.unlinkRef()
        glyph.transform((1, 0, slope, 1, 0, 0))
        slanted += 1
    return slanted, upright


def remove_unencoded_glyphs(font) -> int:
    removed = 0
    for glyph in list(font.glyphs()):
        if glyph.unicode < 0 and glyph.glyphname != ".notdef":
            font.removeGlyph(glyph)
            removed += 1
    return removed


def rewrite_metadata(font, spec, italic: bool) -> None:
    output_style = style_name(spec.style, italic)
    full_name = f"{FAMILY_NAME} {output_style}"
    ps_name = f"{POSTSCRIPT_FAMILY_NAME}-{postscript_style_name(spec.style, italic)}"

    font.familyname = FAMILY_NAME
    font.fullname = full_name
    font.fontname = ps_name
    font.weight = "Normal" if spec.style == "Regular" else spec.style
    font.version = VERSION
    font.italicangle = -ITALIC_ANGLE if italic else 0
    font.os2_weight = spec.weight
    font.os2_width = 5
    font.os2_vendor = "SNUE"
    font.os2_stylemap = (1 if italic else 0) | (32 if spec.weight >= 700 else 0)
    if not italic and spec.weight == 400:
        font.os2_stylemap = 64
    font.sfnt_names = (
        ("English (US)", "Family", FAMILY_NAME),
        ("English (US)", "SubFamily", output_style),
        ("English (US)", "UniqueID", f"{VERSION};SNUE;{ps_name}"),
        ("English (US)", "Fullname", full_name),
        ("English (US)", "Version", f"Version {VERSION}"),
        ("English (US)", "PostScriptName", ps_name),
        ("English (US)", "Preferred Family", FAMILY_NAME),
        ("English (US)", "Preferred Styles", output_style),
    )


def output_path(output_dir: Path, spec, italic: bool) -> Path:
    return output_dir / (
        f"SNUEdge-{postscript_style_name(spec.style, italic)}.otf"
    )


def build_variant(fontforge, args, masters, spec, italic: bool) -> Path:
    quiet = not args.verbose_fontforge
    font = open_source_font(fontforge, masters[spec.source_label], quiet)
    try:
        flattened = flatten_cid_font(font, quiet)
        font.reencode("unicode")
        offset_width = spec.synthetic_weight_steps * args.synthetic_weight_width
        weighted = apply_historic_synthetic_weight(
            font, spec.style, offset_width, quiet
        )
        adjusted = adjust_encoded_glyphs(font)
        slanted, upright = slant_non_cjk_glyphs(font) if italic else (0, 0)
        removed = remove_unencoded_glyphs(font)
        rewrite_metadata(font, spec, italic)

        path = output_path(Path(args.output_dir), spec, italic)
        path.parent.mkdir(parents=True, exist_ok=True)
        with suppress_c_stderr(quiet):
            font.generate(str(path))
        print(
            f"{path}: adjusted={adjusted}, weighted={weighted}, "
            f"offset={offset_width}, unencoded_removed={removed}, "
            f"italic_slanted={slanted}, italic_upright={upright}, "
            f"cid_flattened={flattened}"
        )
        return path
    finally:
        font.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the proof-only historical SNU Edge v1 reference."
    )
    parser.add_argument("styles", nargs="*")
    parser.add_argument("--source-url", dest="source_zip_url", default=DEFAULT_SOURCE_ZIP_URL)
    parser.add_argument("--download-dir", default=DEFAULT_DOWNLOAD_DIR)
    parser.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--verbose-fontforge", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        import fontforge
    except ModuleNotFoundError as exc:
        raise SystemExit("Run this script with FontForge.") from exc

    masters = ensure_source_fonts(args)
    specs = selected_style_specs(args.styles)
    args.synthetic_weight_width = derive_synthetic_weight_width_from_sources(
        fontforge, masters, not args.verbose_fontforge
    )
    for spec in specs:
        build_variant(fontforge, args, masters, spec, italic=False)
        build_variant(fontforge, args, masters, spec, italic=True)


if __name__ == "__main__":
    main()
