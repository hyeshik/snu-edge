#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

from build_snu_edge import (
    COPYRIGHT_TEXT,
    FAMILY_NAME,
    LICENSE_DESCRIPTION,
    LICENSE_URL,
    MODERN_HANGUL_RANGE,
    POSTSCRIPT_FAMILY_NAME,
    STYLE_SPECS,
    VERSION,
    font_revision,
    postscript_style_name,
    style_name,
)


REQUIRED_TABLES = {"CFF ", "GPOS", "GSUB", "OS/2", "cmap", "name", "post"}
REQUIRED_CODEPOINTS = (ord("A"), ord("e"), ord("é"), ord("한"))
FIGURE_NAMES = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
)
PRESERVED_FINAL_H = "갛겋낳넣놓닿땋떻랗렇맣멓뭏빻쌓앻얗옇읗좋찧핳햏헿훃"
EXPECTED_OUTLINED_HANGUL = 2479
FALLBACK_SAMPLES = "갂갷딽힢"


def glyph_bounds(font: TTFont, glyph_name: str):
    glyph_set = font.getGlyphSet()
    pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    return pen.bounds


def glyph_has_outline(font: TTFont, glyph_name: str) -> bool:
    return glyph_bounds(font, glyph_name) is not None


def glyph_dimensions(font: TTFont, glyph_name: str) -> tuple[float, float]:
    bounds = glyph_bounds(font, glyph_name)
    if bounds is None:
        raise ValueError(f"glyph has no outline: {glyph_name}")
    return bounds[2] - bounds[0], bounds[3] - bounds[1]


def verify_hangul_fallback_policy(
    path: Path,
    font: TTFont,
) -> None:
    cmap = font.getBestCmap()
    hangul = {
        codepoint: glyph_name
        for codepoint, glyph_name in cmap.items()
        if MODERN_HANGUL_RANGE[0] <= codepoint <= MODERN_HANGUL_RANGE[1]
    }
    if len(hangul) != EXPECTED_OUTLINED_HANGUL:
        raise ValueError(
            f"{path}: expected {EXPECTED_OUTLINED_HANGUL} outlined Hangul glyphs, "
            f"got {len(hangul)}"
        )

    empty = [
        codepoint
        for codepoint, glyph_name in hangul.items()
        if not glyph_has_outline(font, glyph_name)
    ]
    if empty:
        glyphs = "".join(chr(codepoint) for codepoint in empty)
        raise ValueError(f"{path}: empty Hangul glyphs remain encoded: {glyphs}")

    retained_fallback_samples = [
        character for character in FALLBACK_SAMPLES if ord(character) in hangul
    ]
    if retained_fallback_samples:
        raise ValueError(
            f"{path}: empty Hangul fallback samples remain encoded: "
            f"{''.join(retained_fallback_samples)}"
        )

    missing_preserved = [
        character for character in PRESERVED_FINAL_H if ord(character) not in cmap
    ]
    empty_preserved = [
        character
        for character in PRESERVED_FINAL_H
        if ord(character) in cmap
        and not glyph_has_outline(font, cmap[ord(character)])
    ]
    if missing_preserved or empty_preserved:
        raise ValueError(
            f"{path}: valid NanumSquare final-ㅎ glyphs were not preserved; "
            f"missing={''.join(missing_preserved)!r}, empty={''.join(empty_preserved)!r}"
        )


def single_substitution_mapping(font: TTFont, feature_tag: str) -> dict[str, str]:
    gsub = font["GSUB"].table
    mappings = {}
    records = [
        record
        for record in gsub.FeatureList.FeatureRecord
        if record.FeatureTag == feature_tag
    ]
    if len(records) != 1:
        raise ValueError(f"expected exactly one {feature_tag} feature")
    for lookup_index in records[0].Feature.LookupListIndex:
        lookup = gsub.LookupList.Lookup[lookup_index]
        subtables = lookup.SubTable
        if lookup.LookupType == 7:
            subtables = [
                extension.ExtSubTable
                for extension in lookup.SubTable
                if extension.ExtensionLookupType == 1
            ]
        for subtable in subtables:
            mappings.update(getattr(subtable, "mapping", {}))
    return mappings


