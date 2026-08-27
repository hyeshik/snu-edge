#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont

from add_italic_cjk_guard import GuardStats, append_guard_lookup


DEFAULT_KERN_SCALE = 0.92 * 0.88
HORIZONTAL_VALUE_FIELDS = ("XPlacement", "XAdvance")
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
FIGURE_SWAP_PAIRS = tuple((name, f"{name}.tf") for name in FIGURE_NAMES) + tuple(
    (f"{name}.osf", f"{name}.tosf") for name in FIGURE_NAMES
)
FIGURE_SWAP_MAP = {
    name: replacement
    for first, second in FIGURE_SWAP_PAIRS
    for name, replacement in ((first, second), (second, first))
}


def scale_value_record(value, factor: float) -> int:
    if value is None:
        return 0

    changed = 0
    for field in HORIZONTAL_VALUE_FIELDS:
        amount = getattr(value, field, None)
        if amount is None:
            continue
        scaled = round(amount * factor)
        if scaled != amount:
            setattr(value, field, scaled)
            changed += 1
    return changed


def pair_position_subtables(lookup):
    if lookup.LookupType == 2:
        yield from lookup.SubTable
        return
    if lookup.LookupType != 9:
        return
    for extension in lookup.SubTable:
        if extension.ExtensionLookupType == 2:
            yield extension.ExtSubTable


def swap_figure_outlines_and_metrics(font: TTFont) -> None:
    if "CFF " not in font:
        raise ValueError("The merged font has no CFF outlines.")

    char_strings = font["CFF "].cff.topDictIndex[0].CharStrings
    metrics = font["hmtx"].metrics
    missing = [
        name
        for pair in FIGURE_SWAP_PAIRS
        for name in pair
        if name not in char_strings.charStrings or name not in metrics
    ]
    if missing:
        raise ValueError("Missing Montserrat figure glyphs: " + ", ".join(missing))

    for tabular_name, proportional_name in FIGURE_SWAP_PAIRS:
        if char_strings.charStringsAreIndexed:
            tabular_index = char_strings.charStrings[tabular_name]
            proportional_index = char_strings.charStrings[proportional_name]
            tabular_char_string = char_strings[tabular_name]
            proportional_char_string = char_strings[proportional_name]
            char_strings.charStringsIndex.items[tabular_index] = (
                proportional_char_string
            )
            char_strings.charStringsIndex.items[proportional_index] = (
                tabular_char_string
            )
        else:
            (
                char_strings.charStrings[tabular_name],
                char_strings.charStrings[proportional_name],
            ) = (
                char_strings.charStrings[proportional_name],
                char_strings.charStrings[tabular_name],
            )
        metrics[tabular_name], metrics[proportional_name] = (
            metrics[proportional_name],
            metrics[tabular_name],
        )


def swap_numeric_spacing_features(font: TTFont) -> None:
    if "GSUB" not in font:
        raise ValueError("The merged font has no GSUB table.")

    feature_records = font["GSUB"].table.FeatureList.FeatureRecord
    proportional = [record for record in feature_records if record.FeatureTag == "pnum"]
    tabular = [record for record in feature_records if record.FeatureTag == "tnum"]
    if len(proportional) != 1 or len(tabular) != 1:
        raise ValueError("Expected exactly one pnum and one tnum feature.")

    proportional[0].Feature, tabular[0].Feature = (
        tabular[0].Feature,
        proportional[0].Feature,
    )


def remap_coverage(coverage, glyph_map: dict[str, str], glyph_ids: dict[str, int]) -> None:
    coverage.glyphs = sorted(
        (glyph_map.get(name, name) for name in coverage.glyphs),
        key=glyph_ids.__getitem__,
    )


def remap_class_definition(class_definition, glyph_map: dict[str, str]) -> None:
    class_definition.classDefs = {
        glyph_map.get(name, name): class_id
        for name, class_id in class_definition.classDefs.items()
    }


def remap_pair_position_subtable(
    subtable,
    glyph_map: dict[str, str],
    glyph_ids: dict[str, int],
) -> None:
    if subtable.Format == 1:
        pairs = []
        for first_glyph, pair_set in zip(
            subtable.Coverage.glyphs, subtable.PairSet
        ):
            for record in pair_set.PairValueRecord:
                record.SecondGlyph = glyph_map.get(
                    record.SecondGlyph, record.SecondGlyph
                )
            pair_set.PairValueRecord.sort(
                key=lambda record: glyph_ids[record.SecondGlyph]
            )
            pair_set.PairValueCount = len(pair_set.PairValueRecord)
            pairs.append((glyph_map.get(first_glyph, first_glyph), pair_set))
        pairs.sort(key=lambda item: glyph_ids[item[0]])
        subtable.Coverage.glyphs = [name for name, _ in pairs]
        subtable.PairSet = [pair_set for _, pair_set in pairs]
        subtable.PairSetCount = len(subtable.PairSet)
        return

    if subtable.Format == 2:
        remap_coverage(subtable.Coverage, glyph_map, glyph_ids)
        remap_class_definition(subtable.ClassDef1, glyph_map)
        remap_class_definition(subtable.ClassDef2, glyph_map)
        return

    raise ValueError(f"Unsupported PairPos format: {subtable.Format}")


