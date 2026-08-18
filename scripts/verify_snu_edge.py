#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont

from build_snu_edge import (
    FAMILY_NAME,
    POSTSCRIPT_FAMILY_NAME,
    STYLE_SPECS,
    VERSION,
    postscript_style_name,
    style_name,
)


REQUIRED_TABLES = {"CFF ", "GPOS", "GSUB", "OS/2", "cmap", "name", "post"}
REQUIRED_CODEPOINTS = (ord("A"), ord("e"), ord("é"), ord("한"))


def verify_font(path: Path, spec, italic: bool) -> None:
    font = TTFont(path)
    missing_tables = REQUIRED_TABLES - set(font.keys())
    if missing_tables:
        raise ValueError(f"{path}: missing tables: {sorted(missing_tables)}")
    if "fvar" in font:
        raise ValueError(f"{path}: output must be a static font")

    cmap = font.getBestCmap()
    missing_codepoints = [
        f"U+{codepoint:04X}" for codepoint in REQUIRED_CODEPOINTS if codepoint not in cmap
    ]
    if missing_codepoints:
        raise ValueError(f"{path}: missing glyphs: {', '.join(missing_codepoints)}")
    if cmap[ord("A")] != "A" or cmap[ord("e")] != "e":
        raise ValueError(f"{path}: Latin cmap is not the Montserrat repertoire")
    if not cmap[ord("한")].startswith("Korea1."):
        raise ValueError(f"{path}: Hangul cmap is not the NanumSquare repertoire")

    names = font["name"]
    expected_style = style_name(spec.style, italic)
    expected_ps_name = (
        f"{POSTSCRIPT_FAMILY_NAME}-{postscript_style_name(spec.style, italic)}"
    )
    expected_names = {
        1: FAMILY_NAME,
        2: expected_style,
        5: f"Version {VERSION}",
        6: expected_ps_name,
    }
    for name_id, expected in expected_names.items():
        actual = names.getDebugName(name_id)
        if actual != expected:
            raise ValueError(
                f"{path}: name ID {name_id} is {actual!r}, expected {expected!r}"
            )

    if font["OS/2"].usWeightClass != spec.weight:
        raise ValueError(f"{path}: incorrect OS/2 weight class")
    italic_angle = font["post"].italicAngle
    if italic and italic_angle == 0:
        raise ValueError(f"{path}: italic output has an upright italic angle")
    if not italic and italic_angle != 0:
        raise ValueError(f"{path}: upright output has a nonzero italic angle")

    gpos = font["GPOS"].table
    kern_features = [
        record.Feature
        for record in gpos.FeatureList.FeatureRecord
        if record.FeatureTag == "kern"
    ]
    if not kern_features:
        raise ValueError(f"{path}: missing Montserrat kern feature")
    if italic:
        guard_index = len(gpos.LookupList.Lookup) - 1
        if gpos.LookupList.Lookup[guard_index].LookupType != 2:
            raise ValueError(f"{path}: final lookup is not the italic PairPos guard")
        if any(guard_index not in feature.LookupListIndex for feature in kern_features):
            raise ValueError(f"{path}: italic guard is not attached to every kern feature")

    font.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify the complete SNU Edge family.")
    parser.add_argument("--font-dir", type=Path, default=Path("instance_otf"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    expected_paths = []
    for spec in STYLE_SPECS:
        for italic in (False, True):
            path = args.font_dir / (
                f"{POSTSCRIPT_FAMILY_NAME}-"
                f"{postscript_style_name(spec.style, italic)}.otf"
            )
            if not path.is_file():
                raise SystemExit(f"Missing output font: {path}")
            verify_font(path, spec, italic)
            expected_paths.append(path.resolve())

    actual_paths = {path.resolve() for path in args.font_dir.glob("SNUEdge-*.otf")}
    extras = actual_paths - set(expected_paths)
    if extras:
        raise SystemExit(
            "Unexpected output font(s): " + ", ".join(map(str, sorted(extras)))
        )
    print(f"Verified {len(expected_paths)} SNU Edge fonts in {args.font_dir}")


if __name__ == "__main__":
    main()