def shape_run(path: Path, text: str, features: dict[str, bool]):
    import uharfbuzz as hb

    data = path.read_bytes()
    face = hb.Face(hb.Blob(data))
    hb_font = hb.Font(face)
    hb_font.scale = (face.upem, face.upem)
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(hb_font, buffer, features)
    shaped_font = TTFont(path, lazy=True)
    glyph_order = shaped_font.getGlyphOrder()
    shaped_font.close()
    return [
        (
            glyph_order[info.codepoint],
            position.x_advance,
            position.x_offset,
        )
        for info, position in zip(buffer.glyph_infos, buffer.glyph_positions)
    ]


def verify_figure_styles(path: Path, font: TTFont) -> None:
    metrics = font["hmtx"].metrics
    tabular_lining = [metrics[name][0] for name in FIGURE_NAMES]
    tabular_oldstyle = [metrics[f"{name}.osf"][0] for name in FIGURE_NAMES]
    proportional_lining = [metrics[f"{name}.tf"][0] for name in FIGURE_NAMES]
    proportional_oldstyle = [metrics[f"{name}.tosf"][0] for name in FIGURE_NAMES]
    if len(set(tabular_lining + tabular_oldstyle)) != 1:
        raise ValueError(f"{path}: default and oldstyle tabular figures differ in width")
    if len(set(proportional_lining)) == 1 or len(set(proportional_oldstyle)) == 1:
        raise ValueError(f"{path}: pnum alternates are not proportional")

    expected_pnum = {
        **{name: f"{name}.tf" for name in FIGURE_NAMES},
        **{f"{name}.osf": f"{name}.tosf" for name in FIGURE_NAMES},
    }
    expected_tnum = {replacement: default for default, replacement in expected_pnum.items()}
    if single_substitution_mapping(font, "pnum") != expected_pnum:
        raise ValueError(f"{path}: pnum does not select proportional figures")
    if single_substitution_mapping(font, "tnum") != expected_tnum:
        raise ValueError(f"{path}: tnum does not restore tabular figures")

    default = shape_run(path, "0123456789", {"kern": True})
    if [name for name, _, _ in default] != list(FIGURE_NAMES):
        raise ValueError(f"{path}: default figures are not the encoded lining figures")
    if len({advance for _, advance, _ in default}) != 1:
        raise ValueError(f"{path}: default figure advances are not tabular after shaping")

    explicit_tabular = shape_run(
        path,
        "0123456789",
        {"kern": True, "tnum": True},
    )
    if explicit_tabular != default:
        raise ValueError(f"{path}: tnum does not preserve the tabular default")

    proportional = shape_run(
        path,
        "0123456789",
        {"kern": True, "pnum": True},
    )
    if [name for name, _, _ in proportional] != [
        f"{name}.tf" for name in FIGURE_NAMES
    ]:
        raise ValueError(f"{path}: pnum shaping does not select proportional figures")
    if len({advance for _, advance, _ in proportional}) == 1:
        raise ValueError(f"{path}: pnum shaping remains tabular")

    oldstyle = shape_run(path, "0123456789", {"kern": True, "onum": True})
    if [name for name, _, _ in oldstyle] != [
        f"{name}.osf" for name in FIGURE_NAMES
    ] or len({advance for _, advance, _ in oldstyle}) != 1:
        raise ValueError(f"{path}: onum does not select tabular oldstyle figures")

    proportional_oldstyle = shape_run(
        path,
        "0123456789",
        {"kern": True, "onum": True, "pnum": True},
    )
    if [name for name, _, _ in proportional_oldstyle] != [
        f"{name}.tosf" for name in FIGURE_NAMES
    ] or len({advance for _, advance, _ in proportional_oldstyle}) == 1:
        raise ValueError(
            f"{path}: onum plus pnum does not select proportional oldstyle figures"
        )

    decimal = shape_run(path, "1.23 45.6 789.0", {"kern": True})
    digit_advances = {
        advance for name, advance, _ in decimal if name in FIGURE_NAMES
    }
    period_advances = [advance for name, advance, _ in decimal if name == "period"]
    if len(digit_advances) != 1 or len(set(period_advances)) != 1:
        raise ValueError(f"{path}: decimal figures do not keep stable advances")

    fraction = shape_run(path, "1/2", {"frac": True})
    if [name for name, _, _ in fraction] != ["one.numr", "fraction", "two.dnom"]:
        raise ValueError(f"{path}: frac shaping was broken by figure promotion")


