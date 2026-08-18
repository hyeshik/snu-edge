#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

from fontTools.otlLib.builder import (
    buildLookup,
    buildPairPosClassesSubtable,
    buildValue,
)
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

from build_snu_edge import is_cjk_codepoint


DEFAULT_MIN_GUARD = 20
DEFAULT_CLEARANCE = 30
DEFAULT_BUCKET_SIZE = 5
HANGUL_CODEPOINT_RANGES = (
    (0x1100, 0x11FF),
    (0x3130, 0x318F),
    (0xA960, 0xA97F),
    (0xAC00, 0xD7AF),
    (0xD7B0, 0xD7FF),
)


class GuardStats(NamedTuple):
    latin_glyphs: int
    hangul_glyphs: int
    latin_classes: int
    hangul_classes: int
    guard_min: int
    guard_max: int
    lookup_index: int


def is_hangul_codepoint(codepoint: int) -> bool:
    return any(start <= codepoint <= end for start, end in HANGUL_CODEPOINT_RANGES)


def round_up(value: float, step: int) -> int:
    return int(math.ceil(value / step) * step)


def round_down(value: float, step: int) -> int:
    return int(math.floor(value / step) * step)


def guard_units(
    *,
    right_overhang: float,
    hangul_left_side_bearing: float,
    minimum: int = DEFAULT_MIN_GUARD,
    clearance: int = DEFAULT_CLEARANCE,
    bucket_size: int = DEFAULT_BUCKET_SIZE,
) -> int:
    required = right_overhang + clearance - hangul_left_side_bearing
    return max(minimum, round_up(required, bucket_size))


def glyph_bounds(glyph_set, glyph_name: str) -> tuple[float, float, float, float] | None:
    pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    return pen.bounds


def encoded_glyph_codepoints(font: TTFont) -> dict[str, set[int]]:
    codepoints: dict[str, set[int]] = defaultdict(set)
    for codepoint, glyph_name in font.getBestCmap().items():
        codepoints[glyph_name].add(codepoint)
    return codepoints


def collect_geometry_classes(
    font: TTFont,
    bucket_size: int,
) -> tuple[dict[int, tuple[str, ...]], dict[int, tuple[str, ...]]]:
    glyph_set = font.getGlyphSet()
    hmtx = font["hmtx"]
    latin_classes: dict[int, list[str]] = defaultdict(list)
    hangul_classes: dict[int, list[str]] = defaultdict(list)

    for glyph_name, codepoints in encoded_glyph_codepoints(font).items():
        bounds = glyph_bounds(glyph_set, glyph_name)
        if bounds is None:
            continue

        if any(is_hangul_codepoint(codepoint) for codepoint in codepoints):
            hangul_classes[round_down(bounds[0], bucket_size)].append(glyph_name)
            continue

        is_terminal_letter = any(
            not is_cjk_codepoint(codepoint)
            and unicodedata.category(chr(codepoint)).startswith("L")
            for codepoint in codepoints
        )
        if not is_terminal_letter:
            continue

        advance_width = hmtx[glyph_name][0]
        right_overhang = bounds[2] - advance_width
        latin_classes[round_up(right_overhang, bucket_size)].append(glyph_name)

    return (
        {key: tuple(sorted(value)) for key, value in latin_classes.items()},
        {key: tuple(sorted(value)) for key, value in hangul_classes.items()},
    )


def append_guard_lookup(
    font: TTFont,
    *,
    minimum: int = DEFAULT_MIN_GUARD,
    clearance: int = DEFAULT_CLEARANCE,
    bucket_size: int = DEFAULT_BUCKET_SIZE,
) -> GuardStats:
    if "GPOS" not in font:
        raise ValueError("The input font has no GPOS table.")
    if font["post"].italicAngle == 0:
        raise ValueError("The input font is not marked as italic.")

    latin_classes, hangul_classes = collect_geometry_classes(font, bucket_size)
    if not latin_classes:
        raise ValueError("The input font has no non-CJK terminal letters.")
    if not hangul_classes:
        raise ValueError("The input font has no Hangul glyphs.")

    empty_value = buildValue({})
    pairs = {}
    guard_values = []
    for right_overhang, latin_glyphs in latin_classes.items():
        for left_side_bearing, hangul_glyphs in hangul_classes.items():
            guard = guard_units(
                right_overhang=right_overhang,
                hangul_left_side_bearing=left_side_bearing,
                minimum=minimum,
                clearance=clearance,
                bucket_size=bucket_size,
            )
            pairs[(latin_glyphs, hangul_glyphs)] = (
                buildValue({"XAdvance": guard}),
                empty_value,
            )
            guard_values.append(guard)

    subtable = buildPairPosClassesSubtable(pairs, font.getReverseGlyphMap())
    lookup = buildLookup([subtable])
    gpos = font["GPOS"].table
    lookup_index = len(gpos.LookupList.Lookup)
    gpos.LookupList.Lookup.append(lookup)
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)

    kern_features = [
        record.Feature
        for record in gpos.FeatureList.FeatureRecord
        if record.FeatureTag == "kern"
    ]
    if not kern_features:
        raise ValueError("The input font has no GPOS kern feature.")
    for feature in kern_features:
        feature.LookupListIndex.append(lookup_index)
        feature.LookupCount = len(feature.LookupListIndex)

    return GuardStats(
        latin_glyphs=sum(map(len, latin_classes.values())),
        hangul_glyphs=sum(map(len, hangul_classes.values())),
        latin_classes=len(latin_classes),
        hangul_classes=len(hangul_classes),
        guard_min=min(guard_values),
        guard_max=max(guard_values),
        lookup_index=lookup_index,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Add non-breaking italic Latin-to-upright-Hangul optical guards "
            "to an already merged OpenType font."
        )
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--minimum", type=int, default=DEFAULT_MIN_GUARD)
    parser.add_argument("--clearance", type=int, default=DEFAULT_CLEARANCE)
    parser.add_argument("--bucket-size", type=int, default=DEFAULT_BUCKET_SIZE)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.input.resolve() == args.output.resolve():
        raise SystemExit("Input and output paths must differ.")

    font = TTFont(args.input)
    stats = append_guard_lookup(
        font,
        minimum=args.minimum,
        clearance=args.clearance,
        bucket_size=args.bucket_size,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    font.save(args.output)
    print(
        f"{args.output}: latin_glyphs={stats.latin_glyphs}, "
        f"hangul_glyphs={stats.hangul_glyphs}, "
        f"latin_classes={stats.latin_classes}, "
        f"hangul_classes={stats.hangul_classes}, "
        f"guard_range={stats.guard_min}..{stats.guard_max}, "
        f"lookup_index={stats.lookup_index}"
    )


if __name__ == "__main__":
    main()