def remap_figure_positioning(font: TTFont) -> None:
    if "GPOS" not in font:
        return

    glyph_ids = font.getReverseGlyphMap()
    for lookup in font["GPOS"].table.LookupList.Lookup:
        for subtable in pair_position_subtables(lookup):
            remap_pair_position_subtable(
                subtable,
                FIGURE_SWAP_MAP,
                glyph_ids,
            )

    if "kern" not in font:
        return
    for subtable in font["kern"].kernTables:
        pairs = getattr(subtable, "kernTable", None)
        if pairs is None:
            continue
        subtable.kernTable = {
            (
                FIGURE_SWAP_MAP.get(first, first),
                FIGURE_SWAP_MAP.get(second, second),
            ): amount
            for (first, second), amount in pairs.items()
        }


def promote_tabular_figures(font: TTFont) -> None:
    swap_figure_outlines_and_metrics(font)
    swap_numeric_spacing_features(font)
    remap_figure_positioning(font)


def scale_pair_position_subtable(subtable, factor: float) -> int:
    changed = 0
    if subtable.Format == 1:
        for pair_set in subtable.PairSet:
            for pair in pair_set.PairValueRecord:
                changed += scale_value_record(pair.Value1, factor)
                changed += scale_value_record(pair.Value2, factor)
        return changed

    if subtable.Format == 2:
        for class1 in subtable.Class1Record:
            for class2 in class1.Class2Record:
                changed += scale_value_record(class2.Value1, factor)
                changed += scale_value_record(class2.Value2, factor)
        return changed

    raise ValueError(f"Unsupported PairPos format: {subtable.Format}")


def kern_lookup_indices(font: TTFont) -> set[int]:
    if "GPOS" not in font:
        return set()
    feature_list = font["GPOS"].table.FeatureList
    if feature_list is None:
        return set()
    return {
        lookup_index
        for record in feature_list.FeatureRecord
        if record.FeatureTag == "kern"
        for lookup_index in record.Feature.LookupListIndex
    }


def scale_gpos_kerning(font: TTFont, factor: float) -> tuple[int, int]:
    indices = kern_lookup_indices(font)
    if not indices:
        raise ValueError("The merged font has no GPOS kern feature.")

    changed = 0
    lookups = font["GPOS"].table.LookupList.Lookup
    for lookup_index in sorted(indices):
        for subtable in pair_position_subtables(lookups[lookup_index]):
            changed += scale_pair_position_subtable(subtable, factor)
    return len(indices), changed


def scale_legacy_kerning(font: TTFont, factor: float) -> int:
    if "kern" not in font:
        return 0

    changed = 0
    for subtable in font["kern"].kernTables:
        pairs = getattr(subtable, "kernTable", None)
        if pairs is None:
            continue
        for pair, amount in list(pairs.items()):
            scaled = round(amount * factor)
            if scaled != amount:
                pairs[pair] = scaled
                changed += 1
    return changed


def finalize_font(
    input_path: Path,
    output_path: Path,
    *,
    italic: bool,
    kern_scale: float = DEFAULT_KERN_SCALE,
    revision: float | None = None,
) -> tuple[int, int, int, GuardStats | None]:
    font = TTFont(input_path)
    promote_tabular_figures(font)
    lookup_count, gpos_values = scale_gpos_kerning(font, kern_scale)
    legacy_pairs = scale_legacy_kerning(font, kern_scale)
    guard_stats = append_guard_lookup(font) if italic else None
    if revision is not None:
        font["head"].fontRevision = revision

    output_path.parent.mkdir(parents=True, exist_ok=True)
    font.save(output_path)
    font.close()
    return lookup_count, gpos_values, legacy_pairs, guard_stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scale Montserrat kerning and add the SNU Edge italic CJK guard."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--italic", action="store_true")
    parser.add_argument("--kern-scale", type=float, default=DEFAULT_KERN_SCALE)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    lookup_count, gpos_values, legacy_pairs, guard_stats = finalize_font(
        args.input,
        args.output,
        italic=args.italic,
        kern_scale=args.kern_scale,
    )
    guard_summary = "none"
    if guard_stats is not None:
        guard_summary = f"{guard_stats.guard_min}..{guard_stats.guard_max}"
    print(
        f"{args.output}: kern_lookups={lookup_count}, "
        f"gpos_values_scaled={gpos_values}, legacy_pairs_scaled={legacy_pairs}, "
        f"italic_guard={guard_summary}"
    )


if __name__ == "__main__":
    main()