def verify_latin_geometry(path: Path, font: TTFont, *, italic: bool) -> None:
    upright_geometry = () if italic else (
        "period",
        "degree",
        "copyright",
        "filledbox",
        "uni25A1",
        "uni25C6",
    )
    for glyph_name in upright_geometry:
        width, height = glyph_dimensions(font, glyph_name)
        aspect = width / height
        if not 0.90 <= aspect <= 1.10:
            raise ValueError(
                f"{path}: {glyph_name} did not preserve its near-square aspect: "
                f"{aspect:.4f}"
            )

    if not italic:
        period_width, _ = glyph_dimensions(font, "period")
        colon_width, _ = glyph_dimensions(font, "colon")
        if abs(period_width - colon_width) > 1:
            raise ValueError(
                f"{path}: colon components were not transformed like period: "
                f"{colon_width} != {period_width}"
            )

    component_pairs = (
        ("hyphen", "uni2010"),
        ("emdash", "uni2015"),
        ("gravecomb", "grave"),
        ("two.dnom", "uni00B2"),
        ("periodcentered", "uni2219"),
    )
    for component_name, composite_name in component_pairs:
        component_dimensions = glyph_dimensions(font, component_name)
        composite_dimensions = glyph_dimensions(font, composite_name)
        if any(
            abs(component - composite) > 1
            for component, composite in zip(
                component_dimensions,
                composite_dimensions,
            )
        ):
            raise ValueError(
                f"{path}: {composite_name} received a repeated transform: "
                f"{composite_dimensions} != {component_dimensions}"
            )


def verify_font(
    path: Path,
    spec,
    italic: bool,
) -> None:
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
    expected_full_name = f"{FAMILY_NAME} {expected_style}"
    expected_names = {
        0: COPYRIGHT_TEXT,
        1: FAMILY_NAME,
        2: expected_style,
        4: expected_full_name,
        5: f"Version {VERSION}",
        6: expected_ps_name,
        13: LICENSE_DESCRIPTION,
        14: LICENSE_URL,
        16: FAMILY_NAME,
        18: expected_full_name,
    }
    for name_id, expected in expected_names.items():
        actual = names.getDebugName(name_id)
        if actual != expected:
            raise ValueError(
                f"{path}: name ID {name_id} is {actual!r}, expected {expected!r}"
            )

    expected_revision = font_revision()
    actual_revision = font["head"].fontRevision
    if abs(actual_revision - expected_revision) > 1 / 65536:
        raise ValueError(
            f"{path}: head.fontRevision is {actual_revision}, "
            f"expected {expected_revision}"
        )

    if font["OS/2"].usWeightClass != spec.weight:
        raise ValueError(f"{path}: incorrect OS/2 weight class")
    if font["OS/2"].fsType != 0:
        raise ValueError(f"{path}: OS/2.fsType must allow installable embedding")
    italic_angle = font["post"].italicAngle
    if italic and italic_angle == 0:
        raise ValueError(f"{path}: italic output has an upright italic angle")
    if not italic and italic_angle != 0:
        raise ValueError(f"{path}: upright output has a nonzero italic angle")

    verify_figure_styles(path, font)
    verify_latin_geometry(path, font, italic=italic)
    verify_hangul_fallback_policy(path, font)

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
